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

import time, os, json, hashlib

_CURIOSITY_ENABLED = os.environ.get("CURIOSITY_ENABLED", "true").lower() == "true"
_RANDOM_RATE = 0.05
_PATTERN_WINDOW = 5
_pattern_memory: list[dict] = []
_last_err
...[Truncated]...
        triggers.append(_make_trigger("connection",
            f"并发工具 [{results[i]['tool']}] 和 [{results[j]['tool']}] 的结果之间存在潜在关联",
            agent_id))

    # 5. 随机好奇心（5%/小时）
    h = int(hashlib.md5((agent_id + str(int(time.time() / 3600))).encode()).hexdigest(), 16)
    if h % 100 < _RANDOM_RATE * 100:
        triggers.append(_make_trigger("discovery",
            f"随机好奇: 当前工具链或流程是否有优化空间？", agent_id))

    return triggers
