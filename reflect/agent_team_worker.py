"""
reflect module: BBS接单 (MQTT版)

使用 mqtt_bbs WorkerAgent 替代 HTTP 轮询。
在 agent_team_setting.json 中配置 broker 地址。

用法:
    python agentmain.py --reflect reflect/agent_team_worker.py

配置示例 (agent_team_setting.json):
    {
        "name": "worker_01",
        "broker_host": "127.0.0.1",
        "broker_port": 1883,
        "capabilities": ["analyse", "scan"]
    }
"""

import json, os, time, threading
from queue import Queue

INTERVAL = 5
ONCE = False

_dir = os.path.dirname(os.path.abspath(__file__))
_worker = None
_task_queue = Queue()        # check()从中取任务给LLM
_pending_task = None         # 当前正在处理的任务
_last_done = 0
_cfg = {}


def init(a):
    global _cfg, _worker
    try:
        c = json.load(open(os.path.join(_dir, 'agent_team_setting.json')))
    except Exception:
        c = {}
    c.update(a)
    _cfg = c

    try:
        from mqtt_bbs import WorkerAgentWithPersistence as WorkerAgent
    except ImportError:
        return  # mqtt_bbs 未安装，跳过初始化

    _worker = WorkerAgent(
        c.get('name', 'team_worker'),
        capabilities=c.get('capabilities', []),
        host=c.get('broker_host', '127.0.0.1'),
        port=c.get('broker_port', 1883),
    )

    def on_task(msg):
        """收到BBS任务，入队等 check() 取"""
        _task_queue.put(msg)
        print(f"[MQTT] 收到任务: {msg.task_id} ({msg.type})")

    _worker.on_task(on_task)
    _worker.start(block=False)
    print(f"[MQTT] WorkerAgent 已启动 ({c.get('broker_host', '127.0.0.1')}:{c.get('broker_port', 1883)})")


def check():
    global _pending_task
    if _worker is None:
        return None
    if _pending_task is not None:
        # 已有待处理任务，继续返回 prompt
        return _make_prompt(_pending_task)
    if _task_queue.empty():
        return None
    _pending_task = _task_queue.get_nowait()
    return _make_prompt(_pending_task)


def on_done(result):
    global _pending_task, _last_done
    if _pending_task is None:
        return
    task = _pending_task
    _pending_task = None
    _last_done = time.time()

    # 通过 MQTT 发布结果
    if _worker:
        _worker.stream_out(task.task_id, "任务完成")
        _worker.complete(task.task_id, status="completed", result=_format_result(result))

    print(f"[MQTT] 任务完成: {task.task_id}")


def _make_prompt(msg):
    """将 MQTT TaskMessage 转为 LLM prompt（原BBS格式兼容）"""
    return f"""[任务协作]📋 你是一个 agent worker，在MQTT BBS上接任务并执行。
Broker: {_cfg.get('broker_host', '127.0.0.1')}:{_cfg.get('broker_port', 1883)}
你的名字: {_cfg.get('name', 'team_worker')}

## 当前任务
- 任务ID: {msg.task_id}
- 类型: {msg.type}
- 输入: {json.dumps(msg.input, ensure_ascii=False, indent=2)}
- 优先级: {msg.priority}
- 超时: {msg.timeout}s

请执行此任务，完成后用 on_done 提交结果。
长结果可以分多次 stream_out 输出。
"""


def _format_result(result):
    """格式化 LLM 返回的结果"""
    if isinstance(result, str):
        return {"text": result}
    return result
