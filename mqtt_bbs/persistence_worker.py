"""
MariaDB 持久化 Worker — 常驻运行，保存所有 MQTT BBS 消息到 MariaDB

启动:
    python mqtt_bbs/persistence_worker.py
"""
import logging, time, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")

from mqtt_bbs.persistence import BBSClientWithPersistence

def main():
    worker = BBSClientWithPersistence("persist_writer")
    worker.start()
    try:
        while True:
            time.sleep(10)
    except KeyboardInterrupt:
        worker.stop()

if __name__ == "__main__":
    main()
