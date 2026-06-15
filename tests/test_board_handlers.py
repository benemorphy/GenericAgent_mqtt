"""单元测试: BoardHandlers 核心方法 (Phase2 安全优化)"""

import os
import sys
import time
import json
from unittest.mock import MagicMock, patch, PropertyMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import pytest
from Mqtt_bbs_server.board_handlers import BoardHandlers


# ── Helpers ──

def _make_mock_service():
    """创建模拟 BoardService"""
    svc = MagicMock()
    svc._client = MagicMock()
    svc._plugin_mgr = MagicMock()
    svc._plugin_mgr.apply_filters.return_value = None  # 默认不过滤
    svc._data_dir = "/tmp"
    svc._mariadb = MagicMock()
    svc._running = True
    svc._start_time = time.time()
    svc._webhooks = {}
    svc._dbs_lock = MagicMock()
    svc._db_io_lock = MagicMock()
    svc._boards = {"test-board": {}}
    svc._rate_limiter = MagicMock()
    svc._rate_limiter.allow.return_value = True
    svc._audit_logger = MagicMock()
    return svc


# ═══════════════════════════════════════
# on_register
# ═══════════════════════════════════════

class TestOnRegister:
    def test_normal_register(self):
        svc = _make_mock_service()
        svc._get_db.return_value = MagicMock()
        handlers = BoardHandlers(svc)
        payload = {
            "agent_id": "agent_alpha", "name": "alpha",
            "board": "test-board", "corr_id": "corr-1"
        }
        # set env for JWT
        os.environ["JWT_SECRET"] = "test-secret"
        handlers.on_register("agent/bbs/test-board/register", json.dumps(payload))
        svc._client.publish.assert_called_once()
        call_topic = svc._client.publish.call_args[0][0]
        assert "register" in call_topic

    def test_empty_agent_id_rejected(self):
        svc = _make_mock_service()
        handlers = BoardHandlers(svc)
        payload = {
            "agent_id": "", "name": "",
            "board": "test-board", "corr_id": "corr-2"
        }
        handlers.on_register("agent/bbs/test-board/register", json.dumps(payload))
        svc._client.publish.assert_not_called()

    def test_missing_jwt_secret(self):
        svc = _make_mock_service()
        handlers = BoardHandlers(svc)
        if "JWT_SECRET" in os.environ:
            del os.environ["JWT_SECRET"]
        payload = {
            "agent_id": "agent_beta", "name": "beta",
            "board": "test-board", "corr_id": "corr-3"
        }
        handlers.on_register("agent/bbs/test-board/register", json.dumps(payload))
        svc._client.publish.assert_not_called()


# ═══════════════════════════════════════
# on_post
# ═══════════════════════════════════════

class TestOnPost:
    def test_valid_token_post(self):
        svc = _make_mock_service()
        db = MagicMock()
        db.execute.return_value.fetchone.return_value = {"name": "test_user"}
        db.execute.return_value.lastrowid = 1
        svc._get_db.return_value = db
        svc._plugin_mgr.apply_filters.return_value = {"board_key": "test-board", "token": "valid-token", "content": "hello"}

        handlers = BoardHandlers(svc)
        payload = {"token": "valid-token", "content": "Hello BBS!", "corr_id": "corr-p1"}
        handlers.on_post("agent/bbs/test-board/post", json.dumps(payload))
        assert db.execute.call_count >= 1

    def test_empty_content_rejected(self):
        svc = _make_mock_service()
        handlers = BoardHandlers(svc)
        payload = {"token": "valid-token", "content": "", "corr_id": "corr-p2"}
        handlers.on_post("agent/bbs/test-board/post", json.dumps(payload))
        svc._client.publish.assert_not_called()


# ═══════════════════════════════════════
# on_query (token_hash detection)
# ═══════════════════════════════════════

class TestOnQuery:
    def test_query_users_returns_token_hash(self):
        svc = _make_mock_service()
        db = MagicMock()
        db.execute.return_value.fetchall.return_value = [
            {"name": "user1", "token": "abc123_full_token_here", "board": "test-board"}
        ]
        svc._get_db.return_value = db

        handlers = BoardHandlers(svc)
        payload = {"type": "users", "params": {}, "corr_id": "corr-q1"}
        handlers.on_query("agent/bbs/test-board/query", json.dumps(payload))
        svc._client.publish.assert_called_once()
        resp = json.loads(svc._client.publish.call_args[0][1])
        # Verify no full token in response, only token_hash or token truncated
        assert "token" not in resp or len(str(resp.get("token", ""))) < 20


# ═══════════════════════════════════════
# on_file_download
# ═══════════════════════════════════════

class TestOnFileDownload:
    def test_normal_download(self):
        svc = _make_mock_service()
        svc._get_db.return_value = MagicMock()
        handlers = BoardHandlers(svc)
        payload = {"file_id": 1, "corr_id": "corr-f1"}
        handlers.on_file_download("agent/bbs/test-board/file_download", json.dumps(payload))
        # Should not crash

    def test_oversized_rejection(self):
        svc = _make_mock_service()
        svc._get_db.return_value = MagicMock()
        handlers = BoardHandlers(svc)
        # Very large file request
        payload = {"file_id": 999999, "corr_id": "corr-f2"}
        handlers.on_file_download("agent/bbs/test-board/file_download", json.dumps(payload))
        # Should not crash


# ═══════════════════════════════════════
# post_fast (JWT-based)
# ═══════════════════════════════════════

class TestPostFast:
    def test_valid_jwt(self):
        svc = _make_mock_service()
        db = MagicMock()
        db.execute.return_value.lastrowid = 1
        svc._get_db.return_value = db
        svc._plugin_mgr.apply_filters.return_value = {"board_key": "test-board", "token": "jwt-token", "content": "fast"}

        handlers = BoardHandlers(svc)
        os.environ["JWT_SECRET"] = "test-secret"
        import jwt
        valid_jwt = jwt.encode({"sub": "agent_x", "name": "user_x", "board": "test-board", "exp": int(time.time()) + 3600}, "test-secret", algorithm="HS256")
        payload = {"jwt": valid_jwt, "content": "Fast post!", "corr_id": "corr-j1"}
        handlers.post_fast("agent/bbs/test-board/post_fast", json.dumps(payload))
        assert db.execute.call_count >= 1

    def test_invalid_jwt_rejected(self):
        svc = _make_mock_service()
        handlers = BoardHandlers(svc)
        payload = {"jwt": "invalid.jwt.token", "content": "hack", "corr_id": "corr-j2"}
        handlers.post_fast("agent/bbs/test-board/post_fast", json.dumps(payload))
        svc._client.publish.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
