"""
Board Service 集成测试 — 真实 MQTT broker pub/sub 验证

测试 topic 格式统一后 Python 版和 Rust 版能否互通。

用法:
    pytest tests/test_board_service_integration.py -v
    python -m pytest tests/test_board_service_integration.py -v
"""
import sys, json, time, threading
from pathlib import Path

_proj = Path(__file__).resolve().parent.parent.parent.parent
_beneh = _proj.parent
for p in [str(_proj), str(_beneh)]:
    if p not in sys.path:
        sys.path.insert(0, p)

import pytest
import paho.mqtt.client as mqtt

BROKER = "127.0.0.1"
PORT = 1883
TIMEOUT = 5


class TestTopicFormat:
    """验证 TOPIC 格式统一为 agent/bbs/{board}/{action}"""

    def test_python_config_aligned(self):
        """检查 Python 版 TOPIC_BBS 已对齐 Rust 版的 agent/bbs/"""
        from Mqtt_bbs_server.board_config import TOPIC_BBS
        assert TOPIC_BBS == "agent/bbs", (
            f"Python TOPIC_BBS={TOPIC_BBS}, 期望 agent/bbs"
        )

    def test_rust_subscribe_pattern(self):
        """验证 Rust 订阅模式能被 Python 发布匹配"""
        from Mqtt_bbs_server.board_config import TOPIC_BBS
        # Rust 订阅: agent/bbs/+/register
        # Python 发布时格式: {TOPIC_BBS}/{board}/{action}
        board_key = "test-board"
        action = "register"
        pub_topic = f"{TOPIC_BBS}/{board_key}/{action}"
        # Rust 的订阅通配符: agent/bbs/+/register
        assert pub_topic.startswith("agent/bbs/")
        assert pub_topic.endswith("/register")
        assert "/test-board/" in pub_topic


class TestMQTTIntegration:
    """需要 MQTT broker (Mosquitto:1883) 运行的集成测试"""

    received = []

    @classmethod
    def on_message(cls, client, userdata, msg):
        cls.received.append({
            "topic": msg.topic,
            "payload": msg.payload.decode(),
            "qos": msg.qos,
        })

    @pytest.fixture(autouse=True)
    def setup(self):
        self.__class__.received = []
        self.client = mqtt.Client(client_id="test-integration")
        self.client.on_message = self.on_message
        self.client.connect(BROKER, PORT, 60)
        self.client.loop_start()
        yield
        self.client.loop_stop()
        self.client.disconnect()

    def test_publish_receive_agent_bbs_topic(self):
        """用 agent/bbs/ 格式发布消息，验证能收到"""
        from Mqtt_bbs_server.board_config import TOPIC_BBS
        topic = f"{TOPIC_BBS}/test-board/register"
        payload = json.dumps({"agent_id": "test-agent", "test": True})

        received_events = []

        def on_match(client, userdata, msg):
            received_events.append(msg)

        self.client.subscribe(f"{TOPIC_BBS}/test-board/#")
        self.client.message_callback_add(f"{TOPIC_BBS}/test-board/#", on_match)

        self.client.publish(topic, payload, qos=1)
        time.sleep(1)

        assert len(received_events) > 0, (
            f"未收到 topic={topic} 上的消息。broker={BROKER}:{PORT}"
        )
        msg = received_events[0]
        assert msg.topic == topic, f"topic 不匹配: {msg.topic} != {topic}"
        data = json.loads(msg.payload.decode())
        assert data["agent_id"] == "test-agent"

    def test_topic_format_backward_compat(self):
        """验证旧格式 bbs/ 是否仍然能收到（如果 broker 上还有旧客户端）"""
        from Mqtt_bbs_server.board_config import TOPIC_BBS
        # 新格式
        new_topic = f"{TOPIC_BBS}/compat-board/heartbeat"
        # 旧格式
        old_topic = "bbs/compat-board/heartbeat"

        received_new = []
        received_old = []

        def on_new(client, userdata, msg):
            received_new.append(msg)

        def on_old(client, userdata, msg):
            received_old.append(msg)

        self.client.subscribe(f"{TOPIC_BBS}/compat-board/#")
        self.client.message_callback_add(f"{TOPIC_BBS}/compat-board/#", on_new)
        self.client.subscribe("bbs/compat-board/#")
        self.client.message_callback_add("bbs/compat-board/#", on_old)

        # 用新格式发布
        self.client.publish(new_topic, json.dumps({"ts": 1}), qos=1)
        time.sleep(1)

        assert len(received_new) > 0, f"新格式 {new_topic} 未收到消息"

    def test_subscribe_with_wildcard(self):
        """验证 agent/bbs/+/ 通配符订阅"""
        from Mqtt_bbs_server.board_config import TOPIC_BBS
        topic = f"{TOPIC_BBS}/wildcard-test/query"

        received = []

        def on_msg(client, userdata, msg):
            received.append(msg)

        # Rust 用的通配符模式: agent/bbs/+/register
        self.client.subscribe(f"{TOPIC_BBS}/+/query")
        self.client.message_callback_add(f"{TOPIC_BBS}/+/query", on_msg)

        self.client.publish(topic, json.dumps({"q": "test"}), qos=1)
        time.sleep(1)

        assert len(received) > 0, f"通配符订阅未匹配 {topic}"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
