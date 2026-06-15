"""
文件搜索工具 — 支持 Everything SDK (es.exe) 与 Python fallback

调用者无需关心底层：有 Everything 自动走 es.exe（毫秒级），否则自动降级 os.walk。

用法:
    from tools.utils.file_search import search_files, search_name, es_search, es_available

    # [推荐] 自动路由 — Everything 可用则走 es.exe，否则降级 os.walk
    files = search_files("*.md", root="D:/project")
    files = search_name("config", root="D:/project")
    files = search_content("TODO", root="D:/project")

    # [直接调用 es.exe] 无降级，需自行检查 es_available()
    if es_available():
        files = es_search("*.md")
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
        r = subprocess.run(args, capture_output=True, text=True, timeout=5)
        if r.returncode != 0:
            return []
        paths = [Path(line.strip()) for line in r.stdout.strip().split('\n') if line.strip()]
        return paths
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def search_files(pattern: str, root: Union[str, Path] = ".", max_results: int = 100) -> List[Path]:
    """
    按 glob 模式搜索文件。

    自动路由: es.exe 可用时走 Everything（毫秒级），否则降级 os.walk + fnmatch。

    Args:
        pattern: glob 模式，如 "*.py", "data/*.csv"
        root: 搜索根目录
        max_results: 最大返回数

    Returns:
        匹配的文件路径列表
    """
    # [自动路由] 优先 es.exe
    if es_available():
        return es_search(pattern, root=str(root), max_results=max_results)

    # [降级] Python os.walk fallback
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        return []
    results = []
    ext_filter = None
    if pattern.startswith("*."):
        ext_filter = pattern[1:]
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
    按文件名关键字搜索，不区分大小写。

    自动路由: es.exe 可用时走 Everything，否则降级 os.walk。

    Args:
        name_part: 文件名包含的关键字
        root: 单个搜索根目录（与 roots 二选一）
        roots: 多个搜索根目录列表
        max_results: 最大返回数

    Returns:
        匹配的文件路径列表
    """
    # [自动路由] 优先 es.exe: 将关键字转为通配符 *keyword*
    if es_available():
        pattern = f"*{name_part}*"
        if roots:
            for r in roots:
                result = es_search(pattern, root=str(r), max_results=max_results)
                if result:
                    return result
            return []
        return es_search(pattern, root=str(root), max_results=max_results)

    # [降级] Python os.walk fallback
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

    文件名过滤优先走 es.exe（可用时），内容匹配仍用 Python 逐文件扫描。

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

    # [加速文件名过滤] es.exe 可用时先获取文件列表，跳过 os.walk
    candidate_files: List[Path] = []
    if es_available():
        candidate_files = es_search(pattern, root=str(root), max_results=max_results * 2)
    else:
        ext_filter = None
        if pattern.startswith("*."):
            ext_filter = pattern[1:]
        for dirpath, _, filenames in os.walk(str(root_path)):
            for fn in filenames:
                if ext_filter:
                    if not fn.endswith(ext_filter):
                        continue
                elif not fnmatch.fnmatch(fn, pattern):
                    continue
                candidate_files.append(Path(dirpath) / fn)
                if len(candidate_files) >= max_results * 2:
                    break

    # [内容匹配] 逐文件扫描
    text_lower = text.lower()
    results = []
    for fpath in candidate_files:
        try:
            content = fpath.read_text(encoding='utf-8', errors='ignore')
            if text_lower in content.lower():
                results.append(fpath)
                if len(results) >= max_results:
                    return results
        except Exception:
            continue
    return results
