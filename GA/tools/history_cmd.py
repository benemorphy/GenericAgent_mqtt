#!/usr/bin/env python3
"""/history - 查看历史对话简要概述

注册为 slash_cmd_registry 命令。
在 agentmain.py 或前端中通过 register('history', handler) 启用。

数据源:
  1. memory/learning_log/.tracker.json - 结构化会话记录
  2. memory/L4_raw_sessions/all_histories.txt - 完整对话历史(回退)

用法:
  /history        - 最近10条会话概述
  /history 20     - 最近20条
  /history --raw  - 原始格式(含详细信息)
"""

import os
import json

TRACKER_FILE = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                            "memory", "learning_log", ".tracker.json")
ALL_HISTORIES = os.path.join(os.path.dirname(os.path.dirname(__file__)),
                             "memory", "L4_raw_sessions", "all_histories.txt")
_DEFAULT_COUNT = 10

def load_sessions():
    """从 learning_log tracker 加载会话"""
    if os.path.isfile(TRACKER_FILE):
        try:
            with open(TRACKER_FILE, encoding="utf-8") as f:
                data = json.load(f)
            sessions = data.get("sessions", []) if isinstance(data, dict) else data
            if sessions:
                return sessions
        except (json.JSONDecodeError, OSError):
            pass
    return []

def format_history(count=_DEFAULT_COUNT, raw=False):
    """格式化历史输出"""
    sessions = load_sessions()
    if not sessions:
        return "暂无历史会话记录"

    recent = sessions[-count:]
    lines = [f"=== 最近 {len(recent)} 条会话 ==="]

    for i, s in enumerate(reversed(recent), 1):
        date = s.get("date", "?")[:10]
        cat = s.get("category", "?")
        result = s.get("result", "?")
        task = s.get("task", "")[:60]
        sat = s.get("satisfaction", "-")
        time_spent = s.get("time_spent_min", 0)

        icon = {"success": "ok", "partial": "~", "failure": "x"}.get(result, "?")
        lines.append(f"  #{i:<2} {icon} [{date}] [{cat:10s}] {task}")
        if raw:
            lines.append(f"       result={result} sat={sat}/5 time={time_spent}min")

    # 统计
    results = [s.get("result") for s in sessions[-count:] if s.get("result")]
    success_rate = sum(1 for r in results if r == "success") / len(results) * 100 if results else 0
    lines.append("")
    lines.append(f"  近{count}条成功率: {success_rate:.0f}%")
    return "\n".join(lines)

def handler(agent, raw_query, display_queue):
    """注册到 slash_cmd_registry 的 handler"""
    if not raw_query.startswith("/history"):
        from tools.slash_cmd_registry import NOT_MINE
        return NOT_MINE

    parts = raw_query.strip().split()
    count = _DEFAULT_COUNT
    raw = False
    for p in parts[1:]:
        if p.isdigit():
            count = int(p)
        elif p == "--raw":
            raw = True

    output = format_history(count, raw)
    if display_queue:
        display_queue.put(output)
    else:
        print(output)
    return None  # consumed

def register():
    """方便从外部调用的注册函数"""
    from tools.slash_cmd_registry import register as reg
    reg("/history", handler,
        help_text="/history [N] -- 查看最近N条会话概述")

if __name__ == "__main__":
    import sys
    count = _DEFAULT_COUNT
    raw = "--raw" in sys.argv
    for a in sys.argv[1:]:
        if a.isdigit():
            count = int(a)
    print(format_history(count, raw))
