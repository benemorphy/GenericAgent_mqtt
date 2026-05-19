"""
MQTT Agent BBS — 智能体协作消息总线 (MariaDB持久化模式)

对标当前 subagent 文件协议 (input.txt / output.txt / [ROUND END])，
用 MQTT 主题树实现任务分发、流式反馈、结果收集 + MariaDB 持久化。

快速开始:
    from mqtt_bbs import AgentBoardWithPersistence, WorkerAgentWithPersistence

    # 主智能体：发布任务（自动持久化）
    master = AgentBoardWithPersistence("master_alpha")
    task_id = master.post_task("analyse_log", {"path": "/var/log"})
    result = master.wait_task(task_id)

    # 工作智能体：认领并执行
    worker = WorkerAgentWithPersistence("worker_01")
    worker.start()
"""

from .persistence import BBSClientWithPersistence, MariaDBConn, AgentBoardWithPersistence, WorkerAgentWithPersistence

__version__ = "0.2.0"
