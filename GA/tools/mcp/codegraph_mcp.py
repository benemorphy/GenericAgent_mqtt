"""CodeGraph MCP 工具封装 (colbymchenry/codegraph)

通过 colbchenry/codegraph CLI 子命令，提供代码分析能力。
每次调用独立启动进程，无需常驻。

用法:
    from tools.mcp.codegraph_mcp import codegraph_call
    result = codegraph_call("codegraph_get_symbol_info", {"symbol": "foo"})

可用工具列表见: https://github.com/colbymchenry/codegraph
"""

import os
import json
import subprocess
import shutil
import time

_GA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 查找 colbchenry/codegraph CLI
_CODEGRAPH_CLI = shutil.which('codegraph')

# 新旧工具名映射
_TOOL_MAP = {
    # 新 CLI 原生工具名
    "codegraph_search":       ("query",   {"query": "query", "symbol": "symbol"}, True),
    "codegraph_callers":      ("callers", {"symbol": "symbol"}, True),
    "codegraph_callees":      ("callees", {"symbol": "symbol"}, True),
    "codegraph_impact":       ("impact",  {"symbol": "symbol"}, True),
    "codegraph_files":        ("files",   {}, True),
    "codegraph_status":       ("status",  {}, True),
    # 旧兼容工具名
    "codegraph_get_symbol_info":    ("query",   {"symbol": "symbol"}, True),
    "codegraph_symbol_search":      ("query",   {"symbol": "symbol"}, True),
    "codegraph_get_callers":        ("callers", {"symbol": "symbol"}, True),
    "codegraph_get_callees":        ("callees", {"symbol": "symbol"}, True),
    "codegraph_analyze_impact":     ("impact",  {"symbol": "symbol"}, True),
    "codegraph_get_call_graph":     ("callers", {"symbol": "symbol"}, True),
    "codegraph_get_module_summary": ("files",   {}, True),
    "codegraph_find_by_imports":    ("query",   {"query": "query"}, True),
    "codegraph_find_entry_points":  ("query",   {"query": "query"}, True),
    "codegraph_search_by_pattern":  ("query",   {"query": "query"}, True),
    "codegraph_search_by_error":    ("query",   {"query": "query"}, True),
    "codegraph_find_implementors":  ("query",   {"symbol": "symbol"}, True),
    "codegraph_find_hot_paths":     ("callers", {"symbol": "symbol"}, True),
    "codegraph_traverse_graph":     ("impact",  {"symbol": "symbol"}, True),
    "codegraph_analyze_complexity": ("callers", {"symbol": "symbol"}, True),
    "codegraph_get_detailed_symbol":("query",   {"symbol": "symbol"}, True),
    "codegraph_find_dead_imports":  ("query",   {"query": "query"}, True),
}

# 新 CL1 原生支持的工具
_NATIVE_TOOLS = [
    # 直接映射到新CLI子命令的
    "codegraph_search",
    "codegraph_callers",
    "codegraph_callees",
    "codegraph_impact",
    "codegraph_files",
    "codegraph_status",
    # 旧兼容名也保留
    "codegraph_get_symbol_info",
    "codegraph_symbol_search",
    "codegraph_get_callers",
    "codegraph_get_callees", 
    "codegraph_analyze_impact",
    "codegraph_get_call_graph",
    "codegraph_get_module_summary",
    "codegraph_find_by_imports",
    "codegraph_find_entry_points",
    "codegraph_search_by_pattern",
    "codegraph_search_by_error",
    "codegraph_find_implementors",
    "codegraph_find_hot_paths",
    "codegraph_traverse_graph",
    "codegraph_analyze_complexity",
    "codegraph_get_detailed_symbol",
    "codegraph_find_dead_imports",
]


def _run_cli(subcommand: str, args_list: list, workspace: str, timeout: int) -> dict:
    """运行 codegraph CLI 子命令，返回解析后的结果"""
    if _CODEGRAPH_CLI is None:
        return {"status": "error", "msg": "codegraph CLI 未找到，请执行: npm i -g @colbymchenry/codegraph"}

    # status 不支持 -p 参数
    supports_path = subcommand not in ("status",)
    cmd = [_CODEGRAPH_CLI, subcommand] + args_list + ["-j"]
    if supports_path and workspace:
        cmd.extend(["-p", workspace])

    try:
        r = subprocess.run(
            cmd,
            capture_output=True, text=True, timeout=timeout,
            cwd=workspace or _GA_ROOT,
        )
        result = {
            "status": "success" if r.returncode == 0 else "error",
            "exit_code": r.returncode,
        }
        if r.stdout:
            try:
                result["data"] = json.loads(r.stdout)
            except json.JSONDecodeError:
                result["data"] = r.stdout
        if r.stderr:
            lines = [l for l in r.stderr.split('\n') if len(l.strip()) > 0]
            result["stderr"] = '\n'.join(lines[-20:]) if lines else ''
        return result
    except subprocess.TimeoutExpired:
        return {"status": "error", "msg": f"执行超时 ({timeout}s)"}
    except FileNotFoundError as e:
        return {"status": "error", "msg": f"执行失败: {e}"}
    except Exception as e:
        return {"status": "error", "msg": str(e)}


def codegraph_call(tool_name: str, tool_args: dict = None,
                   workspace: str = None, max_files: int = 5000,
                   graph_only: bool = True, timeout: int = 60) -> dict:
    """调用 CodeGraph 代码分析工具 (P0: SQLite优先, 失败回退CLI)

    Args:
        tool_name: 工具名
        tool_args: 工具参数字典
        workspace: 项目路径，默认 GA 根目录
        max_files: 最大索引文件数（保留，新CLI自动索引）
        graph_only: 保留参数，新CLI不区分
        timeout: 超时秒数

    Returns:
        {"status": "success"|"error", "data": ..., "stderr": ...}
    """
    # P0: SQLite 原生优先 (500x加速)
    try:
        from tools.mcp.codegraph_db import codegraph_call as _sqlite_call
        sqlite_result = _sqlite_call(tool_name, tool_args, workspace, max_files, graph_only, timeout)
        if sqlite_result.get("status") == "success" and sqlite_result.get("source") == "sqlite":
            sqlite_result.pop("source", None)
            sqlite_result.pop("query_ms", None)
            return sqlite_result
    except ImportError:
        pass
    except Exception:
        pass
    
    # 回退: CLI 调用
    workspace = workspace or _GA_ROOT
    tool_args = tool_args or {}

    # 检查新原生工具名
    if tool_name in ("codegraph_status",):
        return _run_cli("status", [], workspace, timeout)

    if tool_name in ("codegraph_files", "codegraph_get_module_summary"):
        return _run_cli("files", [], workspace, timeout)

    # 通过映射表处理
    mapping = _TOOL_MAP.get(tool_name)
    if mapping is None:
        return {"status": "error", "msg": f"未知工具: {tool_name}。可用工具见 available_tools()"}

    subcommand, field_map, supported = mapping
    if not supported:
        return {"status": "error", "msg": f"工具 {tool_name} 当前版本暂不支持"}

    # 提取查询参数
    query_value = None
    for old_field, new_field in field_map.items():
        val = tool_args.get(old_field) or tool_args.get(new_field)
        if val:
            query_value = val
            break

    if subcommand == "files":
        return _run_cli("files", [], workspace, timeout)

    if query_value is None:
        return {"status": "error", "msg": f"缺少查询参数 ({', '.join(field_map.values())})"}

    return _run_cli(subcommand, [str(query_value)], workspace, timeout)


def available_tools() -> list:
    """返回所有可用工具名列表"""
    return _NATIVE_TOOLS
