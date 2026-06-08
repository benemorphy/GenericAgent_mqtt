"""
安全审计模块 — 检出推送/上传前扫描敏感信息

用法:
    from tools.security.security_audit import audit_files, SENSITIVE_PATTERNS
    ok, report = audit_files()
    ok, report = audit_files(files=['path/to/file.py'])
"""

import os
import subprocess

SENSITIVE_PATTERNS = [
    "sk-", "ghp_", "gho_", "ghu_", "ghs_", "ghr_",
    "api_key", "apikey", "api_secret", "apisecret",
    "password", "passwd", "secret", "token",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN PRIVATE KEY-----",
]

_BINARY_EXTS = {'.png', '.jpg', '.jpeg', '.gif', '.ico',
                '.woff', '.woff2', '.ttf', '.eot'}


def _parse_git_status(status_text):
    """解析 git status --porcelain 输出

    输出格式每行: XY path
      X = 暂存区状态, Y = 工作区状态
      空格 = 无变更, ? = 未追踪
      例: " M tools/x.py" = 工作区修改,  "?? new.py" = 未追踪
    """
    files = []
    for line in status_text.split("\n"):
        line = line.rstrip()
        if not line:
            continue
        # XY 是两个字符, 第3字符是空格, 之后是路径
        xy = line[:2]
        path = line[3:]
        # 任一位置为 M/A/? 都算改动
        if 'M' in xy or 'A' in xy or '?' in xy:
            files.append(path)
    return files


def audit_files(files=None):
    """扫描文件中的敏感信息

    Args:
        files: 文件路径列表。为 None 时自动从 git status 读取。

    Returns:
        (ok, details, summary) 三元组
    """
    # 默认扫描 git 暂存文件
    if files is None:
        status = subprocess.run(
            ["git", "status", "--porcelain"],
            capture_output=True, text=True, timeout=30
        )
        files = _parse_git_status(status.stdout)
    if not files:
        return True, [], "无文件改动"

    sensitive_found = []
    for f in files:
        if not os.path.exists(f):
            continue
        ext = os.path.splitext(f)[1].lower()
        if ext in _BINARY_EXTS:
            continue
        if os.path.getsize(f) > 500 * 1024:
            continue
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            for pattern in SENSITIVE_PATTERNS:
                if pattern in content:
                    for i, line in enumerate(content.split('\n'), 1):
                        if pattern in line:
                            masked = line.strip()[:60].replace(
                                pattern, pattern[:3] + '***' + pattern[-3:]
                            )
                            sensitive_found.append(
                                f"  [WARN] {f}:{i}  {masked}"
                            )
        except (IOError, OSError):
            pass

    if sensitive_found:
        return False, sensitive_found, "发现可能的敏感信息泄露"
    return True, [], "审计通过，无安全风险"


def print_report(ok, details, summary):
    """格式化打印审计报告"""
    print(f"\n{'='*50}")
    print(f"[审计] {'PASS' if ok else 'FAIL'}: {summary}")
    print(f"{'='*50}")
    if details:
        for d in details:
            print(d)
    return ok
