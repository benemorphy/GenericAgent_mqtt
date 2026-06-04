"""
文件搜索工具 — 支持 Everything SDK (es.exe) 与 Python fallback

es.exe 路径: D:\open_claw_agent\Beneh\GA\tools\es.exe

用法:
    from tools.file_search import search_files, search_name, es_search, es_available

    # 优先尝试 es.exe（推荐，需 Everything 服务运行中）
    if es_available():
        files = es_search("*.md")
    else:
        # 自动 fallback 到 Python（不报错不等待）
        files = search_files("*.md", root="D:/project")
"""
import subprocess, os, fnmatch
from pathlib import Path
from typing import List, Optional, Union

_ES_PATH = Path(__file__).parent / "es.exe"
_ES_CACHE = [None]  # None=未检测, True=可用, False=不可用


def es_available() -> bool:
    """快速检测 es.exe 是否可用 (约 50ms, 只检测一次后缓存)"""
    if _ES_CACHE[0] is not None:
        return _ES_CACHE[0]
    if not _ES_PATH.is_file():
        _ES_CACHE[0] = False
        return False
    try:
        r = subprocess.run([str(_ES_PATH), "-n", "1", "es_avail_test"],
                           capture_output=True, text=True, timeout=2)
        _ES_CACHE[0] = (r.returncode == 0)
        return _ES_CACHE[0]
    except Exception:
        _ES_CACHE[0] = False
        return False


def es_search(pattern: str, root: str = "", max_results: int = 100) -> List[Path]:
    """
    使用 Everything SDK (es.exe) 执行全盘搜索。

    快速失败: es.exe 不可用时立即返回空列表，不浪费等待。

    Args:
        pattern: 搜索模式，支持通配符如 "*.md", "config*.json"
        root: 搜索路径前缀（可选），如 "D:\\projects"
        max_results: 最大返回数

    Returns:
        匹配的文件路径列表
    """
    if not es_available():
        return []
    try:
        args = [str(_ES_PATH), pattern, "-n", str(max_results)]
        if root:
            args.extend(["-path", root])
        r = subprocess.run(args, capture_output=True, text=True, timeout=5)  # 5s 快速失败
        if r.returncode != 0:
            return []
        paths = [Path(line.strip()) for line in r.stdout.strip().split('\n') if line.strip()]
        return paths
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def search_files(pattern: str, root: Union[str, Path] = ".", max_results: int = 100) -> List[Path]:
    """
    按 glob 模式搜索文件（递归 Python fallback）。

    优先使用 os.walk + fnmatch 过滤，速度快于 rglob。

    Args:
        pattern: glob 模式，如 "*.py", "data/*.csv"
        root: 搜索根目录
        max_results: 最大返回数

    Returns:
        匹配的文件路径列表
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        return []

    results = []
    # 提取文件后缀过滤 (如 *.py → ".py", * → None)
    ext_filter = None
    if pattern.startswith("*."):
        ext_filter = pattern[1:]  # ".py"

    for dirpath, _, filenames in os.walk(str(root_path)):
        for fn in filenames:
            if ext_filter:
                if not fn.endswith(ext_filter):
                    continue
            elif not fnmatch.fnmatch(fn, pattern):
                continue
            results.append(Path(dirpath) / fn)
            if len(results) >= max_results:
                return results
    return results


def search_name(name_part: str, root: Union[str, Path] = ".",
                roots: Optional[List[Union[str, Path]]] = None,
                max_results: int = 100) -> List[Path]:
    """
    按文件名关键字搜索（递归），不区分大小写。

    使用 os.walk 替代 rglob("*")，避免构建全量文件树。

    Args:
        name_part: 文件名包含的关键字
        root: 单个搜索根目录（与 roots 二选一）
        roots: 多个搜索根目录列表
        max_results: 最大返回数

    Returns:
        匹配的文件路径列表
    """
    if roots is None:
        roots = [root]

    name_lower = name_part.lower()
    results = []
    for r in roots:
        root_path = Path(r).resolve()
        if not root_path.is_dir():
            continue
        for dirpath, _, filenames in os.walk(str(root_path)):
            for fn in filenames:
                if name_lower in fn.lower():
                    results.append(Path(dirpath) / fn)
                    if len(results) >= max_results:
                        return results
    return results


def search_content(text: str, root: Union[str, Path] = ".",
                   pattern: str = "*", max_results: int = 50) -> List[Path]:
    """
    按文件内容搜索（文本文件中查找关键字）。

    Args:
        text: 要搜索的文本
        root: 搜索根目录
        pattern: 文件 glob 模式过滤，默认所有文件
        max_results: 最大返回数

    Returns:
        包含目标文本的文件路径列表
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        return []

    text_lower = text.lower()
    ext_filter = None
    if pattern.startswith("*."):
        ext_filter = pattern[1:]

    results = []
    for dirpath, _, filenames in os.walk(str(root_path)):
        for fn in filenames:
            if ext_filter:
                if not fn.endswith(ext_filter):
                    continue
            elif not fnmatch.fnmatch(fn, pattern):
                continue
            fpath = Path(dirpath) / fn
            try:
                content = fpath.read_text(encoding='utf-8', errors='ignore')
                if text_lower in content.lower():
                    results.append(fpath)
                    if len(results) >= max_results:
                        return results
            except Exception:
                continue
    return results
