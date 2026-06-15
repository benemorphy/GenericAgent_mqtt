"""
Shim: re-export from tools.mcp.tool_definitions for backward compatibility.
Originally tools.tool_definitions was moved to tools/mcp/.
"""
import warnings
warnings.warn("tools.tool_definitions is deprecated, use tools.mcp.tool_definitions instead",
              DeprecationWarning, stacklevel=2)

from tools.mcp.tool_definitions import (
    code_run,
    ask_user,
    web_scan,
    web_execute_js,
    file_patch,
    file_read,
)

__all__ = [
    "code_run",
    "ask_user",
    "web_scan",
    "web_execute_js",
    "file_patch",
    "file_read",
]
