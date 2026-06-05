"""
Session Compactor — 后台自动压缩 L4 原始历史

自动检测 memory/L4_raw_sessions/ 大小，超过阈值时触发压缩。
7 天冷却期，daemon 线程不阻塞主流程。

用法:
    from tools.session_compactor import start_auto_compact
    start_auto_compact()  # 启动后台线程
"""

import os
import sys
import time
import threading
import logging
import subprocess as _sp

log = logging.getLogger("session_compactor")
subprocess = _sp

# ── 配置 ──
_THRESHOLD_KB = 500          # 超过此大小触发压缩
_COMPACT_INTERVAL = 172800    # 压缩检测间隔(秒) = 48 小时
_RETENTION_DAYS = 30         # L4 原始会话保留天数
_COOLDOWN_DAYS = 7           # 压缩冷却期(天)
_COMPACT_SCRIPT = None       # 压缩脚本路径缓存

# ── L4 路径 ──
def _get_l4_path() -> str:
    """查找 L4_raw_sessions/ 目录"""
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'memory', 'L4_raw_sessions'),
        os.path.join(os.getcwd(), 'memory', 'L4_raw_sessions'),
    ]
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.isdir(p):
            return p
    # 不存在则尝试创建
    l4 = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'memory', 'L4_raw_sessions'))
    os.makedirs(l4, exist_ok=True)
    return l4


def _get_dir_size_kb(path: str) -> float:
    """递归计算目录大小(KB)"""
    from tools.file_search import search_files
    total = sum(f.stat().st_size for f in search_files("*", root=path))
    return total / 1024.0


def _get_compact_script() -> str:
    """查找已有压缩脚本"""
    global _COMPACT_SCRIPT
    if _COMPACT_SCRIPT:
        return _COMPACT_SCRIPT
    candidates = [
        os.path.join(os.path.dirname(os.path.abspath(__file__)), 'compress_session.py'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools', 'compress_session.py'),
        os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'memory', 'L4_raw_sessions', 'compress_session.py'),
    ]
    for p in candidates:
        p = os.path.abspath(p)
        if os.path.isfile(p):
            _COMPACT_SCRIPT = p
            return p
    return None


def _last_compact_file() -> str:
    """冷却标记文件路径"""
    temp_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'temp')
    os.makedirs(temp_dir, exist_ok=True)
    return os.path.join(temp_dir, '.last_session_compact')


def _should_compact() -> bool:
    """检查是否满足压缩条件（冷却期 + 大小阈值）"""
    # 冷却期检查
    marker = _last_compact_file()
    if os.path.isfile(marker):
        age = time.time() - os.path.getmtime(marker)
        if age < _COOLDOWN_DAYS * 86400:
            remaining = int((_COOLDOWN_DAYS * 86400 - age) / 86400)
            log.debug(f"冷却中，剩余 {remaining} 天")
            return False

    # 大小检查
    l4_path = _get_l4_path()
    size_kb = _get_dir_size_kb(l4_path)
    if size_kb < _THRESHOLD_KB:
        log.debug(f"L4 大小 {size_kb:.0f}KB < {_THRESHOLD_KB}KB，跳过")
        return False

    return True


def _do_compact():
    """执行压缩"""
    script = _get_compact_script()
    if not script:
        log.warning("未找到 compress_session.py，跳过压缩")
        return False

    log.info(f"L4 自动压缩触发: size > {_THRESHOLD_KB}KB")
    result = subprocess.run(
        [sys.executable, script],
        capture_output=True, text=True, timeout=120
    )
    if result.returncode == 0:
        # 更新冷却标记
        marker = _last_compact_file()
        with open(marker, 'w') as f:
            f.write(str(time.time()))
        log.info(f"L4 压缩完成 (exit={result.returncode})")
        return True
    else:
        log.warning(f"L4 压缩失败: {result.stderr[:200]}")
        return False


def auto_compact():
    """单次压缩检测与执行（供后台线程调用）"""
    try:
        if _should_compact():
            _do_compact()
    except Exception as e:
        log.warning(f"自动压缩异常(非致命): {e}")


def rotate_l4_sessions(retain_days: int = _RETENTION_DAYS) -> int:
    """删除 L4_raw_sessions 中超过 retain_days 的原始会话文件

    Args:
        retain_days: 保留天数，默认 30

    Returns:
        删除的文件数
    """
    l4_path = _get_l4_path()
    cutoff = time.time() - retain_days * 86400
    deleted = 0
    from tools.file_search import search_files
    for fpath in search_files("*", root=l4_path):
        if fpath.is_file() and fpath.stat().st_mtime < cutoff:
            os.remove(str(fpath))
            deleted += 1
    if deleted > 0:
        log.info(f"L4 轮换: 删除了 {deleted} 个超过 {retain_days} 天的会话文件")
    return deleted


def start_auto_compact(interval_seconds: int = None):
    """启动后台自动压缩 + L4 轮换线程

    Args:
        interval_seconds: 检测间隔(秒)，默认 _COMPACT_INTERVAL (48h)
    """
    if interval_seconds is None:
        interval_seconds = _COMPACT_INTERVAL

    def _loop():
        log.info(f"后台维护线程启动 (间隔={interval_seconds/3600:.0f}h)")
        while True:
            auto_compact()
            rotate_l4_sessions()
            time.sleep(interval_seconds)

    t = threading.Thread(target=_loop, daemon=True)
    t.start()
    return t


# ── 独立运行 ──
if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s %(message)s")
    l4 = _get_l4_path()
    size = _get_dir_size_kb(l4)
    print(f"L4 路径: {l4}")
    print(f"L4 大小: {size:.0f} KB")
    script = _get_compact_script()
    print(f"压缩脚本: {script or '未找到'}")
    print(f"冷却标记: {_last_compact_file()}")
    print(f"允许压缩: {_should_compact()}")
