"""
CuriosityTrigger — Agent 好奇心自动检测触发器

在 Agent 每轮执行结束时检查工具结果和上下文，若有触发条件则发帖到 CuriosityBoard。
通过 CURIOSITY_ENABLED 环境变量控制开关（默认开启）。

用法:
    from tools.curiosity_trigger import check_curiosity_triggers
    triggers = check_curiosity_triggers(tool_results, "agent_alpha")
    for t in triggers:
        ctx.publish("board/curiosity/post", t)
"""

import time
import os
import hashlib

_CURIOSITY_ENABLED = os.environ.get("CURIOSITY_ENABLED", "true").lower() == "true"
_RANDOM_RATE = 0.05
_PATTERN_WINDOW = 5
_pattern_memory: list[dict] = []


def _make_trigger(trigger_type: str, description: str, agent_id: str) -> dict:
    """Create a trigger dict for curiosity board."""
    return {
        "type": trigger_type,
        "description": description,
        "agent_id": agent_id,
        "timestamp": time.time(),
        "trigger_id": hashlib.md5(
            f"{agent_id}{trigger_type}{description}{time.time()}".encode()
        ).hexdigest()[:12],
    }


def check_curiosity_triggers(tool_results: list[dict], agent_id: str) -> list[dict]:
    """Check if any curiosity triggers are activated."""
    triggers: list[dict] = []
    
    if not _CURIOSITY_ENABLED:
        return triggers
    
    n = len(tool_results)
    if n < 2:
        return triggers
    
    # Check for cross-tool patterns (lines that were originally in the function body)
    for i in range(n - 1):
        for j in range(i + 1, n):
            # Check for tool result connections
            triggers.append(_make_trigger("connection",
                f"并发工具 [{tool_results[i].get('tool', '?')}] 和 [{tool_results[j].get('tool', '?')}] 的结果之间存在潜在关联",
                agent_id))
    
    # 5. Random curiosity (5%/hour)
    h = int(hashlib.md5((agent_id + str(int(time.time() / 3600))).encode()).hexdigest(), 16)
    if h % 100 < _RANDOM_RATE * 100:
        triggers.append(_make_trigger("discovery",
            "随机好奇: 当前工具链或流程是否有优化空间？", agent_id))
    
    return triggers
