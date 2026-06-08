"""
MemPalace Bridge — MemPalace 语义搜索与知识图谱集成桥接模块

为 GeneralAgent 记忆系统提供 MemPalace 的只读增强层。
File-Based 记忆为 Source of Truth，MemPalace 为语义搜索增强层。

Usage:
    from memory.mempalace_bridge import semantic_search
    results = semantic_search("MQTT BoardService")
"""

import os
import re
import json
import subprocess
import sys
from typing import Optional

# ── 项目 Python 路径 ──
_MEMORY_DIR = os.path.dirname(os.path.abspath(__file__))
_GA_DIR = os.path.dirname(_MEMORY_DIR)
_PROJECT_DIR = os.path.dirname(_GA_DIR)
_VENV_PYTHON = os.path.join(_PROJECT_DIR, ".venv", "Scripts", "python.exe")
if not os.path.isfile(_VENV_PYTHON):
    _VENV_PYTHON = sys.executable  # fallback

# ── Palace 路径配置 ──
_MEMORY_DIR = os.path.dirname(os.path.abspath(__file__))
_PALACE_DATA_DIR = os.path.join(_MEMORY_DIR, ".mempalace", "palace")


def _ensure_palace_path() -> str:
    """确保 MEMPALACE_PALACE_PATH 环境变量已设置，返回 palace 数据路径。"""
    if not os.path.isdir(_PALACE_DATA_DIR):
        raise FileNotFoundError(
            f"MemPalace 数据目录不存在: {_PALACE_DATA_DIR}\n"
            f"请先运行: mempalace init --yes {_MEMORY_DIR} && mempalace mine {_MEMORY_DIR}"
        )
    os.environ.setdefault("MEMPALACE_PALACE_PATH", _PALACE_DATA_DIR)
    return _PALACE_DATA_DIR


# ── 搜索 ──

def semantic_search(
    query: str,
    wing: Optional[str] = None,
    room: Optional[str] = None,
    n_results: int = 5,
) -> list[dict]:
    """
    语义搜索 MemPalace 记忆库。使用 subprocess 调用 CLI 获取可靠输出。

    Returns:
        结果列表，每项包含:
            - source: 源文件名
            - room: 所属 room
            - wing: 所属 wing
            - content: 匹配上下文片段
            - cosine: 余弦相似度分数
    """
    palace_path = _ensure_palace_path()

    env = os.environ.copy()
    env["MEMPALACE_PALACE_PATH"] = palace_path

    cmd = [_VENV_PYTHON, "-m", "mempalace", "search"]
    if wing:
        cmd += ["--wing", wing]
    if room:
        cmd += ["--room", room]
    cmd += ["--results", str(n_results), query]

    try:
        result = subprocess.run(
            cmd, capture_output=True, text=True, timeout=60, env=env
        )
        output = result.stdout
    except subprocess.TimeoutExpired:
        return []

    return _parse_search_output(output)


def _parse_search_output(output: str) -> list[dict]:
    """解析 mempalace search 的终端输出为结构化数据。"""
    results = []
    lines = output.strip().split("\n")

    current = None  # 只有内容行出现后才创建 result
    in_result = False
    content_lines = []

    for line in lines:
        stripped = line.strip()

        # 结果标题行: [1] memory / general
        m_result = re.match(r"^\s*\[(\d+)\]\s+(.+?)\s*/\s*(.+?)\s*$", line)
        if m_result:
            # 保存上一个结果
            if current and current.get("source"):
                current["content"] = "\n".join(content_lines).strip()
                results.append(current)

            current = {
                "wing": m_result.group(2).strip(),
                "room": m_result.group(3).strip(),
                "source": "",
                "cosine": 0.0,
                "bm25": 0.0,
                "content": "",
            }
            content_lines = []
            in_result = True
            continue

        if not in_result:
            continue

        # Source 行: "      Source: filename.md"
        if stripped.startswith("Source:"):
            current["source"] = stripped.replace("Source:", "").strip()
            continue

        # 分数行: "      Match:  cosine=0.575  bm25=2.533"
        m_score = re.search(r"cosine=([\d.]+)", stripped)
        if m_score:
            current["cosine"] = float(m_score.group(1))
        m_bm25 = re.search(r"bm25=([\d.]+)", stripped)
        if m_bm25:
            current["bm25"] = float(m_bm25.group(1))

        # 分隔线 ────────────────────────
        if re.match(r"^[\s]*[─━]+", line) and len(line.strip()) > 10:
            if current and current.get("source"):
                current["content"] = "\n".join(content_lines).strip()
                results.append(current)
            current = {
                "wing": current["wing"] if current else "",
                "room": current["room"] if current else "",
                "source": "",
                "cosine": 0.0,
                "bm25": 0.0,
                "content": "",
            }
            content_lines = []
            continue

        # 内容行 — 跳过空行和头部装饰
        if stripped and not stripped.startswith("=") and not stripped.startswith("Results for"):
            content_lines.append(stripped)

    # 最后一个结果
    if current and current.get("source"):
        current["content"] = "\n".join(content_lines).strip()
        results.append(current)

    return results


def search_json(
    query: str,
    wing: Optional[str] = None,
    room: Optional[str] = None,
    n_results: int = 5,
) -> str:
    """语义搜索并以 JSON 格式返回结果。"""
    results = semantic_search(query, wing, room, n_results)
    return json.dumps(results, ensure_ascii=False, indent=2)


# ── 简便接口 ──

def quick_search(query: str) -> str:
    """快速搜索，返回格式化文本（供 CLI/Agent 直接使用）。"""
    try:
        results = semantic_search(query, n_results=3)
        if not results:
            return f"[MemPalace] 未找到与 '{query}' 相关的结果"

        lines = [f"[MemPalace] 语义搜索结果: '{query}'", ""]
        for i, r in enumerate(results, 1):
            source = r.get("source") or "?"
            room_label = r.get("room") or "?"
            cosine = r.get("cosine", 0)
            content = (r.get("content") or "")[:200]
            lines.append(f"  [{i}] {source} ({room_label}, cosine={cosine:.3f})")
            if content:
                lines.append(f"      {content}")
            lines.append("")
        return "\n".join(lines)
    except Exception as e:
        return f"[MemPalace] 搜索失败: {e}"


# ── 状态检查 ──

def palace_status() -> dict:
    """检查 MemPalace palace 状态。"""
    status = {
        "available": False,
        "drawers": 0,
        "rooms": [],
        "error": None,
    }
    try:
        palace_path = _ensure_palace_path()
        env = os.environ.copy()
        env["MEMPALACE_PALACE_PATH"] = palace_path

        result = subprocess.run(
            [_VENV_PYTHON, "-m", "mempalace", "status"],
            capture_output=True, text=True, timeout=30, env=env,
        )
        output = result.stdout or ""

        # 解析抽屉数
        m = re.search(r"(\d+)\s+drawers", output)
        if m:
            status["drawers"] = int(m.group(1))

        # 解析房间
        rooms = re.findall(r"ROOM:\s+(\S+)\s+(\d+)\s+drawers", output)
        status["rooms"] = [
            {"name": r[0], "drawers": int(r[1])} for r in rooms
        ]
        status["available"] = len(status["rooms"]) > 0
    except Exception as e:
        status["error"] = str(e)

    return status


# ── CLI 入口 ──

if __name__ == "__main__":
    # 处理 GBK 编码问题
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")

    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
        print(quick_search(query))
    else:
        print("=== MemPalace Bridge 状态 ===")
        s = palace_status()
        print(f"可用: {s['available']}")
        print(f"抽屉: {s['drawers']}")
        print(f"房间: {[r['name'] for r in s['rooms']]}")
        if s.get("error"):
            print(f"错误: {s['error']}")
        print("\n使用: python mempalace_bridge.py <查询文本>")
