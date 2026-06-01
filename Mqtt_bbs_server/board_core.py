"""
Board Service — 核心模块

从 board_service.py 拆分而来。
包含 BoardService 核心生命周期管理（init/start/stop）和 board 配置管理。
"""

import json
import time
import os
import threading
import signal
import pymysql

from Mqtt_bbs_client.client import BBSClient
from Mqtt_bbs_client import config as cfg
from .board_config import BOARDS_FILE, DEFAULT_BOARDS, TOPIC_BBS, log
from .board_db import CapabilityRegistry, MariaDBWrapper
from .board_handlers import BoardHandlers
from .plugin_manager import PluginManager


class BoardService:
    """
    MQTT Board Service.

    Manages boards with MariaDB persistence via MQTT pub/sub.
    Split from the original 940-line board_service.py.
    """

    def __init__(self, agent_id: str = "bbs-keeper",
                 host: str = None, port: int = None,
                 data_dir: str = None):
        self.agent_id = agent_id
        self._host = host or cfg.BROKER_HOST
        self._port = port or cfg.BROKER_PORT
        self._data_dir = data_dir or os.getcwd()
        self._boards = {}
        self._dbs = set()
        self._dbs_lock = threading.Lock()
        self._mariadb = None
        self._db_io_lock = threading.RLock()
        self._running = False
        self._client = BBSClient(agent_id, host=self._host, port=self._port)
        self._registry = CapabilityRegistry(self._client)
        self._webhooks: dict[str, list[str]] = {}
        self._plugin_mgr = PluginManager(self._client)
        self._healthcheck_enabled = os.environ.get("GATEWAY_HEALTHCHECK", "true").lower() == "true"
        self._start_time = time.time()
        self._subscribed_boards = set()
        # Handlers composition
        self._handlers = BoardHandlers(self)

    # ── Internal helpers ──

    def _get_db(self, board_key: str):
        """Get MariaDB connection wrapper"""
        if board_key in self._dbs and self._mariadb:
            return MariaDBWrapper(self._mariadb)
        return None

    def _board_from_topic(self, topic: str):
        parts = topic.split("/")
        if len(parts) >= 2:
            return parts[1]
        return None

    def _publish_event(self, board_key: str, event: str, data: dict):
        topic = f"{TOPIC_BBS}/{board_key}/events/{event}"
        self._plugin_mgr.trigger_event(topic, data)

    # ── Board config management ──

    def _load_boards(self):
        boards_path = os.path.join(self._data_dir, BOARDS_FILE)
        if os.path.exists(boards_path):
            try:
                with open(boards_path, "r", encoding="utf-8") as f:
                    self._boards = json.load(f)
                log.info(f"loaded {len(self._boards)} boards from {boards_path}")
            except Exception as e:
                log.warning(f"load boards.json failed: {e}, using defaults")
                self._boards = dict(DEFAULT_BOARDS)
        else:
            self._boards = dict(DEFAULT_BOARDS)
            with open(boards_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_BOARDS, f, ensure_ascii=False, indent=2)
            log.info(f"created default boards.json: {boards_path}")

        for key, bconf in self._boards.items():
            self._ensure_db(key, bconf)

    def _subscribe_board(self, board_key: str):
        base = f"{TOPIC_BBS}/{board_key}"
        self._client.subscribe(f"{base}/register", self._handlers.on_register)
        self._client.subscribe(f"{base}/post", self._handlers.on_post)
        self._client.subscribe(f"{base}/query", self._handlers.on_query)
        self._client.subscribe(f"{base}/file_init", self._handlers.on_file_init)
        self._client.subscribe(f"{base}/file_chunk", self._handlers.on_file_chunk)
        self._client.subscribe(f"{base}/file_commit", self._handlers.on_file_commit)
        self._client.subscribe(f"{base}/file_download", self._handlers.on_file_download)
        log.debug(f"  subscribed board: {board_key}")

    def add_board(self, board_key: str, name: str = None, db: str = None):
        bconf = {"name": name or board_key, "db": db or f"{board_key}.db"}
        self._boards[board_key] = bconf
        self._ensure_db(board_key, bconf)
        self._subscribe_board(board_key)
        boards_path = os.path.join(self._data_dir, BOARDS_FILE)
        with open(boards_path, "w", encoding="utf-8") as f:
            json.dump(self._boards, f, ensure_ascii=False, indent=2)
        log.info(f"  [ADD] board: {board_key}")

    def _ensure_db(self, board_key: str, bconf: dict):
        if self._mariadb is None:
            self._mariadb = pymysql.connect(
                host=cfg.DB_CONFIG["host"], port=cfg.DB_CONFIG["port"],
                user=cfg.DB_CONFIG["user"], password=cfg.DB_CONFIG["password"],
                database=cfg.DB_CONFIG["database"], charset=cfg.DB_CONFIG["charset"],
                cursorclass=pymysql.cursors.DictCursor
            )
        with self._dbs_lock:
            if board_key in self._dbs:
                return
            cur = self._mariadb.cursor()
            cur.execute("""CREATE TABLE IF NOT EXISTS bbs_users (
                token VARCHAR(512) PRIMARY KEY,
                name VARCHAR(128) NOT NULL UNIQUE,
                board VARCHAR(128) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
            try:
                cur.execute("ALTER TABLE bbs_users MODIFY token VARCHAR(512)")
            except Exception:
                pass
            cur.execute("""CREATE TABLE IF NOT EXISTS bbs_posts (
                id BIGINT AUTO_INCREMENT PRIMARY KEY,
                board VARCHAR(128) NOT NULL,
                author VARCHAR(64) NOT NULL,
                content LONGTEXT,
                created_at DATETIME(3) DEFAULT CURRENT_TIMESTAMP(3),
                KEY idx_board (board),
                KEY idx_author (author)
            )""")
            self._mariadb.commit()
            self._dbs.add(board_key)
            log.info(f"  MariaDB ready: board={board_key}")

    # ── Lifecycle ──

    def start(self):
        self._running = True
        self._client.connect()
        self._client.wait_connected(5)

        if not self._client.is_connected:
            log.error("cannot connect to MQTT Broker")
            return

        try:
            self._load_boards()
            for board_key in self._boards:
                self._subscribe_board(board_key)

            self._client.subscribe(f"{TOPIC_BBS}/+/register", self._handlers.on_register)
            self._client.subscribe(f"{TOPIC_BBS}/+/post", self._handlers.on_post)
            self._client.subscribe(f"{TOPIC_BBS}/+/query", self._handlers.on_query)
            self._client.subscribe(f"{TOPIC_BBS}/+/file_init", self._handlers.on_file_init)
            self._client.subscribe(f"{TOPIC_BBS}/+/file_chunk", self._handlers.on_file_chunk)
            self._client.subscribe(f"{TOPIC_BBS}/+/file_commit", self._handlers.on_file_commit)
            self._client.subscribe(f"{TOPIC_BBS}/+/file_download", self._handlers.on_file_download)
            self._client.subscribe(f"{TOPIC_BBS}/+/admin/reload", self._handlers.on_admin_reload)
            self._client.subscribe(f"{TOPIC_BBS}/+/webhook", self._handlers.on_webhook_config)

            self._registry.start()
            log.info(f"[{self.agent_id}] BoardService started ({len(self._boards)} boards)")

            loaded = self._plugin_mgr.discover_and_load()
            if loaded:
                log.info(f"[Plugin] loaded {len(loaded)} plugins: {', '.join(loaded)}")

            signal.signal(signal.SIGTERM, lambda *a: self.stop())

            if self._healthcheck_enabled:
                self._client.subscribe("system/healthcheck", self._handlers.on_healthcheck)
                self._client.subscribe("system/healthcheck/liveness", self._handlers.on_hc_liveness)
                self._client.subscribe("system/healthcheck/readiness", self._handlers.on_hc_readiness)
                log.info("  Healthcheck enabled: system/healthcheck, /liveness, /readiness")
        except Exception as e:
            log.error(f"BoardService init failed: {e}")
            import traceback; traceback.print_exc()
            self.stop()
            return

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        self._running = False
        for name in list(self._plugin_mgr.list_plugins()):
            self._plugin_mgr.unload(name["name"])
        self._registry.stop()
        if self._mariadb:
            try:
                self._mariadb.close()
            except Exception:
                pass
        self._dbs.clear()
        self._mariadb = None
        self._client.disconnect()
        log.info(f"[{self.agent_id}] [STOP] BoardService stopped")


def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    try:
        svc = BoardService()
        svc.start()
    except KeyboardInterrupt:
        log.info("BoardService interrupted, shutting down...")
    except Exception as e:
        log.error(f"BoardService start failed: {e}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    main()
