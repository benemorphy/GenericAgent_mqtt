"""
实时协作白板 — BBS 驱动的 KV 共享状态 + CAS 乐观锁

用法:
    from mqtt_bbs.whiteboard import WhiteboardKV, StateKV

    # 传统方式（向后兼容）
    wb = WhiteboardKV("agent-alpha", board="agent-whiteboard")
    wb.connect()
    wb.set("model_config", {"lr": 0.001, "epochs": 10})

    # P1.5: v2/state 状态空间独立化（推荐）
    st = StateKV("agent-alpha", namespace="training")
    st.connect()
    st.set("model_config", {"lr": 0.001, "epochs": 10})
    val = st.get("model_config")
"""

import json, time, os, logging
from typing import Callable, Optional, Any

from .board_client import BoardClient
from . import config as cfg
from .client import BBSClient

log = logging.getLogger("mqtt_bbs.whiteboard")

WHITEBOARD_AUTHOR = "whiteboard"  # BBS 帖子 author 标识

STATE_TOPIC = "v2/state"  # P1.5: v2/state/{namespace}/{key}


class StateKV:
    """P1.5: 基于 MariaDB 的 KV 状态存储

    用法:
        st = StateKV("agent-alpha", namespace="training")
        st.connect()
        st.set("model_config", {"lr": 0.001})
        val = st.get("model_config")
        st.cas("counter", 0, 1)    # CAS 乐观锁
    """

    def __init__(self, agent_id: str, namespace: str = "default",
                 host: str = None, port: int = None):
        self.agent_id = agent_id
        self.namespace = namespace
        self._client = BBSClient(agent_id, host=host, port=port)
        self._connected = False
        self._watchers: dict[str, list[Callable]] = {}
        self._subscribed = False
        self._db = None
        self._db_config = cfg.DB_CONFIG.copy()

    def connect(self):
        self._client.connect()
        self._client.wait_connected(5)
        self._connected = self._client.is_connected
        if not self._subscribed:
            self._msg_handler = self._client.subscribe(
                self._ns_topic() + "#", self._on_message)
            self._subscribed = True
        # 初始化 DB 连接
        import pymysql
        self._db = pymysql.connect(**self._db_config)

    def disconnect(self):
        if self._db:
            self._db.close()
            self._db = None
        self._client.disconnect()
        self._connected = False

    def _ns_topic(self):
        return f"v2/state/{self.namespace}/"

    def _topic(self, key: str):
        return f"v2/state/{self.namespace}/{key}"

    def get(self, key: str, default: Any = None) -> Optional[dict]:
        if not self._db:
            return None
        cur = self._db.cursor()
        cur.execute(
            "SELECT value, version, updated_by, updated_at FROM state_kv WHERE namespace=%s AND `key`=%s",
            (self.namespace, key))
        row = cur.fetchone()
        if not row:
            return None
        return {
            "key": key,
            "value": json.loads(row[0]) if isinstance(row[0], str) else row[0],
            "version": row[1],
            "updated_by": row[2],
            "updated_at": str(row[3]) if row[3] else "",
        }

    def set(self, key: str, value: Any):
        if not self._db:
            return
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        cur = self._db.cursor()
        cur.execute(
            "INSERT INTO state_kv (namespace, `key`, value, version, updated_by, updated_at) "
            "VALUES (%s, %s, %s, 1, %s, %s) "
            "ON DUPLICATE KEY UPDATE value=%s, version=version+1, updated_by=%s, updated_at=%s",
            (self.namespace, key, json.dumps(value, ensure_ascii=False), self.agent_id, now,
             json.dumps(value, ensure_ascii=False), self.agent_id, now))
        self._db.commit()
        self._client.publish(self._topic(key), {"value": value, "version_inc": True}, retain=False, qos=1)

    def cas(self, key: str, expected_version: int, new_value: Any) -> bool:
        if not self._db:
            return False
        cur = self._db.cursor()
        cur.execute(
            "SELECT version FROM state_kv WHERE namespace=%s AND `key`=%s",
            (self.namespace, key))
        row = cur.fetchone()
        cur_version = row[0] if row else 0
        if cur_version != expected_version:
            return False
        now = time.strftime("%Y-%m-%d %H:%M:%S")
        cur.execute(
            "INSERT INTO state_kv (namespace, `key`, value, version, updated_by, updated_at) "
            "VALUES (%s, %s, %s, %s, %s, %s) "
            "ON DUPLICATE KEY UPDATE value=%s, version=%s, updated_by=%s, updated_at=%s",
            (self.namespace, key, json.dumps(new_value, ensure_ascii=False),
             expected_version + 1, self.agent_id, now,
             json.dumps(new_value, ensure_ascii=False),
             expected_version + 1, self.agent_id, now))
        self._db.commit()
        self._client.publish(self._topic(key), {"value": new_value, "version": expected_version + 1},
                             retain=False, qos=1)
        return True

    def increment(self, key: str, delta: int = 1, default: int = 0) -> Optional[int]:
        for attempt in range(3):
            current = self.get(key)
            cur_val = current["value"] if current else default
            new_val = cur_val + delta
            if self.cas(key, current["version"] if current else 0, new_val):
                return new_val
            import time as _t
            _t.sleep(0.05)
        return None

    def delete(self, key: str):
        if not self._db:
            return
        cur = self._db.cursor()
        cur.execute("DELETE FROM state_kv WHERE namespace=%s AND `key`=%s",
                     (self.namespace, key))
        self._db.commit()
        self._client.publish(self._topic(key), {"deleted": True}, retain=False, qos=1)

    def watch(self, key: str, callback: Callable):
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)

    def _on_message(self, topic, payload):
        key = topic.replace(self._ns_topic(), "").split("/")[0]
        value = payload.get("value") if isinstance(payload, dict) else None
        if key and key in self._watchers:
            for cb in self._watchers[key]:
                try:
                    cb(key, value)
                except Exception as e:
                    log.error(f"[StateKV] watcher 异常 [{key}]: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected




class WhiteboardKV:
    """基于 BBS board 的 KV 共享状态存储，支持 CAS 乐观锁"""

    def __init__(self, agent_id: str, board: str = "agent-whiteboard",
                 host: str = None, port: int = None):
        self.agent_id = agent_id
        self.board = board
        self._bbs = BoardClient(f"{agent_id}_wb", board=board, host=host, port=port)
        self._token = None
        self._connected = False
        self._watchers: dict[str, list[Callable]] = {}
        self._subscribed = False

    def connect(self):
        """连接并注册到 BBS"""
        self._bbs.connect()
        # BoardClient.connect() 内部已调用 wait_connected
        info = self._bbs.register(WHITEBOARD_AUTHOR, timeout=5)
        self._token = info.get("token", "")
        self._connected = bool(self._token)
        if self._connected:
            log.info(f"[Whiteboard] ✅ 已连接 (board={self.board})")
        else:
            log.warning(f"[Whiteboard] ❌ 注册失败")
        return self._connected

    def disconnect(self):
        """断开连接"""
        if self._subscribed:
            self._bbs.unsubscribe(f"{self.board}/post")
        self._bbs.disconnect()
        self._connected = False

    # ── 读 ──

    def get(self, key: str, default: Any = None) -> Optional[dict]:
        """读取指定 key 的值

        Returns:
            {"key": str, "value": Any, "version": int, "updated_by": str, "updated_at": float}
            或 default（key 不存在时）
        """
        if not self._connected:
            raise RuntimeError("WhiteboardKV 未连接，请先调用 connect()")
        # 查询所有帖子，找匹配 key
        posts = self._bbs.query_posts(author=WHITEBOARD_AUTHOR, limit=200, timeout=10)
        if not posts:
            return default
        for p in reversed(posts):
            content = p.get("content", "{}")
            if isinstance(content, str):
                try:
                    entry = json.loads(content)
                except json.JSONDecodeError:
                    continue
            elif isinstance(content, dict):
                entry = content
            else:
                continue
            if entry.get("key") == key:
                return entry
        return default

    def list_keys(self) -> list[str]:
        """列出所有 key（返回最新版本的去重列表）"""
        posts = self._bbs.query_posts(author=WHITEBOARD_AUTHOR, limit=200, timeout=10)
        seen = {}
        for p in reversed(posts):
            content = p.get("content", "{}")
            if isinstance(content, str):
                try:
                    entry = json.loads(content)
                except json.JSONDecodeError:
                    continue
            elif isinstance(content, dict):
                entry = content
            else:
                continue
            key = entry.get("key")
            if key and key not in seen:
                seen[key] = entry.get("version", 0)
        return list(seen.keys())

    # ── 写（无条件） ──

    def set(self, key: str, value: Any) -> bool:
        """无条件写入 key-value（可能覆盖他人写入）

        Returns:
            True 表示写入成功
        """
        if not self._connected:
            raise RuntimeError("WhiteboardKV 未连接")
        # 读取旧值获取版本号
        old = self.get(key)
        new_version = (old["version"] + 1) if old else 1
        entry = {
            "key": key,
            "value": value,
            "version": new_version,
            "updated_by": self.agent_id,
            "updated_at": time.time(),
        }
        self._bbs.post(json.dumps(entry, ensure_ascii=False), self._token, timeout=5)
        log.info(f"[Whiteboard] ✏️  {key} = {str(value)[:60]} (v{new_version})")
        return True

    # ── CAS 乐观锁写 ──

    def cas(self, key: str, expected_version: int, new_value: Any) -> bool:
        """CAS（Compare-And-Swap）乐观锁写入

        仅当 key 的当前版本 == expected_version 时写入。

        Returns:
            True = 写入成功, False = 版本冲突
        """
        if not self._connected:
            raise RuntimeError("WhiteboardKV 未连接")
        current = self.get(key)
        cur_version = current["version"] if current else 0
        if cur_version != expected_version:
            log.warning(f"[Whiteboard] ⚠️ CAS 冲突: {key} 期望 v{expected_version}，实际 v{cur_version}")
            return False
        entry = {
            "key": key,
            "value": new_value,
            "version": expected_version + 1,
            "updated_by": self.agent_id,
            "updated_at": time.time(),
        }
        self._bbs.post(json.dumps(entry, ensure_ascii=False), self._token, timeout=5)
        log.info(f"[Whiteboard] 🔒 CAS: {key} = {str(new_value)[:60]} (v{expected_version}→{expected_version+1})")
        return True

    # ── 原子增减 ──

    def increment(self, key: str, delta: int = 1, default: int = 0) -> Optional[int]:
        """原子增减（读→CAS→重试循环）

        Returns:
            新值，失败返回 None
        """
        for attempt in range(3):
            current = self.get(key)
            cur_val = current["value"] if current else default
            cur_ver = current["version"] if current else 0
            if self.cas(key, cur_ver, cur_val + delta):
                return cur_val + delta
            time.sleep(0.1)  # 退避重试
        log.warning(f"[Whiteboard] ⚠️ increment {key} 重试3次后失败")
        return None

    # ── P0速赢: 基于 CAS 的分布式锁 ──

    def acquire_lock(self, lock_name: str, holder_id: str,
                     ttl: int = 30, retry_count: int = 10,
                     retry_delay: float = 0.5) -> bool:
        """
        获取分布式锁（基于 WhiteboardKV CAS）。
        
        参数:
            lock_name: 锁名称（如 "dag:scheduler"）
            holder_id: 持有者标识（如 agent_id）
            ttl: 锁自动释放时间（秒）
            retry_count: 获取重试次数
            retry_delay: 重试间隔（秒）
        
        返回:
            True=获取成功, False=获取失败
        """
        lock_key = f"_lock:{lock_name}"
        now = time.time()
        for attempt in range(retry_count):
            current = self.get(lock_key)
            if current:
                value = current.get("value", {})
                ver = current.get("version", 0)
                holder = value.get("holder", "")
                # 检查锁是否过期：只有 holder 非空且未过期才算被占用
                if holder and holder != holder_id:
                    expires_at = value.get("expires_at", 0)
                    if time.time() < expires_at:
                        time.sleep(retry_delay)
                        continue
                    # 过期了，视为可抢占
            # 尝试 CAS 获取锁
            lock_data = {
                "holder": holder_id,
                "acquired_at": now,
                "expires_at": now + ttl,
            }
            cur_ver = current.get("version", 0) if current else 0
            if self.cas(lock_key, cur_ver, lock_data):
                log.info(f"[Whiteboard] 🔒 获取锁: {lock_name} → {holder_id}")
                return True
            time.sleep(retry_delay)
        log.warning(f"[Whiteboard] ⚠️ 获取锁失败(重试{retry_count}次): {lock_name}")
        return False

    def release_lock(self, lock_name: str, holder_id: str) -> bool:
        """
        释放分布式锁。
        
        参数:
            lock_name: 锁名称
            holder_id: 持有者标识（仅持有者可释放）
        
        返回:
            True=释放成功, False=释放失败
        """
        lock_key = f"_lock:{lock_name}"
        current = self.get(lock_key)
        if not current:
            return True  # 锁已不存在
        value = current.get("value", {})
        if value.get("holder") != holder_id:
            log.warning(f"[Whiteboard] ⚠️ 非锁持有者无法释放: {lock_name}")
            return False
        # 用 set() 直接写入空 holder（不通过 CAS，避免版本号冲突）
        self.set(lock_key, {"holder": "", "released_at": time.time()})
        log.info(f"[Whiteboard] 🔓 释放锁: {lock_name} → {holder_id}")
        return True

    # ── 订阅变更 ──

    def watch(self, key: str, callback: Callable[[str, Any], None]):
        """订阅指定 key 的变更"""
        if not self._subscribed:
            self._bbs.subscribe(f"{self.board}/post", self._on_whiteboard_post)
            self._subscribed = True
        if key not in self._watchers:
            self._watchers[key] = []
        self._watchers[key].append(callback)
        log.info(f"[Whiteboard] 👁️ 已订阅: {key}")

    def unwatch(self, key: str, callback: Callable = None):
        """取消订阅"""
        if callback and key in self._watchers:
            self._watchers[key].remove(callback)
        elif key in self._watchers:
            del self._watchers[key]

    def _on_whiteboard_post(self, topic, payload):
        """处理 BBS 新帖 → 匹配 watcher"""
        if not isinstance(payload, dict):
            return
        content = payload.get("content", "{}")
        if isinstance(content, str):
            try:
                entry = json.loads(content)
            except json.JSONDecodeError:
                return
        elif isinstance(content, dict):
            entry = content
        else:
            return
        key = entry.get("key")
        value = entry.get("value")
        if key and key in self._watchers:
            for cb in self._watchers[key]:
                try:
                    cb(key, value)
                except Exception as e:
                    log.error(f"[Whiteboard] watcher 异常 [{key}]: {e}")

    @property
    def is_connected(self) -> bool:
        return self._connected
