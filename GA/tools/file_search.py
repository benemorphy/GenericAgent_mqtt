"""
文件搜索工具 — 支持 es.exe (Everything SDK) 与 Python fallback

es.exe 路径: D:\open_claw_agent\Beneh\GA\tools\es.exe

用法:
    from tools.file_search import search_files, search_name, es_search

    # 使用 es.exe 全盘搜索（推荐）
    files = es_search("*.md")           # 全盘搜索 .md 文件
    files = es_search("config*.json")   # 支持通配符

    # 按 glob 模式搜索（Python fallback）
    files = search_files("*.py", root="D:/project")

    # 按文件名关键字搜索（Python fallback）
    files = search_name("config", root="D:/project")
"""

import subprocess, os
from pathlib import Path
from typing import List, Optional, Union

_ES_PATH = Path(__file__).parent / "es.exe"
_ES_AVAILABLE = _ES_PATH.is_file()


def es_search(pattern: str, root: str = "", max_results: int = 100) -> List[Path]:
    """
    使用 Everything SDK (es.exe) 执行全盘搜索。返回速度远快于 Python fallback。

    Args:
        pattern: 搜索模式，支持通配符如 "*.md", "config*.json"
        root: 搜索路径前缀（可选），如 "D:\\projects"
        max_results: 最大返回数

    Returns:
        匹配的文件路径列表
    """
    if not _ES_AVAILABLE:
        return []
    try:
        args = [_ES_PATH, pattern, "-n", str(max_results)]
        if root:
            args.extend(["-path", root])
        r = subprocess.run(args, capture_output=True, text=True, timeout=30)
        if r.returncode != 0:
            return []
        paths = [Path(line.strip()) for line in r.stdout.strip().split('\n') if line.strip()]
        return paths
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return []


def search_files(pattern: str, root: Union[str, Path] = ".", max_results: int = 100) -> List[Path]:
    """
    按 glob 模式搜索文件（递归）。

    Args:
        pattern: glob 模式，如 "*.py", "**/test_*.py", "data/*.csv"
        root: 搜索根目录
        max_results: 最大返回数，防止返回过多

    Returns:
        匹配的文件路径列表
    """
    root_path = Path(root).resolve()
    if not root_path.is_dir():
        return []

    results = []
    for f in root_path.rglob(pattern):
        if f.is_file():
            results.append(f)
            if len(results) >= max_results:
                break
    return results


def search_name(name_part: str, root: Union[str, Path] = ".",
                roots: Optional[List[Union[str, Path]]] = None,
                max_results: int = 100) -> List[Path]:
    """
    按文件名关键字搜索（递归），不区分大小写。

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
        for f in root_path.rglob("*"):
            if f.is_file() and name_lower in f.name.lower():
                results.append(f)
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
    results = []
    for f in root_path.rglob(pattern):
        if not f.is_file():
            continue
        try:
            content = f.read_text(encoding='utf-8', errors='ignore')
            if text_lower in content.lower():
                results.append(f)
                if len(results) >= max_results:
                    break
        except Exception:
            continue
    return results
