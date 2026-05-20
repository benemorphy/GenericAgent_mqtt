"""
实时协作白板 — BBS 驱动的 KV 共享状态 + CAS 乐观锁

用法:
    from mqtt_bbs.whiteboard import WhiteboardKV

    wb = WhiteboardKV("agent-alpha", board="agent-whiteboard")
    wb.connect()

    # 写
    wb.set("model_config", {"lr": 0.001, "epochs": 10})

    # 读
    val = wb.get("model_config")

    # CAS 乐观锁写
    old = wb.get("counter")
    wb.cas("counter", old["version"], old["value"] + 1)

    # 订阅变更
    def on_change(key, value):
        print(f"{key} 变更为: {value}")
    wb.watch("model_config", on_change)
"""

import json, time, logging
from typing import Callable, Optional, Any

from .board_client import BoardClient

log = logging.getLogger("mqtt_bbs.whiteboard")

WHITEBOARD_AUTHOR = "whiteboard"  # BBS 帖子 author 标识


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
