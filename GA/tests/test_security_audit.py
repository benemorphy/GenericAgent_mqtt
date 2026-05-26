"""单元测试: tools/security_audit.py"""
import os, sys, json, tempfile
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from tools.security_audit import audit_files, _parse_git_status, SENSITIVE_PATTERNS


class TestParseGitStatus:
    def test_modified_file(self):
        files = _parse_git_status(" M tools/md_server.py\n")
        assert "tools/md_server.py" in files

    def test_new_file(self):
        files = _parse_git_status("?? new_file.py\n")
        assert "new_file.py" in files

    def test_empty(self):
        files = _parse_git_status("")
        assert files == []

    def test_ignored_others(self):
        files = _parse_git_status("?? foo.py\n M bar.py\n D deleted.py\n")
        # 删除的文件不应包含
        assert "foo.py" in files
        assert "bar.py" in files
        assert "deleted.py" not in files


class TestAuditFiles:
    def test_clean_file(self):
        """纯文本文件应通过审计"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                         delete=False, encoding='utf-8') as f:
            f.write("print('hello')\nx = 1 + 2\n")
            fname = f.name
        try:
            ok, details, summary = audit_files(files=[fname])
            assert ok is True
            assert details == []
        finally:
            os.unlink(fname)

    def test_matches_api_key(self):
        """含 sk- 模式应触发告警"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                         delete=False, encoding='utf-8') as f:
            f.write('api_key = "sk-ant-abc123xyz"\n')
            fname = f.name
        try:
            ok, details, summary = audit_files(files=[fname])
            assert ok is False
            assert len(details) >= 1
        finally:
            os.unlink(fname)

    def test_matches_github_token(self):
        """含 ghp_ 模式应触发告警"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                         delete=False, encoding='utf-8') as f:
            f.write('token = "ghp_xxxxxxxxxxxxxxxxxxxx"\n')
            fname = f.name
        try:
            ok, details, summary = audit_files(files=[fname])
            assert ok is False
        finally:
            os.unlink(fname)

    def test_matches_private_key(self):
        """含私钥头部应触发告警"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.key',
                                         delete=False, encoding='utf-8') as f:
            f.write("-----BEGIN RSA PRIVATE KEY-----\nABC123\n")
            fname = f.name
        try:
            ok, details, summary = audit_files(files=[fname])
            assert ok is False
        finally:
            os.unlink(fname)

    def test_binary_file_skipped(self):
        """二进制文件应跳过"""
        with tempfile.NamedTemporaryFile(suffix='.png',
                                         delete=False) as f:
            f.write(b'\x89PNG\r\n\x1a\n')
            fname = f.name
        try:
            ok, details, summary = audit_files(files=[fname])
            assert ok is True
        finally:
            os.unlink(fname)

    def test_large_file_skipped(self):
        """超大文件应跳过"""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.py',
                                         delete=False, encoding='utf-8') as f:
            f.write('x\n' * 100_000)
            fname = f.name
        try:
            ok, details, summary = audit_files(files=[fname])
            assert ok is True
        finally:
            os.unlink(fname)

    def test_not_exist_file(self):
        """不存在的文件应优雅跳过"""
        ok, details, summary = audit_files(files=['/tmp/_nonexistent_xyz.py'])
        assert ok is True


class TestSensitivePatterns:
    def test_has_expected_patterns(self):
        assert "sk-" in SENSITIVE_PATTERNS
        assert "ghp_" in SENSITIVE_PATTERNS
        assert "password" in SENSITIVE_PATTERNS
        assert "secret" in SENSITIVE_PATTERNS
        assert "-----BEGIN RSA PRIVATE KEY-----" in SENSITIVE_PATTERNS
