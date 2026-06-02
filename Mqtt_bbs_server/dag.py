"""
DAG 工作流引擎 — 基于 BBS 的任务编排

用法:
    from Mqtt_bbs_server.dag import DAGWorkflow, DAGTask

    wf = DAGWorkflow("data_pipeline")
    wf.add_task(DAGTask("fetch", capability="scraper",
               input={"url": "https://..."}))
    wf.add_task(DAGTask("parse", deps=["fetch"],
               capability="parser", retry=2))
    wf.add_task(DAGTask("report", deps=["parse"],
               capability="analyst"))

    # 执行（返回 task_id → result 映射）
    results = wf.run(board, timeout=300)
"""

import json, time, uuid, logging
from typing import Optional, Callable
from dataclasses import dataclass, field
from enum import Enum

log = logging.getLogger("Mqtt_bbs.dag")


class TaskStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class DAGTask:
    """DAG 中的一个任务节点"""
    name: str
    deps: list = field(default_factory=list)        # 依赖的任务名列表
    capability: str = ""                             # 需要的能力
    target_agent: str = ""                           # 定向 Agent
    input: dict = field(default_factory=dict)        # 任务输入
    retry: int = 0                                   # 重试次数
    timeout: int = 120                               # 超时(秒)
    max_concurrency: int = -1                        # 并行度限制(-1=不限)
    condition: Optional[Callable] = None             # 条件分支: callable(results) → bool


class DAGWorkflow:
    """
    DAG 工作流

    1. add_task() 定义 DAG
    2. run(board) 按拓扑序执行
    3. 自动并行 + 条件分支 + 重试
    """

    def __init__(self, name: str = "dag"):
        self.name = name
        self._tasks: dict[str, DAGTask] = {}
        self._results: dict[str, dict] = {}          # task_name → TaskOutput
        self._statuses: dict[str, TaskStatus] = {}
        self._wf_id = f"wf_{uuid.uuid4().hex[:8]}"

    def add_task(self, task: DAGTask) -> "DAGWorkflow":
        """添加任务节点"""
        self._tasks[task.name] = task
        self._statuses[task.name] = TaskStatus.PENDING
        return self

    def validate(self) -> list[str]:
        """检查 DAG 合法性（循环依赖/缺失依赖）"""
        errors = []
        for name, task in self._tasks.items():
            for dep in task.deps:
                if dep not in self._tasks:
                    errors.append(f"任务 '{name}' 依赖 '{dep}' 不存在")
            if task.condition and task.deps:
                cond_deps = task.condition.__code__.co_varnames
                for cd in cond_deps:
                    if cd not in task.deps and cd != task.deps[0]:
                        pass  # 条件函数可以使用任意变量名
        # 环检测（简单拓扑排序）
        visited = set()
        temp = set()

        def _dfs(n):
            if n in temp:
                errors.append(f"循环依赖: {n}")
                return
            if n in visited:
                return
            temp.add(n)
            for dep in self._tasks[n].deps:
                _dfs(dep)
            temp.remove(n)
            visited.add(n)

        for n in self._tasks:
            _dfs(n)

        return errors

    def _ready_tasks(self) -> list[str]:
        """返回所有待办且依赖已满足的任务"""
        ready = []
        for name, status in self._statuses.items():
            if status != TaskStatus.PENDING:
                continue
            task = self._tasks[name]
            # 检查依赖是否全部成功（或根据条件分支决定）
            all_deps_ok = True
            for dep in task.deps:
                dep_status = self._statuses.get(dep)
                if dep_status != TaskStatus.SUCCESS:
                    all_deps_ok = False
                    break
                # 检查条件分支
                if task.condition:
                    dep_result = self._results.get(dep, {})
                    if not task.condition(dep_result):
                        all_deps_ok = False
                        break
            if all_deps_ok:
                ready.append(name)
        return ready

    def run(self, board, timeout: float = 300) -> dict[str, dict]:
        """
        执行 DAG 工作流（阻塞直到完成或超时）

        参数:
            board: AgentBoard 实例
            timeout: 整体超时

        返回: task_name → TaskOutput dict
        """
        errors = self.validate()
        if errors:
            raise ValueError(f"DAG 校验失败: {', '.join(errors)}")

        deadline = time.time() + timeout
        tid_map = {}  # task_name → task_id

        while time.time() < deadline:
            # 检查是否全部完成
            completed = {n for n, s in self._statuses.items()
                         if s in (TaskStatus.SUCCESS, TaskStatus.FAILED, TaskStatus.SKIPPED)}
            if len(completed) == len(self._tasks):
                break

            # 获取就绪任务
            ready = self._ready_tasks()
            for name in ready:
                task = self._tasks[name]
                self._statuses[name] = TaskStatus.RUNNING
                # 发布任务
                if task.target_agent:
                    tid = board.post_task_routed(
                        task.name, task.input,
                        target_agent_id=task.target_agent,
                    )
                elif task.capability:
                    tid = board.post_task_routed(
                        task.name, task.input,
                        target_capability=task.capability,
                    )
                else:
                    tid = board.post_task(task.name, task.input)
                tid_map[name] = tid
                log.info(f"[DAG] [START] 启动任务 '{name}' → {tid}")

            # 轮询完成的任务
            for name, tid in list(tid_map.items()):
                if self._statuses[name] != TaskStatus.RUNNING:
                    continue
                try:
                    output = board.wait_task(tid, timeout=min(30, deadline - time.time()))
                    if output and output.get("status") == "completed":
                        self._results[name] = output
                        self._statuses[name] = TaskStatus.SUCCESS
                        log.info(f"[DAG] [OK] 任务 '{name}' 完成")
                    else:
                        # 重试逻辑
                        task = self._tasks[name]
                        if task.retry > 0:
                            task.retry -= 1
                            self._statuses[name] = TaskStatus.PENDING
                            log.info(f"[DAG] [SYNC] 重试 '{name}' (剩余{task.retry})")
                        else:
                            self._results[name] = output or {}
                            self._statuses[name] = TaskStatus.FAILED
                            log.warning(f"[DAG] [FAIL] 任务 '{name}' 失败")
                except Exception as e:
                    log.warning(f"[DAG] [WARN] 等待任务 '{name}' 异常: {e}")

            time.sleep(0.5)

        # 返回结果
        return {
            name: {
                "status": self._statuses[name].value,
                "result": self._results.get(name, {}).get("result"),
            }
            for name in self._tasks
        }


# ── 快捷入口 ──

def run_dag(name: str, tasks: list[DAGTask], board,
            timeout: float = 300) -> dict[str, dict]:
    """快捷执行 DAG"""
    wf = DAGWorkflow(name)
    for t in tasks:
        wf.add_task(t)
    return wf.run(board, timeout=timeout)
