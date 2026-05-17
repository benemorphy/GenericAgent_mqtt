"""
BBS 业务层 — AgentBoard（主智能体）+ WorkerAgent（工作智能体）

对标 subagent 文件协议的业务语义：
    AgentBoard.post_task()    → 创建任务（写 input.txt）
    AgentBoard.wait_task()    → 等待结果（轮询 output.txt → 改为了订阅推送）
    WorkerAgent.start()       → 启动消息循环（类似 agentmain.py --task）
    WorkerAgent.claim_task()  → 认领任务（创建 task 目录）
    WorkerAgent.stream_out()  → 实时输出（写 stdout/stderr）
    WorkerAgent.complete()    → 完成任务（写 output.txt + [ROUND END]）
"""

import json, time, uuid, logging, threading
from typing import Optional, Callable, Any
from enum import Enum

from .client import BBSClient, TaskMessage, TaskOutput
from . import config

log = logging.getLogger("mqtt_bbs.bbs")


class TaskStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    DONE = "done"
    FAILED = "failed"
    CANCELLED = "cancelled"


# ──────────────────────────────────────────────
# AgentBoard — 主智能体（任务发布者）
# ──────────────────────────────────────────────

class AgentBoard:
    """
    主智能体接口。

    对标: 创建 temp/{task_name}/input.txt → 等 output.txt → 读结果

    用法:
        board = AgentBoard("master")
        tid = board.post_task("scan", {"target": "10.0.0.0/24"})
        result = board.wait_task(tid, timeout=120)
    """

    def __init__(self, agent_id: str = "master"):
        self.agent_id = agent_id
        self._client = BBSClient(agent_id)

        # 任务结果缓存：task_id → TaskOutput
        self._results: dict[str, TaskOutput] = {}
        # 任务回调：task_id → callback
        self._callbacks: dict[str, Callable] = {}

    def __enter__(self):
        self._client.connect()
        self._client.wait_connected(5)
        return self

    def __exit__(self, *args):
        self._client.disconnect()

    # ── 发布任务 ──

    def post_task(self, task_type: str, task_input: dict,
                  task_id: Optional[str] = None,
                  priority: int = 3,
                  timeout: int = config.DEFAULT_TASK_TIMEOUT) -> str:
        """
        发布任务到公告板。

        对标: 写入 temp/{task_id}/input.txt

        Returns: task_id
        """
        if task_id is None:
            task_id = f"task_{uuid.uuid4().hex[:8]}"

        msg = TaskMessage(
            task_id=task_id,
            type=task_type,
            input=task_input,
            priority=priority,
            timeout=timeout,
        )

        # 发布 input + 初始状态
        self._client.publish(f"board/task/{task_id}/input", msg.to_dict(), retain=True)
        self._client.publish(f"board/task/{task_id}/status", TaskStatus.PENDING.value, retain=True)

        # 也发布到 open 索引（待认领列表）
        self._client.publish(f"board/open", task_id, retain=False)

        log.info(f"[{self.agent_id}] 📤 发布任务: {task_id} ({task_type})")
        return task_id

    # ── 等待结果 ──

    def wait_task(self, task_id: str, timeout: Optional[float] = None,
                  poll_interval: float = 0.5) -> TaskOutput:
        """
        等待任务完成。

        对标: 轮询 temp/{task_id}/output.txt + 检测 [ROUND END]

        通过订阅 task/{id}/signal 和 task/{id}/output 实现实时推送。

        Returns: TaskOutput
        """
        if timeout is None:
            timeout = config.DEFAULT_TASK_TIMEOUT

        result_holder = {"output": None}

        def on_output(topic, payload):
            if isinstance(payload, dict):
                result_holder["output"] = TaskOutput.from_dict(payload)

        def on_signal(topic, payload):
            signal = payload
            if isinstance(payload, bytes):
                signal = payload.decode("utf-8")
            if signal == "[ROUND_END]":
                # signal 收到后，output 应该在 Retain 中
                pass

        # 订阅 output 和 signal
        self._client.subscribe(f"board/task/{task_id}/output", on_output)
        self._client.subscribe(f"board/task/{task_id}/signal", on_signal)

        # 先尝试读 Retain（任务可能已经完成）
        # paho 的 subscribe 会自动收到 Retain 消息

        deadline = time.time() + timeout
        while time.time() < deadline:
            if result_holder["output"] is not None:
                self._client.unsubscribe(f"board/task/{task_id}/output")
                self._client.unsubscribe(f"board/task/{task_id}/signal")
                log.info(f"[{self.agent_id}] ✅ 任务完成: {task_id}")
                return result_holder["output"]
            time.sleep(poll_interval)

        # 超时
        self._client.unsubscribe(f"board/task/{task_id}/output")
        self._client.unsubscribe(f"board/task/{task_id}/signal")
        log.warning(f"[{self.agent_id}] ⏰ 任务超时: {task_id}")
        return TaskOutput(task_id=task_id, agent_id="", status="failed",
                          error={"type": "timeout", "msg": f"等待超过{timeout}秒"})

    # ── 取消任务 ──

    def cancel_task(self, task_id: str):
        """发送取消信号"""
        self._client.publish(f"board/task/{task_id}/signal", "[CANCEL]", retain=True, qos=2)
        self._client.publish(f"board/task/{task_id}/status", TaskStatus.CANCELLED.value, retain=True)
        log.info(f"[{self.agent_id}] 🛑 取消任务: {task_id}")


# ──────────────────────────────────────────────
# WorkerAgent — 工作智能体（任务执行者）
# ──────────────────────────────────────────────

class WorkerAgent:
    """
    工作智能体接口。

    对标: agentmain.py --task {name} → 读 input.txt → 执行 → 写 output.txt → [ROUND END]

    用法:
        worker = WorkerAgent("agent_alpha", capabilities=["scan", "analyse"])
        worker.on_task(lambda task: {"result": "ok"})
        worker.start()  # 进入消息循环
    """

    def __init__(self, agent_id: str, capabilities: Optional[list[str]] = None,
                 host: str = config.BROKER_HOST, port: int = config.BROKER_PORT):
        self.agent_id = agent_id
        self.capabilities = capabilities or []
        self._client = BBSClient(agent_id, host, port)
        self._task_handler: Optional[Callable] = None
        self._running = False
        self._current_task_id: Optional[str] = None
        self._seq = 0  # stdout/stderr 序列号

    # ── 注册任务处理器 ──

    def on_task(self, handler: Callable[[TaskMessage], Any]):
        """
        注册任务处理函数。

        handler 接收 TaskMessage，返回结果（将被写入 output）。
        handler 也可以调用 self.stream_out() / self.stream_err() 实时输出。
        """
        self._task_handler = handler
        return self

    # ── 启动 ──

    def start(self, block: bool = True):
        """
        启动工作智能体。

        - 发布能力声明到 node/{id}/capability
        - 订阅 board/task/+/input 等待任务
        - block=True 时进入阻塞循环

        对标: subagent 启动后等待任务分配
        """
        self._client.connect()
        self._client.wait_connected(5)
        self._running = True

        # 发布能力声明
        self._client.publish(f"node/{self.agent_id}/capability",
                             {"agent_id": self.agent_id, "capabilities": self.capabilities},
                             retain=True)

        # 发布在线状态
        self._client.publish(f"node/{self.agent_id}/status", "online", retain=True)

        # 订阅所有任务的 input（含待认领 + 新发布）
        # 注意：公共 Broker 上会看到所有任务，实际使用应加 ACL
        self._client.subscribe("board/task/+/input", self._on_task_input)

        # 订阅取消信号
        self._client.subscribe(f"node/{self.agent_id}/task/current", self._on_cancel)

        log.info(f"[{self.agent_id}] 🚀 启动 (capabilities={self.capabilities})")

        if block:
            try:
                while self._running:
                    time.sleep(1)
            except KeyboardInterrupt:
                self.stop()

    def stop(self):
        """停止工作智能体"""
        self._running = False
        self._client.publish(f"node/{self.agent_id}/status", "offline", retain=True)
        self._client.disconnect()
        log.info(f"[{self.agent_id}] 🛑 停止")

    # ── 认领任务 ──

    def claim_task(self, task_id: str) -> bool:
        """
        认领任务。

        对标: agentmain.py --task {task_id} → 创建 temp/{task_id}/目录
        """
        self._current_task_id = task_id
        self._seq = 0

        # 发布 claim + 状态
        self._client.publish(f"board/task/{task_id}/claim",
                             {"agent_id": self.agent_id, "claimed_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())},
                             retain=True)
        self._client.publish(f"board/task/{task_id}/status", TaskStatus.RUNNING.value, retain=True)
        self._client.publish(f"node/{self.agent_id}/task/current", task_id, retain=True)
        self._client.publish(f"node/{self.agent_id}/status", "busy", retain=True)

        log.info(f"[{self.agent_id}] 🤝 认领任务: {task_id}")
        return True

    # ── 流式输出 ──

    def stream_out(self, data: str):
        """
        实时标准输出。

        对标: print / logger 写入 stdout
        """
        self._seq += 1
        if self._current_task_id:
            self._client.publish_stream(f"board/task/{self._current_task_id}/stdout", self._seq, data)

    def stream_err(self, data: str):
        """
        实时错误输出。

        对标: logger.error 写入 stderr
        """
        self._seq += 1
        if self._current_task_id:
            self._client.publish_stream(f"board/task/{self._current_task_id}/stderr", self._seq, data)

    # ── 完成任务 ──

    def complete(self, result: Any = None, status: str = "completed", error: Optional[dict] = None):
        """
        完成任务。

        对标: 写入 output.txt → 追加 [ROUND END]

        Args:
            result: 任务结果
            status: "completed" | "failed"
            error: 错误信息
        """
        task_id = self._current_task_id
        if not task_id:
            return

        output = TaskOutput(
            task_id=task_id,
            agent_id=self.agent_id,
            status=status,
            result=result,
            error=error,
            metrics={"duration_sec": 0},  # TODO: 可加计时
        )

        # 写 output（对标 output.txt）
        self._client.publish(f"board/task/{task_id}/output", output.to_dict(), retain=True, qos=1)

        # 发完成信号（对标 [ROUND END]）
        self._client.publish(f"board/task/{task_id}/signal", "[ROUND_END]", retain=True, qos=2)

        # 更新状态
        task_status = TaskStatus.DONE if status == "completed" else TaskStatus.FAILED
        self._client.publish(f"board/task/{task_id}/status", task_status.value, retain=True)

        # 清理自身状态
        self._client.publish(f"node/{self.agent_id}/task/current", "", retain=True)
        self._client.publish(f"node/{self.agent_id}/status", "online", retain=True)

        log.info(f"[{self.agent_id}] ✅ 任务完成: {task_id} (status={status})")
        self._current_task_id = None

    # ── 内部消息处理 ──

    def _on_task_input(self, topic: str, payload):
        """收到任务 input → 判断能力匹配 → 自动认领"""
        if not self._task_handler:
            return

        if not isinstance(payload, dict):
            return

        # 提取 task_id 从 topic "board/task/{task_id}/input"
        parts = topic.split("/")
        if len(parts) >= 3:
            task_id = parts[2]
        else:
            return

        msg = TaskMessage.from_dict(payload)

        # 能力匹配检查
        if self.capabilities and msg.type not in self.capabilities:
            log.debug(f"[{self.agent_id}] ⏭ 跳过不匹配任务: {msg.type} (我有: {self.capabilities})")
            return

        # 自动认领
        self.claim_task(task_id)

        # 执行
        try:
            log.info(f"[{self.agent_id}] ▶ 执行任务: {task_id} ({msg.type})")
            self.stream_out(f"开始执行: {msg.type}")
            result = self._task_handler(msg)
            self.complete(result=result)
        except Exception as e:
            log.error(f"[{self.agent_id}] ❌ 任务异常: {e}")
            self.stream_err(f"异常: {str(e)}")
            self.complete(status="failed", error={"type": "exception", "msg": str(e)})

    def _on_cancel(self, topic: str, payload):
        """收到取消信号"""
        if isinstance(payload, bytes):
            payload = payload.decode("utf-8")
        if payload == "[CANCEL]" and self._current_task_id:
            log.warning(f"[{self.agent_id}] 🛑 收到取消信号")
            self.complete(status="failed", error={"type": "cancelled", "msg": "被主智能体取消"})
