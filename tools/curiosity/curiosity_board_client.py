"""
CuriosityBoard Client — 好奇心讨论板客户端

供 GA Handler 使用，通过 MQTT 与 CuriosityBoardPlugin 通信。

用法:
    from tools.curiosity.curiosity_board_client import CuriosityBoardClient
    client = CuriosityBoardClient("agent_alpha")
    client.connect()
    post_id = client.post_curiosity(signal)
    responses = client.get_responses(post_id)
    client.disconnect()
"""

import uuid
import threading
from typing import Optional
from Mqtt_bbs_client.client import BBSClient
from Mqtt_bbs_server import config as cfg

POST_BASE = "board/curiosity"

class CuriosityBoardClient:
    """轻量 MQTT 客户端，发布好奇心信号到 BBS"""

    def __init__(self, agent_id: str, host: str = None, port: int = None, timeout: float = 5.0):
        self.agent_id = agent_id
        self._client = BBSClient(agent_id, host=host or cfg.BROKER_HOST, port=port or cfg.BROKER_PORT)
        self._timeout = timeout
        self._pending: dict[str, dict] = {}
        self._pending_lock = threading.Lock()
        self._connected = False

    def connect(self):
        """连接并订阅所有可能的响应主题"""
        self._client.connect()
        self._client.wait_connected(3)
        # 订阅响应主题
        self._client.subscribe("curiosity/post/response/+", self._on_response)
        self._client.subscribe("curiosity/discuss/response/+", self._on_response)
        self._client.subscribe("curiosity/status/response/+", self._on_response)
        self._client.subscribe("curiosity/query/response/+", self._on_response)
        self._client.subscribe("curiosity/hot/response/+", self._on_response)
        self._connected = True
        return self

    def disconnect(self):
        self._client.disconnect()
        self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client.is_connected

    def _on_response(self, topic: str, payload):
        """匹配 corr_id 并唤醒等待者"""
        parts = topic.split("/")
        if len(parts) < 3:
            return
        corr_id = parts[-1]
        with self._pending_lock:
            if corr_id in self._pending:
                self._pending[corr_id]["result"] = payload
                self._pending[corr_id]["event"].set()

    def _wait_response(self, corr_id: str) -> Optional[dict]:
        """等待异步响应"""
        event = threading.Event()
        with self._pending_lock:
            self._pending[corr_id] = {"event": event, "result": None}
        event.wait(self._timeout)
        with self._pending_lock:
            entry = self._pending.pop(corr_id, None)
            return entry.get("result") if entry else None

    def _publish_and_wait(self, topic: str, payload: dict) -> Optional[dict]:
        """发布请求并等待响应"""
        corr_id = str(uuid.uuid4())[:8]
        payload["agent_id"] = self.agent_id
        payload["corr_id"] = corr_id
        self._client.publish(topic, payload)
        return self._wait_response(corr_id)

    # ── 公开 API ──

    def post_curiosity(self, signal) -> Optional[str]:
        """发布一条好奇心信号到讨论板

        Args:
            signal: CuriositySignal 实例

        Returns:
            帖子ID，失败返回 None
        """
        if not self.is_connected:
            return None
        payload = {
            "type": signal.type,
            "source": signal.source,
            "target": signal.target,
            "reason": signal.reason,
            "severity": signal.severity,
            "context": signal.context,
        }
        result = self._publish_and_wait(f"{POST_BASE}/post", payload)
        if result and result.get("ok"):
            return result.get("id")
        return None

    def discuss(self, post_id: str, content: str) -> bool:
        """回复一个好奇心帖子"""
        if not self.is_connected:
            return False
        result = self._publish_and_wait(f"{POST_BASE}/discuss/{post_id}", {"content": content})
        return result is not None and result.get("ok", False)

    def get_post(self, post_id: str) -> Optional[dict]:
        """获取帖子详情（含回复列表）"""
        if not self.is_connected:
            return None
        result = self._publish_and_wait(f"{POST_BASE}/post/{post_id}", {})
        if result and result.get("ok"):
            return result.get("post")
        return None

    def update_status(self, post_id: str, status: str) -> bool:
        """更新帖子状态 (open/discussing/resolved/archived)"""
        if not self.is_connected:
            return False
        result = self._publish_and_wait(f"{POST_BASE}/status/{post_id}", {"status": status})
        return result is not None and result.get("ok", False)

    def query(self, status: str = None, type_: str = None, limit: int = 20) -> list:
        """查询帖子列表"""
        if not self.is_connected:
            return []
        payload = {}
        if status: payload["status"] = status
        if type_: payload["type"] = type_
        if limit: payload["limit"] = limit
        result = self._publish_and_wait(f"{POST_BASE}/query", payload)
        if result and result.get("ok"):
            return result.get("posts", [])
        return []

    def get_hot(self) -> list:
        """获取热门好奇心帖子"""
        if not self.is_connected:
            return []
        result = self._publish_and_wait(f"{POST_BASE}/hot", {})
        if result and result.get("ok"):
            return result.get("posts", [])
        return []
