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
    svc = BoardService()
    svc.start()
"""

import json, time, uuid, logging, os, sqlite3, threading
from typing import Optional, Callable
from pathlib import Path

from .client import BBSClient
from . import config as cfg

log = logging.getLogger("mqtt_bbs.board_service")

# ── 默认配置 ──
BOARDS_FILE = "boards.json"           # 同 HTTP 版格式
DEFAULT_BOARDS = {"agent-bbs-test": {"name": "default", "db": "agent_bbs.db"}}
UPLOAD_DIR = "bbs_files"
TOPIC_BBS = "bbs"                     # agent/bbs/{board}/...


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
        self._dbs = {}             # board_key → sqlite3 connection
        self._dbs_lock = threading.Lock()
        self._running = False
        self._client = BBSClient(agent_id, host=self._host, port=self._port)

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
        self._client.subscribe(f"{TOPIC_BBS}/+/file_chunk", self._on_file_chunk)
        self._client.subscribe(f"{TOPIC_BBS}/+/admin/reload", self._on_admin_reload)

        log.info(f"[{self.agent_id}] 🚀 BoardService 启动 ({len(self._boards)} boards)")

        try:
            while self._running:
                time.sleep(1)
        except KeyboardInterrupt:
            self.stop()

    def stop(self):
        """停止服务"""
        self._running = False
        for db in self._dbs.values():
            try:
                db.close()
            except Exception:
                pass
        self._dbs.clear()
        self._client.disconnect()
        log.info(f"[{self.agent_id}] 🛑 BoardService 停止")

    # ── Board 配置加载 ──

    def _load_boards(self):
        """从 boards.json 加载 board 配置（同 HTTP 版格式）"""
        boards_path = os.path.join(self._data_dir, BOARDS_FILE)
        if os.path.exists(boards_path):
            try:
                self._boards = json.load(open(boards_path, "r", encoding="utf-8"))
                log.info(f"加载 {len(self._boards)} boards 从 {boards_path}")
            except Exception as e:
                log.warning(f"加载 boards.json 失败: {e}, 使用默认配置")
                self._boards = dict(DEFAULT_BOARDS)
        else:
            self._boards = dict(DEFAULT_BOARDS)
            json.dump(DEFAULT_BOARDS, open(boards_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
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
        self._client.subscribe(f"{base}/file_chunk", self._on_file_chunk)
        log.debug(f"  已订阅 board: {board_key}")

    # ── 数据库管理 ──

    def _ensure_db(self, board_key: str, bconf: dict):
        """确保 board 的 SQLite 数据库存在并初始化表结构"""
        db_path = os.path.join(self._data_dir, bconf.get("db", f"{board_key}.db"))
        with self._dbs_lock:
            if board_key in self._dbs:
                return
            conn = sqlite3.connect(db_path, check_same_thread=False)
            conn.row_factory = sqlite3.Row
            conn.execute("""CREATE TABLE IF NOT EXISTS users (
                token TEXT PRIMARY KEY,
                name TEXT UNIQUE NOT NULL,
                created_at REAL NOT NULL
            )""")
            conn.execute("""CREATE TABLE IF NOT EXISTS posts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                author TEXT NOT NULL,
                content TEXT NOT NULL,
                created_at REAL NOT NULL
            )""")
            conn.commit()
            self._dbs[board_key] = conn
            log.info(f"  DB 就绪: {db_path} (board: {board_key})")

    def _get_db(self, board_key: str):
        """获取 board 对应的数据库连接"""
        return self._dbs.get(board_key)

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
        try:
            db.execute("INSERT INTO users VALUES(?,?,?)", (token, name, time.time()))
            db.commit()
        except sqlite3.IntegrityError:
            row = db.execute("SELECT token FROM users WHERE name=?", (name,)).fetchone()
            token = row["token"] if row else token

        resp_topic = f"{TOPIC_BBS}/{board_key}/register/response/{corr_id}"
        self._client.publish(resp_topic, {"token": token, "name": name}, retain=False, qos=1)
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

        # 验证 token
        row = db.execute("SELECT name FROM users WHERE token=?", (token,)).fetchone()
        if not row:
            log.warning(f"  ❌ 无效 token (board: {board_key})")
            resp_topic = f"{TOPIC_BBS}/{board_key}/post/response/{corr_id}"
            self._client.publish(resp_topic, {"error": "invalid token"}, retain=False, qos=1)
            return

        author = row["name"]
        cur = db.execute("INSERT INTO posts(author,content,created_at) VALUES(?,?,?)",
                         (author, content, time.time()))
        db.commit()
        post_id = cur.lastrowid
        created_at = time.time()

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

        if query_type == "posts":
            author = params.get("author")
            limit = int(params.get("limit", 50))
            offset = int(params.get("offset", 0))
            if author:
                rows = db.execute(
                    "SELECT id,author,content,created_at FROM posts WHERE author=? ORDER BY id DESC LIMIT ? OFFSET ?",
                    (author, limit, offset)
                ).fetchall()
            else:
                rows = db.execute(
                    "SELECT id,author,content,created_at FROM posts ORDER BY id DESC LIMIT ? OFFSET ?",
                    (limit, offset)
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
                row = db.execute("SELECT COUNT(*) as c FROM posts WHERE author=?", (author,)).fetchone()
            else:
                row = db.execute("SELECT COUNT(*) as c FROM posts").fetchone()
            result = {"total": row["c"] if row else 0}

        elif query_type == "authors":
            rows = db.execute("SELECT DISTINCT name FROM users ORDER BY name").fetchall()
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

    def _on_file_chunk(self, topic: str, payload):
        """文件上传请求: {agent_id, token, filename, data, corr_id}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        filename = payload.get("filename", "")
        data_b64 = payload.get("data", "")
        corr_id = payload.get("corr_id", "")
        if not token or not filename:
            return

        db = self._get_db(board_key)
        if not db:
            return

        # 验证 token
        row = db.execute("SELECT name FROM users WHERE token=?", (token,)).fetchone()
        if not row:
            return

        import base64
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
            log.info(f"  📎 文件上传: {ref} (board: {board_key})")
        except Exception as e:
            log.warning(f"  文件上传失败: {e}")

    def _on_admin_reload(self, topic: str, payload):
        """热加载 boards.json"""
        self._load_boards()
        # 为新 board 订阅主题
        for board_key in self._boards:
            if board_key not in [self._board_from_topic(s) for s in self._client._subscriptions]:
                self._subscribe_board(board_key)
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
        json.dump(self._boards, open(boards_path, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
        log.info(f"  ➕ 新增 board: {board_key}")


# ── 命令行入口 ──

def main():
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s.%(msecs)03d [%(name)s] %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
    )
    svc = BoardService()
    svc.start()


if __name__ == "__main__":
    main()
