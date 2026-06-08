"""
MemPalace MCP Server Launcher & Auto-Save Hook

启动 MemPalace MCP Server（SSE 传输）以暴露 32 个记忆工具。
集成自动会话保存 hook，在项目启动时自动同步记忆。

Usage:
    # 启动 MCP Server（后台）
    python mempalace_mcp_launcher.py start

    # 停止 MCP Server
    python mempalace_mcp_launcher.py stop

    # 查看状态
    python mempalace_mcp_launcher.py status

    # 自动保存当前会话（由项目框架调用）
    python mempalace_mcp_launcher.py save --session "session_name"
"""

import os
import sys
import json
import time
import signal
import subprocess
from pathlib import Path

# ── 路径配置 ──
_MEMORY_DIR = Path(__file__).parent
_GA_DIR = _MEMORY_DIR.parent
_PROJECT_DIR = _GA_DIR.parent
_VENV_PYTHON = _PROJECT_DIR / ".venv" / "Scripts" / "python.exe"
_VENV_MCP = _PROJECT_DIR / ".venv" / "Scripts" / "mempalace-mcp.exe"
_PALACE_PATH = _MEMORY_DIR / ".mempalace" / "palace"
_PID_FILE = _MEMORY_DIR / ".mcp_server.pid"
_LOG_FILE = _MEMORY_DIR / ".mcp_server.log"


def start_server():
    """启动 MemPalace MCP Server 后台进程。"""
    if _PID_FILE.exists():
        pid = int(_PID_FILE.read_text().strip())
        if _is_running(pid):
            print(f"MCP Server 已在运行 (PID: {pid})")
            return True
        _PID_FILE.unlink(missing_ok=True)

    if not _VENV_MCP.exists():
        print(f"错误: mempalace-mcp 未找到 ({_VENV_MCP})")
        print("提示: 确认 '.venv' 已安装 mempalace")
        return False

    if not _PALACE_PATH.exists():
        print(f"警告: Palace 路径不存在 ({_PALACE_PATH})")
        print("提示: 先运行 mempalace init")

    cmd = [str(_VENV_MCP), "--palace", str(_PALACE_PATH)]
    print(f"启动 MCP Server: {' '.join(cmd)}")

    try:
        proc = subprocess.Popen(
            cmd,
            stdout=open(_LOG_FILE, "w"),
            stderr=subprocess.STDOUT,
            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
        )
        _PID_FILE.write_text(str(proc.pid))
        print(f"MCP Server 已启动 (PID: {proc.pid})")
        print(f"日志: {_LOG_FILE}")
        time.sleep(1)
        return True
    except Exception as e:
        print(f"启动失败: {e}")
        return False


def stop_server():
    """停止 MCP Server。"""
    if not _PID_FILE.exists():
        print("MCP Server 未运行")
        return True

    pid = int(_PID_FILE.read_text().strip())
    try:
        if sys.platform == "win32":
            subprocess.run(["taskkill", "/F", "/PID", str(pid)], capture_output=True)
        else:
            os.kill(pid, signal.SIGTERM)
        _PID_FILE.unlink(missing_ok=True)
        print(f"MCP Server 已停止 (PID: {pid})")
        return True
    except Exception as e:
        print(f"停止失败: {e}")
        return False


def server_status():
    """检查 MCP Server 状态。"""
    if not _PID_FILE.exists():
        print("MCP Server: 未运行")
        return False

    pid = int(_PID_FILE.read_text().strip())
    if _is_running(pid):
        print(f"MCP Server: 运行中 (PID: {pid})")
        return True
    else:
        print(f"MCP Server: 已停止 (PID 文件残留)")
        _PID_FILE.unlink(missing_ok=True)
        return False


def _is_running(pid: int) -> bool:
    """检查 PID 是否在运行。"""
    try:
        if sys.platform == "win32":
            result = subprocess.run(
                ["tasklist", "/FI", f"PID eq {pid}"],
                capture_output=True, text=True, timeout=5
            )
            return str(pid) in result.stdout
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def auto_save(session_name: str = None):
    """自动保存当前会话到 MemPalace。

    由项目框架在会话结束时调用。
    """
    venv_python = str(_VENV_PYTHON)
    memory_dir = str(_MEMORY_DIR)
    palace_env = os.environ.copy()
    palace_env["MEMPALACE_PALACE_PATH"] = str(_PALACE_PATH)

    try:
        # 使用 mempalace mine 增量同步
        result = subprocess.run(
            [venv_python, "-m", "mempalace", "mine", memory_dir],
            capture_output=True, text=True, timeout=60, env=palace_env
        )
        print(f"Auto-save: {result.stdout[-200:]}")
        return True
    except Exception as e:
        print(f"Auto-save failed: {e}")
        return False


# ── MCP 工具集成说明 ──
MCP_TOOLS_SUMMARY = """
MemPalace MCP Server 提供以下工具（32个）：

记忆管理:
  - tool_status          : Palace 状态
  - tool_list_wings      : 列出所有 wing
  - tool_list_rooms      : 列出房间
  - tool_get_taxonomy    : 获取分类体系

搜索与查询:
  - tool_search          : 语义搜索
  - tool_search_wing     : 在指定 wing 中搜索
  - tool_search_room     : 在指定房间中搜索

会话管理:
  - tool_mine            : 挖掘文件到 Palace
  - tool_mine_session    : 挖掘单个会话
  - tool_sweep           : 清理 Palace
  - tool_compress        : 压缩 Palace

知识图谱:
  - tool_entity_query    : 查询实体
  - tool_relation_query  : 查询关系

集成方式:
  1. Claude Desktop: claude mcp add mempalace -- mempalace-mcp --palace <path>
  2. 项目内部: python mempalace_mcp_launcher.py start
"""


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(0)

    command = sys.argv[1]

    if command == "start":
        start_server()
    elif command == "stop":
        stop_server()
    elif command == "status":
        server_status()
    elif command == "save":
        session = sys.argv[2] if len(sys.argv) > 2 else None
        auto_save(session)
    elif command == "tools":
        print(MCP_TOOLS_SUMMARY)
    else:
        print(f"未知命令: {command}")
        print("可用: start, stop, status, save, tools")
