"""
Board Service — MQTT 消息处理器模块

从 board_service.py 拆分而来。
包含 BoardService 中所有 _on_* MQTT 消息处理方法。
"""

import json
import time
import os
import base64
import threading as _th
import pymysql

from .board_config import TOPIC_BBS, webhook_send, log


class BoardHandlers:
    """
    MQTT message handlers for BoardService.

    These handlers are mixed into BoardService via composition.
    They require BoardService to provide:
      - _board_from_topic(topic) -> str
      - _get_db(board_key) -> MariaDBWrapper
      - _publish_event(board_key, event, data)
      - _client (BBSClient)
      - _plugin_mgr (PluginManager)
      - _webhooks
      - _data_dir
      - _mariadb
      - _running, _start_time
      - _dbs_lock, _db_io_lock
    """

    def __init__(self, service):
        self._svc = service
        self._client = service._client
        self._plugin_mgr = service._plugin_mgr
        self._data_dir = service._data_dir
        self._mariadb = service._mariadb
        self._running = service._running
        self._start_time = service._start_time
        self._webhooks = service._webhooks
        self._dbs_lock = service._dbs_lock
        self._db_io_lock = service._db_io_lock

    def _get_db(self, board_key):
        return self._svc._get_db(board_key)

    def _board_from_topic(self, topic):
        return self._svc._board_from_topic(topic)

    def _publish_event(self, board_key, event, data):
        self._svc._publish_event(board_key, event, data)

    def _reply_topic(self, payload, board_key, action, corr_id):
        """Build response topic respecting reply_to override"""
        reply_to = payload.get("reply_to", "")
        if reply_to:
            return f"{reply_to}{corr_id}"
        return f"{TOPIC_BBS}/{board_key}/{action}/response/{corr_id}"

    # ── Registration ──

    def on_register(self, topic: str, payload):
        """Handle register request: {agent_id, name} -> {token, name}"""
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

        import jwt as _jwt
        _jwt_secret = os.environ.get("JWT_SECRET")
        if not _jwt_secret:
            log.error("JWT_SECRET not set, rejecting registration")
            return
        token = _jwt.encode({
            "sub": agent_id, "name": name, "role": "worker",
            "board": board_key,
            "exp": int(time.time()) + 86400 * 7,
            "iat": int(time.time()),
        }, _jwt_secret, algorithm="HS256")

        with self._db_io_lock:
            try:
                db.execute("INSERT INTO bbs_users(token,name,board,created_at) VALUES(%s,%s,%s,NOW())",
                           (token, name, board_key))
                db.commit()
            except pymysql.err.IntegrityError:
                row = db.execute("SELECT token FROM bbs_users WHERE name=%s AND board=%s",
                                 (name, board_key)).fetchone()
                token = row["token"] if row else token

        resp_topic = self._reply_topic(payload, board_key, "register", corr_id)
        self._client.publish(resp_topic, {"token": token, "name": name}, retain=False, qos=1)
        self._publish_event(board_key, "register", {"agent_id": name, "token": token, "board": board_key})
        log.info(f"  [OK] register: {name} -> token={token[:8]}... (board: {board_key})")

    # ── Post ──

    def on_post(self, topic: str, payload):
        """Handle post request: {agent_id, token, content, corr_id}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        content = payload.get("content", "")
        corr_id = payload.get("corr_id", "")
        if not token or not content:
            return

        filtered = self._plugin_mgr.apply_filters("pre_post", {
            "board_key": board_key, "token": token,
            "content": content, "corr_id": corr_id,
            "payload": payload,
        })
        if filtered is None:
            return

        db = self._get_db(board_key)
        if not db:
            return

        with self._db_io_lock:
            row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
            if not row:
                log.warning(f"  [FAIL] invalid token (board: {board_key})")
                resp_topic = self._reply_topic(payload, board_key, "post", corr_id)
                self._client.publish(resp_topic, {"error": "invalid token"}, retain=False, qos=1)
                return

            author = row["name"]
            cur = db.execute(
                "INSERT INTO bbs_posts(board,author,content,created_at) VALUES(%s,%s,%s,NOW(3))",
                (board_key, author, content)
            )
            db.commit()
            post_id = cur.lastrowid
            created_at = time.time()
            self._publish_event(board_key, "post", {"post_id": post_id, "author": author, "board": board_key})

        if corr_id:
            resp_topic = self._reply_topic(payload, board_key, "post", corr_id)
            self._client.publish(resp_topic, {
                "id": post_id, "author": author, "created_at": created_at
            }, retain=False, qos=1)

        broadcast = {"id": post_id, "author": author, "content": content, "created_at": created_at}
        self._client.publish(f"{TOPIC_BBS}/{board_key}/new_post", broadcast, retain=False, qos=0)
        log.info(f"  [NOTE] post #{post_id} by {author} (board: {board_key})")

        if board_key in self._webhooks:
            for url in self._webhooks[board_key]:
                try:
                    _th.Thread(target=webhook_send, args=(url, {
                        "board": board_key, "event": "new_post",
                        "post_id": post_id, "author": author, "content": content,
                    }), daemon=True).start()
                except Exception as _e:
                    log.warning(f"  Webhook failed: {url} -> {_e}")

    # ── Query ──

    def on_query(self, topic: str, payload):
        """Handle query request: {type, params, corr_id}"""
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
                        "SELECT id,author,content,created_at FROM bbs_posts WHERE author=%s AND board=%s ORDER BY id DESC LIMIT %s OFFSET %s",
                        (author, board_key, limit, offset)
                    ).fetchall()
                else:
                    rows = db.execute(
                        "SELECT id,author,content,created_at FROM bbs_posts WHERE board=%s ORDER BY id DESC LIMIT %s OFFSET %s",
                        (board_key, limit, offset)
                    ).fetchall()
                result = [dict(r) for r in rows]
                for _r in result:
                    for _k, _v in list(_r.items()):
                        if hasattr(_v, 'isoformat'):
                            _r[_k] = _v.isoformat()

            elif query_type == "poll":
                since_id = int(params.get("since_id", 0))
                limit = int(params.get("limit", 50))
                rows = db.execute(
                    "SELECT id,author,content,created_at FROM bbs_posts WHERE board=%s AND id>%s ORDER BY id DESC LIMIT %s",
                    (board_key, since_id, limit)
                ).fetchall()
                result = [dict(r) for r in rows]
                for _r in result:
                    for _k, _v in list(_r.items()):
                        if hasattr(_v, 'isoformat'):
                            _r[_k] = _v.isoformat()

            elif query_type == "users":
                rows = db.execute("SELECT name,token,board,created_at FROM bbs_users WHERE board=%s", (board_key,)).fetchall()
                result = [dict(r) for r in rows]
                for _r in result:
                    for _k, _v in list(_r.items()):
                        if hasattr(_v, 'isoformat'):
                            _r[_k] = _v.isoformat()

            elif query_type == "post":
                post_id = int(params.get("id", 0))
                rows = db.execute(
                    "SELECT id,author,content,created_at FROM bbs_posts WHERE id=%s AND board=%s",
                    (post_id, board_key)
                ).fetchall()
                result = [dict(r) for r in rows] if rows else []

        if result is not None:
            resp_topic = self._reply_topic(payload, board_key, "query", corr_id)
            self._client.publish(resp_topic, {"type": query_type, "data": result, "count": len(result)}, retain=False, qos=1)
            log.info(f"  query: type={query_type} -> {len(result)} rows (board: {board_key})")

    # ── Webhook Config ──

    def on_webhook_config(self, topic: str, payload):
        """Handle webhook config: {action: 'set'|'del', url, board}"""
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
                log.info(f"  [NET] webhook set: {board_key} -> {url}")
        elif action == "del":
            if board_key in self._webhooks:
                self._webhooks[board_key] = [u for u in self._webhooks[board_key] if u != url]
                log.info(f"  [NET] webhook del: {board_key} -> {url}")

    # ── Healthcheck ──

    def on_healthcheck(self, topic: str, payload):
        """Handle system/healthcheck"""
        self._client.publish(f"{topic}/response", {
            "status": "ok" if self._running else "stopped",
            "uptime": time.time() - self._start_time,
            "boards": len(self._svc._boards),
            "version": "0.3.0",
        })

    def on_hc_liveness(self, topic: str, payload):
        """Handle system/healthcheck/liveness"""
        self._client.publish(f"{topic}/response", {"status": "ok"})

    def on_hc_readiness(self, topic: str, payload):
        """Handle system/healthcheck/readiness"""
        db_ok = self._mariadb is not None
        mqtt_ok = self._client.is_connected
        self._client.publish(f"{topic}/response", {
            "status": "ready" if (db_ok and mqtt_ok) else "not_ready",
            "db": "ok" if db_ok else "down",
            "mqtt": "ok" if mqtt_ok else "down",
        })

    # ── File Operations ──

    def on_file_init(self, topic: str, payload):
        """Handle file upload init: {token, filename, total_size, chunk_count, corr_id}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        filename = payload.get("filename", "")
        total_size = payload.get("total_size", 0)
        chunk_count = payload.get("chunk_count", 1)
        corr_id = payload.get("corr_id", "")
        if not token or not filename:
            return

        db = self._get_db(board_key)
        if not db:
            return
        row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
        if not row:
            return

        rand_id = base64.urlsafe_b64encode(os.urandom(4)).decode().rstrip("=")
        session_id = f"{rand_id}"
        if chunk_count > 1:
            session_dir = os.path.join(self._data_dir, "uploads", board_key, f"chunk_{session_id}")
            os.makedirs(session_dir, exist_ok=True)
            meta = {"filename": filename, "total_size": total_size,
                    "chunk_count": chunk_count, "received": 0, "chunks": []}
            with open(os.path.join(session_dir, "_meta.json"), "w") as mf:
                json.dump(meta, mf)
            if corr_id:
                resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
                self._client.publish(resp_topic, {"session_id": session_id}, retain=False, qos=1)
            log.info(f"  file init: {filename} ({chunk_count} chunks)")
        else:
            if corr_id:
                resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
                self._client.publish(resp_topic, {"session_id": session_id}, retain=False, qos=1)
            log.info(f"  file init (single): {filename}")

    def on_file_chunk(self, topic: str, payload):
        """Handle file chunk upload: {token, session_id, seq, data, corr_id}"""
        board_key = self._board_from_topic(topic)
        if not board_key or not isinstance(payload, dict):
            return
        token = payload.get("token", "")
        session_id = payload.get("session_id", "")
        seq = payload.get("seq", 0)
        data_b64 = payload.get("data", "")
        corr_id = payload.get("corr_id", "")
        if not token or not session_id or not data_b64:
            return

        db = self._get_db(board_key)
        if not db:
            return
        row = db.execute("SELECT name FROM bbs_users WHERE token=%s", (token,)).fetchone()
        if not row:
            return

        if session_id and len(session_id) <= 6 and "_" not in session_id:
            safe_name = session_id
            filepath = os.path.join(self._data_dir, "uploads", board_key, safe_name)
            os.makedirs(os.path.dirname(filepath), exist_ok=True)
            try:
                file_bytes = base64.b64decode(data_b64)
                with open(filepath, "wb") as f:
                    f.write(file_bytes)
                ref = f"{rand_id}/{safe_name}"
                if corr_id:
                    resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
                    self._client.publish(resp_topic, {"ref": ref}, retain=False, qos=1)
                log.info(f"  file upload (single): {ref} (board: {board_key})")
            except Exception as e:
                log.warning(f"  file upload failed: {e}")
            return

        session_dir = os.path.join(self._data_dir, "uploads", board_key, f"chunk_{session_id}")
        meta_path = os.path.join(session_dir, "_meta.json")
        if not os.path.exists(meta_path):
            return

        try:
            chunk_data = base64.b64decode(data_b64)
            chunk_path = os.path.join(session_dir, f"{seq:04d}.chunk")
            with open(chunk_path, "wb") as cf:
                cf.write(chunk_data)
            with open(meta_path) as mf:
                meta = json.load(mf)
            meta["received"] += 1
            meta["chunks"].append(seq)
            with open(meta_path, "w") as mf:
                json.dump(meta, mf)
            if corr_id:
                resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
                self._client.publish(resp_topic, {"seq": seq}, retain=False, qos=1)
        except Exception as e:
            log.warning(f"  chunk failed: {e}")

    def on_file_commit(self, topic: str, payload):
        """Handle file chunk merge: {token, session_id, corr_id}"""
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

        session_dir = os.path.join(self._data_dir, "uploads", board_key, f"chunk_{session_id}")
        meta_path = os.path.join(session_dir, "_meta.json")
        if not os.path.exists(meta_path):
            return

        with open(meta_path) as f:
            meta = json.load(f)
        chunk_count = meta.get("chunk_count", 0)
        received = meta.get("received", 0)

        if received < chunk_count:
            log.warning(f"  chunks incomplete: {received}/{chunk_count}")
            if corr_id:
                resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
                self._client.publish(resp_topic, {"error": f"incomplete: {received}/{chunk_count}"}, retain=False, qos=1)
            return

        import shutil
        target_dir = os.path.join(self._data_dir, "uploads", board_key, session_id[:6])
        os.makedirs(target_dir, exist_ok=True)
        target_path = os.path.join(target_dir, meta["filename"])
        with open(target_path, "wb") as out:
            for seq in range(chunk_count):
                chunk_path = os.path.join(session_dir, f"{seq:04d}.chunk")
                if os.path.exists(chunk_path):
                    with open(chunk_path, "rb") as cf:
                        out.write(cf.read())

        shutil.rmtree(session_dir, ignore_errors=True)
        file_ref = f"{session_id[:6]}/{meta['filename']}"
        if corr_id:
            resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
            self._client.publish(resp_topic, {"ref": file_ref}, retain=False, qos=1)
        log.info(f"  file merge: {file_ref} ({received} chunks)")

    def on_file_download(self, topic: str, payload):
        """Handle file download: {token, file_ref, corr_id}"""
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

        filepath = os.path.join(self._data_dir, "uploads", board_key, file_ref)
        if os.path.exists(filepath) and os.path.isfile(filepath):
            with open(filepath, "rb") as dlf:
                file_bytes = dlf.read()
            data_b64 = base64.b64encode(file_bytes).decode()
            if corr_id:
                resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
                self._client.publish(resp_topic, {"ref": file_ref, "data": data_b64, "size": len(file_bytes)}, retain=False, qos=1)
            log.info(f"  file download: {file_ref} ({len(file_bytes)}B)")
        else:
            if corr_id:
                resp_topic = self._reply_topic(payload, board_key, "file", corr_id)
                self._client.publish(resp_topic, {"error": "not_found"}, retain=False, qos=1)

    # ── Admin ──

    def on_admin_reload(self, topic: str, payload):
        """Handle hot reload of boards.json"""
        self._svc._load_boards()
        subscribed = getattr(self._svc, '_subscribed_boards', set())
        for board_key in list(subscribed):
            if board_key not in self._svc._boards:
                subscribed.discard(board_key)
        for board_key in self._svc._boards:
            if board_key not in subscribed:
                self._svc._subscribe_board(board_key)
                subscribed.add(board_key)
        self._svc._subscribed_boards = subscribed
        log.info("  [SYNC] boards hot reloaded")
