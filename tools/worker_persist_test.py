"""
持久化版 WorkerAgent + AgentBoardWithPersistence 测试
- 用 WorkerAgentWithPersistence 启动 worker
- 用 AgentBoardWithPersistence 发布任务
- 验证 MariaDB 写入
"""
import sys, os, time, json, logging
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ["MQTT_HOST"] = "127.0.0.1"
os.environ["MQTT_PORT"] = "1883"

logging.basicConfig(level=logging.INFO, format="%(name)s | %(message)s")
log = logging.getLogger("persist_test")

from mqtt_bbs.persistence import WorkerAgentWithPersistence, AgentBoardWithPersistence

# ── Worker 任务处理函数 ──
def task_handler(task):
    """模拟处理 analyse_log / scan 任务"""
    log.info(f"📥 收到任务: {task.type} | input={task.input}")
    
    # 模拟处理延迟
    time.sleep(0.5)
    
    if task.type == "analyse_log":
        return {
            "total_lines": 2048,
            "errors": 5,
            "warnings": 18,
            "top_ips": ["192.168.1.1", "10.0.0.5"],
            "analysis": "persisted test result",
        }
    elif task.type == "scan":
        return {
            "target": task.input.get("target", "unknown"),
            "open_ports": [22, 80, 443, 8080],
            "hosts_up": 3,
            "scan_duration": "2.3s",
        }
    else:
        return {"status": "unknown_type", "received_type": task.type}


if __name__ == "__main__":
    import threading
    
    mode = sys.argv[1] if len(sys.argv) > 1 else "all"
    
    if mode in ("all", "worker"):
        log.info("=" * 60)
        log.info("🚀 [PERSIST] 启动持久化 WorkerAgent")
        log.info("=" * 60)
        
        worker = WorkerAgentWithPersistence(
            "persist_worker",
            capabilities=["analyse_log", "scan"],
        )
        worker.on_task(task_handler)
        worker.start(block=(mode == "worker"))
    
    if mode in ("all", "master"):
        # 等 worker 启动
        time.sleep(2)
        
        log.info("=" * 60)
        log.info("🚀 [PERSIST] AgentBoardWithPersistence 发布任务")
        log.info("=" * 60)
        
        with AgentBoardWithPersistence("persist_master") as board:
            # 任务1: analyse_log
            log.info("\n📋 [PERSIST] 发布任务1: analyse_log")
            task1 = board.post_task("analyse_log", {
                "path": "/var/log/nginx",
                "pattern": "error",
                "source": "persistence_test",
            })
            log.info(f"   Task ID: {task1}")
            
            output1 = board.wait_task(task1, timeout=30)
            log.info(f"   状态: {output1.status}")
            log.info(f"   Agent: {output1.agent_id}")
            log.info(f"   结果: {json.dumps(output1.result, ensure_ascii=False)}")
            
            # 任务2: scan
            log.info("\n📋 [PERSIST] 发布任务2: scan")
            task2 = board.post_task("scan", {
                "target": "10.0.0.0/24",
                "ports": [22, 80, 443],
                "source": "persistence_test",
            })
            log.info(f"   Task ID: {task2}")
            
            output2 = board.wait_task(task2, timeout=30)
            log.info(f"   状态: {output2.status}")
            log.info(f"   Agent: {output2.agent_id}")
            log.info(f"   结果: {json.dumps(output2.result, ensure_ascii=False)}")
        
        log.info("\n" + "=" * 60)
        log.info("✅ [PERSIST] 所有任务完成！")
        log.info("=" * 60)
        
        # 最后验证数据库
        log.info("\n📊 验证 MariaDB 持久化...")
        try:
            import pymysql
            from pymysql.cursors import DictCursor
            conn = pymysql.connect(
                host="127.0.0.1", port=3306,
                user="root", password="mariadb",
                database="mqtt_bbs", charset="utf8mb4",
                cursorclass=DictCursor, autocommit=True
            )
            with conn.cursor() as cur:
                cur.execute("SELECT COUNT(*) as cnt FROM agent_sessions WHERE status='online'")
                online = cur.fetchone()['cnt']
                cur.execute("SELECT COUNT(*) as cnt FROM agent_sessions WHERE agent_id LIKE 'persist_%'")
                persist_agents = cur.fetchone()['cnt']
                cur.execute("SELECT COUNT(*) as cnt FROM retained_messages")
                retained = cur.fetchone()['cnt']
                cur.execute("SELECT COUNT(*) as cnt FROM retained_messages WHERE source_agent LIKE 'persist_%'")
                persist_msgs = cur.fetchone()['cnt']
                log.info(f"   agent_sessions: {online} online / {persist_agents} persist_* 的 session")
                log.info(f"   retained_messages: {retained} 总行 / {persist_msgs} 条来自 persist_*")
            conn.close()
        except Exception as e:
            log.error(f"   DB 验证失败: {e}")
