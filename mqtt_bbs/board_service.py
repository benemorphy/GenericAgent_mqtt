"""
Board Service — MQTT 公告板持久化服务

对标 HTTP agent_bbs.py 的 SQLite 持久化 + 业务逻辑，
改为 MQTT Pub/Sub 驱动。

架构:
    Agent (MQTT Client) ←→ MQTT Broker ←→ BoardService (本服务)
                                                ↓
                                             SQLite

启动:
    python -m mqtt_bbs.board_service

或:
    from mqtt_bbs.board_service import BoardService
    try:
        svc = BoardService()
        svc.start()
    except KeyboardInterrupt:
        log.info("BoardService 收到中断信号，正在关闭...")
    except Exception as e:
        log.error(f"BoardService 启动失败: {e}")
        import traceback; traceback.print_exc()
"""

import json, datetime, uuid, logging, os, threading
import pymysql
from typing import Optional, Callable
from pathlib import Path

from .client import BBSClient
from . import config as cfg
from .plugin_manager import PluginManager

log = logging.getLogger("mqtt_bbs.board_service")

# ── 默认配置 ──
BOARDS_FILE = "boards.json"           # 同 HTTP 版格式
DEFAULT_BOARDS = {"agent-bbs-test": {"name": "default", "db": "agent_bbs.db"},
                  "agent-inspiration": {"name": "灵感板", "db": "agent_inspiration.db"},
                  "agent-whiteboard": {"name": "白板", "db": "agent_whiteboard.db"}}
UPLOAD_DIR = "bbs_files"
TOPIC_BBS = "bbs"                     # agent/bbs/{board}/...

# ── Webhook 辅助 ──
def _webhook_send(url: str, data: dict):
    """发送 webhook 回调（在独立线程中执行）"""
    import requests as _req
    try:
        _r = _req.post(url, json=data, timeout=5)
        log.info(f"  🌐 Webhook 发送成功: {url} ({_r.status_code})")
    except Exception as e:
        log.warning(f"  🌐 Webhook 失败: {url} → {e}")

# ── CapabilityRegistry ──
# BoardService 内置的能力注册表，监听 node/+/capability + heartbeat
# 提供 board/capability/query 查询接口
class CapabilityRegistry:
    """
    MQTT 驱动的 Agent 能力注册表。

    通过订阅 node/{agent_id}/capability（retain）获取能力声明，
    通过 node/{agent_id}/heartbeat 获取心跳维持活性，
    通过 node/{agent_id}/status（含 LWT）检测离线。
    """

    def __init__(self, client: BBSClient):
        self._client = client
        self._lock = threading.Lock()
        # agent_id → {capabilities, status, last_seen, agent_id}
        self._agents: dict[str, dict] = {}
        self._cleanup_timer: Optional[threading.Thread] = None
        self._running = False

    def start(self):
        """启动注册表：订阅相关主题"""
        self._running = True
        # 订阅能力声明（retain 消息会在连接后立即收到）
        self._client.subscribe("node/+/capability", self._on_capability)
        # 订阅心跳
        self._client.subscribe("node/+/heartbeat", self._on_heartbeat)
        # 订阅状态变更（含 LWT 离线）
        self._client.subscribe("node/+/status", self._on_status)
        # 订阅查询请求
        self._client.subscribe("board/capability/query", self._on_query)
        # 启动过期清理线程
        self._cleanup_timer = threading.Thread(target=self._cleanup_loop, daemon=True)
        self._cleanup_timer.start()
        log.info("[CapabilityRegistry] 🚀 启动")

    def stop(self):
        self._running = False

    def get_agents(self, capability: Optional[str] = None) -> list[dict]:
        """获取注册的 Agent 列表，可选按能力过滤"""
        with self._lock:
            agents = list(self._agents.values())
        if capability:
            agents = [a for a in agents if capability in a.get("capabilities", [])]
        return agents

    def get_agent(self, agent_id: str) -> Optional[dict]:
        with self._lock:
            return self._agents.get(agent_id)

    # ── 内部消息处理 ──

    def _on_capability(self, topic: str, payload):
        """处理能力声明: node/{agent_id}/capability"""
        parts = topic.split("/")
        if len(parts) < 3:
            return
        agent_id = parts[1]
        caps = []
        if isinstance(payload, dict):
            caps = payload.get("capabilities", [])
        with self._lock:
            if agent_id not in self._agents:
                self._agents[agent_id] = {"agent_id": agent_id, "capabilities": [], "status": "unknown", "last_seen": time.time()}
            self._agents[agent_id]["capabilities"] = caps
            self._agents[agent_id]["last_seen"] = time.time()
        log.info(f"  📋 能力声明: {agent_id} → {caps}")

    def _on_heartbeat(self, topic: str, payload):
        """处理心跳: node/{agent_id}/heartbeat"""
        parts = topic.split("/")
        if len(parts) < 3:
            return
        agent_id = parts[1]
        caps = []
        load = None
        if isinstance(payload, dict):
            caps = payload.get("capabilities", [])
            load = payload.get("load")
        with self._lock:
            if agent_id not in self._agents:
                self._agents[agent_id] = {"agent_id": agent_id, "capabilities": [], "status": "online", "last_seen": time.time()}
            if caps:
                self._agents[agent_id]["capabilities"] = caps
            self._agents[agent_id]["status"] = "online"
            self._agents[agent_id]["last_seen"] = time.time()
            if load is not None:
                self._agents[agent_id]["load"] = load

    def _on_status(self, topic: str, payload):
        """处理状态变更（含 LWT 离线信号）: node/{agent_id}/status"""
        parts = topic.split("/")
        if len(parts) < 3:
            return
        agent_id = parts[1]
        status = "online"
        if isinstance(payload, bytes):
            status = payload.decode("utf-8")
        elif isinstance(payload, str):
            status = payload
        with self._lock:
            if agent_id not in self._agents:
                self._agents[agent_id] = {"agent_id": agent_id, "capabilities": [], "status": status, "last_seen": time.time()}
            else:
                self._agents[agent_id]["status"] = status
                if status == "online":
                    self._agents[agent_id]["last_seen"] = time.time()
        log.info(f"  🔵 状态变更: {agent_id} → {status}")

    def _on_query(self, topic: str, payload):
        """处理能力查询请求: board/capability/query"""
        corr_id = ""
        capability_filter = None
        if isinstance(payload, dict):
            corr_id = payload.get("corr_id", "")
            capability_filter = payload.get("capability")
        agents = self.get_agents(capability_filter)
        resp = {
            "type": "capability_list",
            "agents": agents,
            "count": len(agents),
            "timestamp": time.time(),
        }
        if corr_id:
            self._client.publish(f"board/capability/query/response/{corr_id}", resp, retain=False)
        else:
            # 无 corr_id 则直接回复到通用响应主题
            self._client.publish("board/capability/query/response", resp, retain=False)
        log.info(f"  🔍 能力查询: filter={capability_filter} → {len(agents)} agents")

    def _cleanup_loop(self):
        """定期清理过期 Agent（HEARTBEAT_TIMEOUT 无心跳标记为 offline）"""
        while self._running:
            time.sleep(cfg.HEARTBEAT_INTERVAL)
            now = time.time()
            expired = []
            with self._lock:
                for agent_id, info in self._agents.items():
                    if info.get("status") == "offline":
                        continue
                    last_seen = info.get("last_seen", 0)
                    if now - last_seen > cfg.HEARTBEAT_TIMEOUT:
                        info["status"] = "offline"
                        expired.append(agent_id)
            if expired:
                log.warning(f"  ⏰ 心跳超时标记离线: {expired}")


class BoardService:
    """
    MQTT 公告板服务。

    监听主题: agent/bbs/{board}/register, agent/bbs/{board}/post, agent/bbs/{board}/query
    持久化到 SQLite，返回结果到响应主题。
    """

    def __init__(self, agent_id: str = "board-keeper",
                 host: str = None, port: int = None,
                 data_dir: str = None):
        self.agent_id = agent_id
        self._host = host or cfg.BROKER_HOST
        self._port = port or cfg.BROKER_PORT
        self._data_dir = data_dir or os.getcwd()
        self._boards = {}          # board_key → config
        self._dbs = set()            # board_key 集合
        self._dbs_lock = threading.Lock()
        self._mariadb = None  # MariaDB 连接（延迟初始化）
        self._db_io_lock = threading.RLock()  # SQLite 线程安全锁（所有DB操作共用）
        self._running = False
        self._client = BBSClient(agent_id, host=self._host, port=self._port)
        self._registry = CapabilityRegistry(self._client)
        self._webhooks: dict[str, list[str]] = {}  # board_key → [webhook_urls]
        self._plugin_mgr = PluginManager(self._client)

    # ── 公开 API ──

    def start(self):
        """启动服务（阻塞）"""
        self._running = True
        self._client.connect()
        self._client.wait_connected(5)

        if not self._client.is_connected:
            log.error("无法连接到 MQTT Broker")
            return

        # 加载 board 配置
        self._load_boards()

        # 订阅所有 board 的管理主题
        for board_key in self._boards:
            self._subscribe_board(board_key)

        # 同时也监听 boards.json 变更（热加载）
        self._client.subscribe(f"{TOPIC_BBS}/+/register", self._on_register)
        self._client.subscribe(f"{TOPIC_BBS}/+/post", self._on_post)
        self._client.subscribe(f"{TOPIC_BBS}/+/query", self._on_query)
        self._client.subscribe(f"{TOPIC_BBS}/+/file_init", self._on_file_init)
        self._client.subscribe(f"{TOPIC_BBS}/+/file_chunk", self._on_file_chunk)
        self._client.subscribe(f"{TOPIC_BBS}/+/file_commit", self._on_file_commit)
        self._client.subscribe(f"{TOPIC_BBS}/+/file_download", self._on_file_download)
        self._client.subscribe(f"{TOPIC_BBS}/+/admin/reload", self._on_admin_reload)
        self._client.subscribe(f"{TOPIC_BBS}/+/webhook", self._on_webhook_config)

        # 启动能力注册表
        self._registry.start()

        log.info(f"[{self.agent_id}] 🚀 BoardService 启动 ({len(self._boards)} boards)")

        # 启动插件系统
        loaded = self._plugin_mgr.discover_and_load()
        if loaded:
            log.info(f"[Plugin] 已加载 {len(loaded)} 个插件: {', '.join(loaded)}")

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止服务"""
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
        log.info(f"[{self.agent_id}] 🛑 BoardService 停止")

    # ── 事件发布（供插件系统使用）──

    def _publish_event(self, board_key: str, event: str, data: dict):
        """发布 events 主题，供插件订阅"""
        topic = f"{TOPIC_BBS}/{board_key}/events/{event}"
        self._plugin_mgr.trigger_event(topic, data)

    # ── Board 配置加载 ──

    def _load_boards(self):
        """从 boards.json 加载 board 配置（同 HTTP 版格式）"""
        boards_path = os.path.join(self._data_dir, BOARDS_FILE)
        if os.path.exists(boards_path):
            try:
                with open(boards_path, "r", encoding="utf-8") as f:
                    self._boards = json.load(f)
                log.info(f"加载 {len(self._boards)} boards 从 {boards_path}")
            except Exception as e:
                log.warning(f"加载 boards.json 失败: {e}, 使用默认配置")
                self._boards = dict(DEFAULT_BOARDS)
        else:
            self._boards = dict(DEFAULT_BOARDS)
            with open(boards_path, "w", encoding="utf-8") as f:
                json.dump(DEFAULT_BOARDS, f, ensure_ascii=False, indent=2)
            log.info(f"创建默认 boards.json: {boards_path}")

        # 确保每个 board 的 DB 已初始化
        for key, bconf in self._boards.items():
            self._ensure_db(key, bconf)

    def _subscribe_board(self, board_key: str):
        """订阅单个 board 的所有管理主题（全量通配）"""
        base = f"{TOPIC_BBS}/{board_key}"
        self._client.subscribe(f"{base}/register", self._on_register)
        self._client.subscribe(f"{base}/post", self._on_post)
        self._client.subscribe(f"{base}/query", self._on_query)
        self._client.subscribe(f"{base}/file_init", self._on_file_init)
        self._client.subscribe(f"{base}/file_chunk", self._on_file_chunk)
        self._client.subscribe(f"{base}/file_commit", self._on_file_commit)
        self._client.subscribe(f"{base}/file_download", self._on_file_download)
        log.debug(f"  已订阅 board: {board_key}")

    # ── 数据库管理 ──

    def _ensure_db(self, board_key: str, bconf: dict):
        """确保 board 的 MariaDB 表存在"""
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
                token VARCHAR(32) PRIMARY KEY,
                name VARCHAR(128) NOT NULL UNIQUE,
                board VARCHAR(128) NOT NULL,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            )""")
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
            log.info(f"  MariaDB 就绪: board={board_key}")

    def _get_db(self, board_key: str):
        """获取 MariaDB 连接"""
        return self._mariadb if board_key in self._dbs else None

    def _board_from_topic(self, topic: str) -> Optional[str]:
        """从 topic 中提取 board_key, 形如 bbs/{board_key}/..."""
        parts = topic.split("/")
        if len(parts) >= 2:
            return parts[1]
        return None

    # ── 消息处理器 ──

    def _on_register(self, topic: str, payload):
        """注册请求: {agent_id, name} → 返回 {token, name}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        agent_id = payload.get("agent_id", "")
        name = payload.get("name", "")
        corr_id = payload.get("corr_id", agent_id)
        if not name:
            return

        db = self._get_db(board_key)
        if not db:
            return

        token = uuid.uuid4().hex[:16]
        with self._db_io_lock:
            try:
                db.execute("INSERT INTO bbs_users(token,name,board) VALUES(%s,%s,%s)", (token, name, board_key))
                db.commit()
            except pymysql.err.IntegrityError:
                row = db.execute("SELECT token FROM bbs_users WHERE name=%s AND board=%s", (name, board_key)).fetchone()
                token = row["token"] if row else token

        resp_topic = f"{TOPIC_BBS}/{board_key}/register/response/{corr_id}"
        self._client.publish(resp_topic, {"token": token, "name": name}, retain=False, qos=1)
        self._publish_event(board_key, "register", {"agent_id": name, "token": token, "board": board_key})
        log.info(f"  ✅ 注册: {name} → token={token[:8]}... (board: {board_key})")

    def _on_post(self, topic: str, payload):
        """发帖请求: {agent_id, token, content, corr_id} → 存储并广播"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        content = payload.get("content", "")
        corr_id = payload.get("corr_id", "")
        if not token or not content:
            return

        db = self._get_db(board_key)
        if not db:
            return

        with self._db_io_lock:
            # 验证 token
            row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
            if not row:
                log.warning(f"  ❌ 无效 token (board: {board_key})")
                resp_topic = f"{TOPIC_BBS}/{board_key}/post/response/{corr_id}"
                self._client.publish(resp_topic, {"error": "invalid token"}, retain=False, qos=1)
                return

            author = row["name"]
            cur = db.execute("INSERT INTO bbs_posts(board,author,content,created_at) VALUES(%s,%s,%s,NOW(3))",
                             (board_key, author, content))
            db.commit()
            post_id = cur.lastrowid
            created_at = time.time()
            self._publish_event(board_key, "post", {"post_id": post_id, "author": author, "board": board_key})

        # 响应给发布者
        if corr_id:
            resp_topic = f"{TOPIC_BBS}/{board_key}/post/response/{corr_id}"
            self._client.publish(resp_topic, {
                "id": post_id, "author": author, "created_at": created_at
            }, retain=False, qos=1)

        # 广播给所有订阅者
        broadcast = {
            "id": post_id, "author": author, "content": content, "created_at": created_at
        }
        self._client.publish(f"{TOPIC_BBS}/{board_key}/new_post", broadcast, retain=False, qos=0)
        log.info(f"  📝 新帖 #{post_id} by {author} (board: {board_key})")

        # ── Webhook: 转发新帖到配置的 URL ──
        if board_key in self._webhooks:
            for url in self._webhooks[board_key]:
                try:
                    import threading as _th
                    _th.Thread(target=_webhook_send, args=(url, {
                        "board": board_key, "event": "new_post",
                        "post_id": post_id, "author": author, "content": content,
                    }), daemon=True).start()
                except Exception as _e:
                    log.warning(f"  Webhook 发送失败: {url} → {_e}")

    def _on_webhook_config(self, topic: str, payload):
        """Webhook 配置: {action: "set"|"del", url: "...", board: "..."}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        action = payload.get("action", "set")
        url = payload.get("url", "")
        if not url:
            return
        if action == "set":
            self._webhooks.setdefault(board_key, [])
            if url not in self._webhooks[board_key]:
                self._webhooks[board_key].append(url)
                log.info(f"  🌐 注册 webhook: {board_key} → {url}")
        elif action == "del":
            if board_key in self._webhooks:
                self._webhooks[board_key] = [u for u in self._webhooks[board_key] if u != url]
                log.info(f"  🌐 删除 webhook: {board_key} → {url}")

    def _on_query(self, topic: str, payload):
        """查询请求: {agent_id, type, params, corr_id} → 返回查询结果"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        query_type = payload.get("type", "")
        params = payload.get("params", {})
        corr_id = payload.get("corr_id", "")

        db = self._get_db(board_key)
        if not db or not corr_id:
            return

        result = None

        with self._db_io_lock:
            if query_type == "posts":
                author = params.get("author")
                limit = int(params.get("limit", 50))
                offset = int(params.get("offset", 0))
                if author:
                    rows = db.execute(
                        "SELECT id,author,content,created_at FROM bbs_posts WHERE board=%s AND author=%s ORDER BY id DESC LIMIT %s OFFSET %s",
                        (board_key, author, limit, offset)
                    ).fetchall()
                else:
                    rows = db.execute(
                        "SELECT id,author,content,created_at FROM bbs_posts WHERE board=%s ORDER BY id DESC LIMIT %s OFFSET %s",
                        (board_key, limit, offset)
                    ).fetchall()
                result = [dict(r) for r in rows]

            elif query_type == "poll":
                since_id = int(params.get("since_id", 0))
                limit = int(params.get("limit", 50))
                rows = db.execute(
                    "SELECT id,author,content,created_at FROM posts WHERE id>? ORDER BY id LIMIT ?",
                    (since_id, limit)
                ).fetchall()
                result = [dict(r) for r in rows]

            elif query_type == "count":
                author = params.get("author")
                if author:
                    row = db.execute("SELECT COUNT(*) as c FROM bbs_posts WHERE board=%s AND author=%s", (board_key, author)).fetchone()
                else:
                    row = db.execute("SELECT COUNT(*) as c FROM bbs_posts WHERE board=%s", (board_key,)).fetchone()
                result = {"total": row["c"] if row else 0}

            elif query_type == "authors":
                rows = db.execute("SELECT DISTINCT name FROM bbs_users WHERE board=%s ORDER BY name", (board_key,)).fetchall()
                result = [r["name"] for r in rows]

            elif query_type == "since":
                """GET /poll 等效: 返回 ID 大于 since_id 的新帖"""
                since_id = int(params.get("since_id", 0))
                limit = int(params.get("limit", 50))
                rows = db.execute(
                    "SELECT id,author,content,created_at FROM posts WHERE id>? ORDER BY id LIMIT ?",
                    (since_id, limit)
                ).fetchall()
                result = [dict(r) for r in rows]

        resp_topic = f"{TOPIC_BBS}/{board_key}/query/response/{corr_id}"
        self._client.publish(resp_topic, {"type": query_type, "data": result}, retain=False, qos=1)
        log.debug(f"  🔍 查询: {query_type} (board: {board_key}, corr: {corr_id[:8]})")

    def _on_file_init(self, topic: str, payload):
        """文件分片上传初始化: {token, filename, total_size, chunk_count, corr_id}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        filename = payload.get("filename", "")
        total_size = payload.get("total_size", 0)
        chunk_count = payload.get("chunk_count", 0)
        corr_id = payload.get("corr_id", "")
        if not token or not filename:
            return

        db = self._get_db(board_key)
        if not db:
            return
        row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
        if not row:
            return

        import base64
        session_id = uuid.uuid4().hex[:12]
        safe_name = os.path.basename(filename)
        session_dir = os.path.join(self._data_dir, UPLOAD_DIR, board_key, f"chunk_{session_id}")
        os.makedirs(session_dir, exist_ok=True)

        # 保存 session 元信息
        meta = {"session_id": session_id, "filename": safe_name, "total_size": total_size,
                "chunk_count": chunk_count, "received": 0, "board_key": board_key}
        meta_path = os.path.join(session_dir, "_meta.json")
        with open(meta_path, "w") as f:
            json.dump(meta, f)

        if corr_id:
            resp_topic = f"{TOPIC_BBS}/{board_key}/file/response/{corr_id}"
            self._client.publish(resp_topic, {"session_id": session_id}, retain=False, qos=1)
        log.info(f"  📋 分片初始化: {safe_name} ({total_size}B, {chunk_count} chunks) → {session_id}")

    def _on_file_chunk(self, topic: str, payload):
        """文件上传/分片上传请求

        兼容两种模式:
        - 旧版单chunk: {token, filename, data(base64), corr_id}
        - 新版分片:   {token, session_id, seq, data(base64), corr_id}
        """
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        corr_id = payload.get("corr_id", "")
        if not token:
            return

        db = self._get_db(board_key)
        if not db:
            return
        row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
        if not row:
            return

        import base64

        # ── 新版分片模式 ──
        session_id = payload.get("session_id")
        if session_id:
            seq = payload.get("seq", 0)
            data_b64 = payload.get("data", "")
            if not data_b64:
                return
            session_dir = os.path.join(self._data_dir, UPLOAD_DIR, board_key, f"chunk_{session_id}")
            meta_path = os.path.join(session_dir, "_meta.json")
            if not os.path.exists(meta_path):
                return
            chunk_path = os.path.join(session_dir, f"{seq:04d}.chunk")
            try:
                chunk_bytes = base64.b64decode(data_b64)
                with open(chunk_path, "wb") as f:
                    f.write(chunk_bytes)
                # 更新 meta
                with open(meta_path) as f:
                    meta = json.load(f)
                meta["received"] = meta.get("received", 0) + 1
                with open(meta_path, "w") as f:
                    json.dump(meta, f)
                if corr_id:
                    resp_topic = f"{TOPIC_BBS}/{board_key}/file/response/{corr_id}"
                    self._client.publish(resp_topic, {"session_id": session_id, "seq": seq}, retain=False, qos=1)
                log.info(f"  🧩 分片 {seq}: {len(chunk_bytes)}B (session: {session_id[:8]}...)")
            except Exception as e:
                log.warning(f"  分片写入失败: {e}")
            return

        # ── 旧版单chunk模式 ──
        filename = payload.get("filename", "")
        data_b64 = payload.get("data", "")
        if not filename or not data_b64:
            return
        rand_id = uuid.uuid4().hex[:6]
        safe_name = os.path.basename(filename)
        board_upload_dir = os.path.join(self._data_dir, UPLOAD_DIR, board_key, rand_id)
        os.makedirs(board_upload_dir, exist_ok=True)
        filepath = os.path.join(board_upload_dir, safe_name)
        try:
            file_bytes = base64.b64decode(data_b64)
            with open(filepath, "wb") as f:
                f.write(file_bytes)
            ref = f"{rand_id}/{safe_name}"
            if corr_id:
                resp_topic = f"{TOPIC_BBS}/{board_key}/file/response/{corr_id}"
                self._client.publish(resp_topic, {"ref": ref}, retain=False, qos=1)
            log.info(f"  📎 文件上传(单chunk): {ref} (board: {board_key})")
        except Exception as e:
            log.warning(f"  文件上传失败: {e}")

    def _on_file_commit(self, topic: str, payload):
        """文件分片合并: {token, session_id, corr_id}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        session_id = payload.get("session_id", "")
        corr_id = payload.get("corr_id", "")
        if not token or not session_id:
            return

        db = self._get_db(board_key)
        if not db:
            return
        row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
        if not row:
            return

        session_dir = os.path.join(self._data_dir, UPLOAD_DIR, board_key, f"chunk_{session_id}")
        meta_path = os.path.join(session_dir, "_meta.json")
        if not os.path.exists(meta_path):
            return

        with open(meta_path) as f:
            meta = json.load(f)
        chunk_count = meta.get("chunk_count", 0)
        received = meta.get("received", 0)

        if received < chunk_count:
            log.warning(f"  ⚠️ 分片不完整: {received}/{chunk_count}")
            if corr_id:
                resp_topic = f"{TOPIC_BBS}/{board_key}/file/response/{corr_id}"
                self._client.publish(resp_topic, {"error": f"incomplete: {received}/{chunk_count}"}, retain=False, qos=1)
            return

        # 合并分片
        target_dir = os.path.join(self._data_dir, UPLOAD_DIR, board_key, session_id[:6])
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, meta["filename"])
        with open(target_path, "wb") as out:
            for seq in range(chunk_count):
                chunk_path = os.path.join(session_dir, f"{seq:04d}.chunk")
                if os.path.exists(chunk_path):
                    with open(chunk_path, "rb") as cf:
                        out.write(cf.read())

        # 清理临时分片目录
        import shutil
        shutil.rmtree(session_dir, ignore_errors=True)

        file_ref = f"{session_id[:6]}/{meta['filename']}"
        if corr_id:
            resp_topic = f"{TOPIC_BBS}/{board_key}/file/response/{corr_id}"
            self._client.publish(resp_topic, {"ref": file_ref}, retain=False, qos=1)
        log.info(f"  ✅ 分片合并: {file_ref} ({received} chunks)")

    def _on_file_download(self, topic: str, payload):
        """文件下载: {token, file_ref, corr_id}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        file_ref = payload.get("file_ref", "")
        corr_id = payload.get("corr_id", "")
        if not token or not file_ref:
            return

        db = self._get_db(board_key)
        if not db:
            return
        row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
        if not row:
            return

        board_upload_dir = os.path.join(self._data_dir, UPLOAD_DIR, board_key)
        filepath = os.path.join(board_upload_dir, file_ref)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            import base64
            with open(filepath, "rb") as dlf:
                file_bytes = dlf.read()
            data_b64 = base64.b64encode(file_bytes).decode()
            if corr_id:
                resp_topic = f"{TOPIC_BBS}/{board_key}/file/response/{corr_id}"
                self._client.publish(resp_topic, {"ref": file_ref, "data": data_b64, "size": len(file_bytes)}, retain=False, qos=1)
            log.info(f"  📥 文件下载: {file_ref} ({len(file_bytes)}B)")
        else:
            if corr_id:
                resp_topic = f"{TOPIC_BBS}/{board_key}/file/response/{corr_id}"
                self._client.publish(resp_topic, {"error": "not_found"}, retain=False, qos=1)

    def _on_admin_reload(self, topic: str, payload):
        """热加载 boards.json"""
        self._load_boards()
        # 取消已删除 board 的订阅 + 为新 board 订阅
        subscribed = getattr(self, '_subscribed_boards', set())
        for board_key in list(subscribed):
            if board_key not in self._boards:
                subscribed.discard(board_key)
        for board_key in self._boards:
            if board_key not in subscribed:
                self._subscribe_board(board_key)
                subscribed.add(board_key)
        self._subscribed_boards = subscribed
        log.info("  🔄 boards 热加载完成")

    # ── 便捷方法 ──

    def add_board(self, board_key: str, name: str = None, db: str = None):
        """动态添加 board"""
        bconf = {"name": name or board_key, "db": db or f"{board_key}.db"}
        self._boards[board_key] = bconf
        self._ensure_db(board_key, bconf)
        self._subscribe_board(board_key)
        # 持久化到 boards.json
        boards_path = os.path.join(self._data_dir, BOARDS_FILE)
        with open(boards_path, "w", encoding="utf-8") as f:
            json.dump(self._boards, f, ensure_ascii=False, indent=2)
        log.info(f"  ➕ 新增 board: {board_key}")


# ── 命令行入口 ──

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
        log.info("BoardService 收到中断信号，正在关闭...")
    except Exception as e:
        log.error(f"BoardService 启动失败: {e}")
        import traceback; traceback.print_exc()


if __name__ == "__main__":
    main()
