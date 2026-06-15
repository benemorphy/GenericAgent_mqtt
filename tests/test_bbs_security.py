"""单元测试: MQTT BBS 安全增强模块 (rate_limiter, audit_log, plugin, config)"""

import os
import sys
import time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from Mqtt_bbs_client.rate_limiter import RateLimiter, TokenBucket
from Mqtt_bbs_client.audit_log import AuditLogger, AuditEvent
from Mqtt_bbs_client.plugin import Plugin, PluginManager, PluginContext, plugin_hook
from Mqtt_bbs_client import config


# ═══════════════════════════════════════
# TokenBucket
# ═══════════════════════════════════════

class TestTokenBucket:
    def test_initial_tokens(self):
        tb = TokenBucket(rate=10, burst=20)
        assert tb.available == 20.0, "初始应为满桶"

    def test_consume_success(self):
        tb = TokenBucket(rate=1000, burst=100)
        assert tb.consume(1) is True
        assert tb.consume(50) is True
        assert tb.available < 100

    def test_consume_exhaust(self):
        tb = TokenBucket(rate=1000, burst=5)
        for _ in range(5):
            assert tb.consume(1) is True
        assert tb.consume(1) is False, "超过 burst 应拒绝"


class TestRateLimiter:
    def test_disabled(self):
        rl = RateLimiter(max_per_sec=1, burst=1, enabled=False)
        for _ in range(10):
            assert rl.allow("test/topic") is True, "禁用时全部放行"

    def test_global_limit(self):
        rl = RateLimiter(max_per_sec=1000, burst=3, enabled=True)
        assert rl.allow("t1") is True
        assert rl.allow("t2") is True
        assert rl.allow("t3") is True
        # burst 用完后应拒绝
        assert rl.allow("t4") is False

    def test_stats(self):
        rl = RateLimiter(max_per_sec=1000, burst=2, enabled=True)
        rl.allow("a")
        rl.allow("a")
        rl.allow("a")  # 应被拒绝
        stats = rl.stats
        assert stats["allowed"] == 2
        assert stats["denied"] == 1
        assert stats["total"] == 3
        assert stats["block_rate"] > 0

    def test_per_topic_limit(self):
        """验证 per-topic 限流独立运作"""
        rl = RateLimiter(max_per_sec=1000, burst=100, enabled=True,
                         per_topic_max_per_sec=1, per_topic_burst=2)
        assert rl.allow("board/post") is True
        assert rl.allow("board/post") is True
        assert rl.allow("board/post") is False  # per-topic 限流
        # 不同 topic 不受影响
        assert rl.allow("heartbeat/pulse") is True


# ═══════════════════════════════════════
# AuditLogger
# ═══════════════════════════════════════

class TestAuditLogger:
    def test_disabled(self):
        logger = AuditLogger(enabled=False)
        assert logger.log(AuditEvent(type="TEST", detail="ignored")) is False

    def test_console_log(self):
        logger = AuditLogger(enabled=True, log_to_console=True)
        evt = AuditEvent(type="AUTH", detail="test login", result="SUCCESS")
        assert logger.log(evt) is True

    def test_shortcuts(self):
        logger = AuditLogger(enabled=True, log_to_console=False)
        assert logger.auth_success("agent_a", "mqtt_login") is True
        assert logger.auth_failure("agent_b", "jwt", "token expired") is True
        assert logger.connect("agent_c") is True
        assert logger.disconnect("agent_c") is True
        assert logger.security_warning("suspicious activity") is True
        assert logger.command("admin", "restart") is True
        assert logger.system_error("OOM") is True


# ═══════════════════════════════════════
# Config
# ═══════════════════════════════════════

class TestConfigSecurity:
    def test_tls_config_exists(self):
        assert hasattr(config, 'MQTT_TLS_ENABLED')
        assert hasattr(config, 'MQTT_TLS_CA_CERTS')
        assert hasattr(config, 'MQTT_TLS_INSECURE')

    def test_rate_limit_config_exists(self):
        assert hasattr(config, 'RATE_LIMIT_ENABLED')
        assert isinstance(config.RATE_LIMIT_ENABLED, bool)

    def test_audit_config_exists(self):
        assert hasattr(config, 'AUDIT_LOG_ENABLED')
        assert hasattr(config, 'AUDIT_LOG_TOPIC')

    def test_no_hardcoded_secrets(self):
        """验证 config 无硬编码密钥"""
        src = open(os.path.join(os.path.dirname(config.__file__), 'config.py')).read()
        assert '"Mqtt_bbs_hmac_secret_2026"' not in src, "HMAC secret 不应硬编码"
        assert '"bbs-jwt-secret-key"' not in src, "JWT secret 不应硬编码"


# ═══════════════════════════════════════
# Plugin System
# ═══════════════════════════════════════

class TestPluginManager:
    def test_plugin_manager_init(self):
        pm = PluginManager()
        assert pm is not None
        assert len(pm.list_plugins()) == 0

    def test_plugin_hook_decorator(self):
        @plugin_hook
        class TestPlugin(Plugin):
            name = "test_plugin"
            version = "1.0"
            description = "Test plugin"

        assert issubclass(TestPlugin, Plugin)
        assert TestPlugin.name == "test_plugin"
        assert TestPlugin.version == "1.0"

    def test_plugin_manager_custom_dir(self, tmpdir):
        """验证 PluginManager 接受自定义扫描目录"""
        pm = PluginManager(plugin_dirs=[str(tmpdir)])
        assert pm is not None


# ═══════════════════════════════════════
# 集成测试: RateLimiter + AuditLogger
# ═══════════════════════════════════════

class TestSecurityIntegration:
    def test_rate_limiter_reset(self):
        rl = RateLimiter(max_per_sec=1000, burst=1, enabled=True)
        rl.allow("test")
        rl.allow("test")  # 被拒绝
        assert rl.stats["denied"] == 1
        rl.reset_stats()
        assert rl.stats["denied"] == 0

    def test_audit_event_serialization(self):
        evt = AuditEvent(
            type="SECURITY",
            detail="test",
            severity="CRITICAL",
            result="BLOCKED",
            agent_id="tester",
            metadata={"key": "value"},
        )
        d = evt.to_dict()
        assert d["type"] == "SECURITY"
        assert d["severity"] == "CRITICAL"
        assert d["metadata"]["key"] == "value"
        assert "timestamp" in d
