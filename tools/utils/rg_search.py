"""
rg_search.py — ripgrep 全文搜索包装器

快速搜索文件内容（比 Python 遍历快 50-100x）。
依赖: tools/bin/rg.exe（从 .marscode 搬来的 ripgrep v13.0.0）

用法:
    from tools.utils.rg_search import rg_search
    results = rg_search("pattern", root_dir="D:/project", file_types=["py", "js"])
    
    # 命令行
    python -m tools.utils.rg_search "pattern" --root D:/project --type py
"""

import subprocess
import json
import os
from pathlib import Path
from typing import List, Optional, Dict, Any

RG_PATH = Path(__file__).resolve().parent.parent / "bin" / "rg.exe"


def rg_search(
    pattern: str,
    root_dir: str = None,
    file_types: List[str] = None,
    regex: bool = True,
    ignore_case: bool = False,
    max_results: int = 100,
    context_lines: int = 0,
    fixed_strings: bool = False,
    globs: List[str] = None,
    exclude_globs: List[str] = None,
    json_output: bool = True,
) -> List[Dict[str, Any]]:
    """
    使用 ripgrep 搜索文件内容。

    Args:
        pattern: 搜索模式（正则或普通字符串）
        root_dir: 搜索根目录（默认当前工作目录）
        file_types: 文件类型过滤，如 ["py", "js", "md"]
        regex: 是否将 pattern 视为正则（默认 True）
        ignore_case: 忽略大小写
        max_results: 最大返回结果数
        context_lines: 匹配行上下文的行数
        fixed_strings: 纯文本搜索（非正则）
        globs: 额外的 glob 包含模式，如 ["*.py", "*.js"]
        exclude_globs: 排除的 glob 模式，如 ["node_modules/**"]
        json_output: 返回结构化 JSON（否则返回纯文本行）

    Returns:
        匹配结果列表，每项包含 {path, line_number, line, lines} 等字段
    """
    if not RG_PATH.exists():
        # 尝试从 PATH 找
        import shutil
        rg_in_path = shutil.which("rg")
        if rg_in_path:
            rg_exe = rg_in_path
        else:
            raise FileNotFoundError(
                f"ripgrep not found at {RG_PATH} and not in PATH. "
                "Run setup first: copy rg.exe to tools/bin/"
            )
    else:
        rg_exe = str(RG_PATH)

    if root_dir is None:
        root_dir = os.getcwd()

    cmd = [rg_exe]

    # 输出格式
    if json_output:
        cmd.extend(["--json"])
    
    # 上下文行
    if context_lines > 0:
        cmd.extend(["-C", str(context_lines)])
    
    # 大小写
    if ignore_case:
        cmd.append("-i")
    
    # 纯文本 vs 正则
    if fixed_strings:
        cmd.append("-F")
    elif not regex:
        cmd.append("--fixed-strings")
    
    # 文件类型过滤
    if file_types:
        for ft in file_types:
            cmd.extend(["--type-add", f"custom:*.{ft}"])
            cmd.append("--type")
            cmd.append("custom")
    
    # 自定义 glob 包含
    if globs:
        for g in globs:
            cmd.extend(["-g", g])
    
    # 排除 glob
    if exclude_globs:
        for g in exclude_globs:
            cmd.extend(["-g", f"!{g}"])
    
    # 最大结果
    cmd.extend(["-m", str(max_results)])
    
    # 不搜索隐藏文件（以 . 开头的目录）
    cmd.append("--no-ignore")
    
    # pattern
    cmd.append(pattern)
    
    # root dir
    cmd.append(root_dir)

    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=30,
        )
    except subprocess.TimeoutExpired:
        return [{"error": f"Search timeout (>30s) for pattern: {pattern}"}]
    except FileNotFoundError:
        return [{"error": f"ripgrep executable not found: {rg_exe}"}]

    if json_output:
        return _parse_json_output(result.stdout, result.stderr)
    else:
        return _parse_text_output(result.stdout, result.stderr, pattern)


def _parse_json_output(stdout: str, stderr: str) -> List[Dict[str, Any]]:
    """解析 ripgrep --json 输出"""
    results = []
    for line in stdout.splitlines():
        if not line.strip():
            continue
        try:
            obj = json.loads(line)
        except json.JSONDecodeError:
            continue
        
        if obj.get("type") == "match":
            data = obj.get("data", {})
            path = data.get("path", {}).get("text", "")
            results.append({
                "path": path,
                "line_number": data.get("line_number"),
                "line": data.get("lines", {}).get("text", "").rstrip("\n"),
                "absolute_offset": data.get("absolute_offset"),
            })
    
    if stderr:
        # 非致命错误（如二进制文件跳过）可能出现在 stderr
        for line in stderr.splitlines():
            if "error" in line.lower() and "WARNING" not in line:
                results.append({"error": line})
    
    return results


def _parse_text_output(stdout: str, stderr: str, pattern: str) -> List[Dict[str, Any]]:
    """解析纯文本输出"""
    results = []
    for line in stdout.splitlines():
        # ripgrep 默认格式: filepath:lineno:content
        if ":" in line:
            parts = line.split(":", 2)
            if len(parts) == 3:
                results.append({
                    "path": parts[0],
                    "line_number": int(parts[1]) if parts[1].isdigit() else 0,
                    "line": parts[2],
                })
    return results


def rg_search_files(
    pattern: str,
    root_dir: str = None,
    globs: List[str] = None,
    max_results: int = 50,
) -> List[str]:
    """
    仅返回匹配的文件路径（去重），不返回具体行。
    适合快速找包含某内容的文件。
    """
    if root_dir is None:
        root_dir = os.getcwd()

    cmd = [str(RG_PATH), "-l", "-m", str(max_results)]
    
    if globs:
        for g in globs:
            cmd.extend(["-g", g])
    
    cmd.extend([pattern, root_dir])
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
    except subprocess.TimeoutExpired:
        return []
    
    return [f for f in result.stdout.splitlines() if f.strip()]


# ========== 命令行入口 ==========
if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="rg_search: 全文搜索工具")
    parser.add_argument("pattern", help="搜索模式")
    parser.add_argument("--root", "-r", default=None, help="搜索根目录")
    parser.add_argument("--type", "-t", nargs="*", default=None, help="文件类型，如 py js md")
    parser.add_argument("--ignore-case", "-i", action="store_true", help="忽略大小写")
    parser.add_argument("--context", "-C", type=int, default=0, help="上下文行数")
    parser.add_argument("--fixed", "-F", action="store_true", help="纯文本搜索（非正则）")
    parser.add_argument("--files-only", "-l", action="store_true", help="只返回文件名")
    parser.add_argument("--max", "-m", type=int, default=100, help="最大结果数")
    parser.add_argument("--plain", action="store_true", help="纯文本输出（非 JSON）")
    
    args = parser.parse_args()

    if args.files_only:
        files = rg_search_files(
            pattern=args.pattern,
            root_dir=args.root,
            globs=[f"*.{t}" for t in args.type] if args.type else None,
            max_results=args.max,
        )
        for f in files:
            print(f)
    else:
        results = rg_search(
            pattern=args.pattern,
            root_dir=args.root,
            file_types=args.type,
            ignore_case=args.ignore_case,
            context_lines=args.context,
            fixed_strings=args.fixed,
            max_results=args.max,
            json_output=not args.plain,
        )
        if args.plain:
            for r in results:
                if "error" in r:
                    print(f"[ERR] {r['error']}")
                else:
                    print(f"{r['path']}:{r['line_number']}:{r['line']}")
        else:
            print(json.dumps(results, indent=2, ensure_ascii=False))
