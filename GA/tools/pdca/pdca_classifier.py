"""
PDCA 任务复杂度分级器 (Gliding Horse 设计理念提取)

借鉴 Gliding Horse 的 PDCA 7 级复杂度模型，对 Agent 接收到的任务自动分级，
并生成对应的执行策略 instruction 注入 prompt。

用法:
    from tools.pdca import classify_task, get_execution_strategy
    level = classify_task(task_desc, available_tools)
    instruction = get_execution_strategy(level).prompt_instruction
"""

import re

# ── 7 级复杂度定义 ──

TASK_LEVELS = {
    0: {
        "name": "L0_Instant",
        "desc": "即时任务，单轮无需规划",
        "patterns": [
            "当前时间", "简单查询", "单一工具调用",
            "几点了", "天气", "日期", "翻译",
        ],
        "prompt_instruction": (
            "[PDCA L0] 即时任务：直接执行，无需 Plan 步骤。\n"
            "  单次工具调用后即可返回结果，不需要复杂的拆解。"
        ),
        "max_turns": 3,
    },
    1: {
        "name": "L1_Simple",
        "desc": "简单任务，单次 PDCA",
        "patterns": [
            "读取文件", "简单搜索", "单步操作",
            "查看", "读取", "搜索", "列出",
        ],
        "prompt_instruction": (
            "[PDCA L1] 简单任务：先做简要计划，然后执行，最后确认结果。\n"
            "  Plan: 明确目标和工具\n"
            "  Do: 执行 1-2 步工具调用\n"
            "  Check: 确认结果是否符合预期"
        ),
        "max_turns": 5,
    },
    2: {
        "name": "L2_Standard",
        "desc": "标准任务，完整 PDCA + 审计",
        "patterns": [
            "分析数据", "多步代码", "文件修改",
            "修改", "分析", "重构", "编写", "实现",
        ],
        "prompt_instruction": (
            "[PDCA L2] 标准任务：Plan-Do-Check-Act 四阶段完整执行。\n"
            "  Plan: 用 update_working_checkpoint 记录 5W2H 目标和步骤\n"
            "  Do: 分步执行工具调用\n"
            "  Check: 自行验证结果正确性\n"
            "  Act: 必要时调整策略重新执行"
        ),
        "max_turns": 15,
    },
    3: {
        "name": "L3_Complex",
        "desc": "复杂项目，多步骤串行",
        "patterns": [
            "大型重构", "跨模块开发", "系统设计",
            "架构", "模块", "系统", "平台", "全量",
        ],
        "prompt_instruction": (
            "[PDCA L3] 复杂任务：拆分子任务，按优先级依次执行。\n"
            "  Plan: 拆分为多个 L0-L2 子任务，按依赖顺序排列\n"
            "  Do: 逐个子任务执行，每个子任务走 PDCA\n"
            "  Check: 每个子任务完成时验证结果\n"
            "  Act: 子任务失败时回滚或调整"
        ),
        "max_turns": 30,
    },
    4: {
        "name": "L4_Exploratory",
        "desc": "探索型任务，多方案对比",
        "patterns": [
            "技术调研", "方案对比", "研究方向",
            "调研", "对比", "评估", "可行性", "选型",
        ],
        "prompt_instruction": (
            "[PDCA L4] 探索任务：并行探索多方案后综合。\n"
            "  Plan: 列出 2-3 种可行方案及其评估标准\n"
            "  Do: 分别验证每个方案的可行性\n"
            "  Check: 按统一标准对比各方案优劣\n"
            "  Act: 给出推荐方案及理由"
        ),
        "max_turns": 25,
    },
    5: {
        "name": "L5_Recursive",
        "desc": "递归任务，子 PDCA 嵌套",
        "patterns": [
            "全面重构", "大型系统", "完整项目",
            "整体", "全面", "完全重写", "大规模",
            "全量重构", "级联", "多级嵌套", "递推",
            "递归拆解", "层层展开",
        ],
        "prompt_instruction": (
            "[PDCA L5] 递归任务：递归拆解为嵌套子 PDCA 循环。\n"
            "  Plan: 顶层规划，每个子模块是一个独立的 PDCA\n"
            "  Do: 逐层展开子任务，子任务可递归为更细粒度\n"
            "  Check: 逐层验证，下层失败影响上层决策\n"
            "  Act: 必要时终止整个递归链并上报"
        ),
        "max_turns": 50,
    },
    6: {
        "name": "L6_Emergency",
        "desc": "紧急模式，跳过 Plan 直接 Do",
        "patterns": [
            "修 Bug", "线上故障", "紧急恢复",
            "紧急", "立即", "马上", "修复", "bug",
            "线上", "生产故障", "宕机", "崩溃",
            "安全漏洞", "数据丢失", "紧急修复",
        ],
        "prompt_instruction": (
            "[PDCA L6] 紧急模式：跳过 Plan 阶段，直接 Do-Check-Act 循环。\n"
            "  第一步直接执行修复操作，事后补充复盘。\n"
            "  Check 阶段缩短确认周期，边做边验证。"
        ),
        "max_turns": 10,
    },
}


def classify_task(task_description: str) -> int:
    """基于任务描述自动判定复杂度级别 (0-6)。

    匹配策略：
    1. 先匹配 pattern 关键词（精确匹配优先）
    2. 后匹配模糊语义（上下文长度、结构特征）

    Args:
        task_description: 用户输入的任务描述

    Returns:
        int: 0-6 的复杂度级别
    """
    if not task_description:
        return 0

    desc_lower = task_description.lower()

    # 策略1: pattern 关键词匹配（从高到低反向匹配，高优先级先命中）
    for level in sorted(TASK_LEVELS.keys(), reverse=True):
        for pattern in TASK_LEVELS[level]["patterns"]:
            if pattern.lower() in desc_lower:
                return level

    # 策略2: 基于任务描述的长度和结构特征
    word_count = len(desc_lower.split())

    if word_count < 5:
        return 0  # 极短 = 即时
    elif word_count < 15:
        return 1  # 短 = 简单
    elif word_count < 30:
        return 2  # 中等 = 标准

    # 超过 30 词 + 有结构特征 = 复杂
    has_structure = any(
        kw in desc_lower for kw in ["第一步", "第二步", "首先", "然后", "最后", "分别", "依次"]
    )
    if has_structure and word_count > 40:
        return 3

    return 2  # 默认标准


def get_execution_strategy(level: int) -> dict:
    """获取指定级别的完整执行策略。

    Args:
        level: 0-6 的复杂度级别

    Returns:
        dict: 包含 name, desc, prompt_instruction, max_turns 的配置字典
    """
    return TASK_LEVELS.get(level, TASK_LEVELS[2])


def get_prompt_instruction(level: int) -> str:
    """获取指定级别的 prompt instruction 文本，用于注入 Agent prompt。"""
    return get_execution_strategy(level)["prompt_instruction"]


def format_level_badge(level: int) -> str:
    """格式化显示级别标签。"""
    info = TASK_LEVELS.get(level, TASK_LEVELS[2])
    return f"[PDCA {info['name']}] {info['desc']}"


# from tools.utils.retry_utils import retry_stream
# from tools.utils.logger import log


def _classify_fallback(task_description: str) -> int:
    """带 LLM 二次确认的分级（预留钩子，后续可选）。

    初次规则匹配后，可调用 LLM 做语义确认。
    当前版本直接返回规则匹配结果。
    """
    level = classify_task(task_description)
    # TODO: 可选 LLM 二次确认，当 level >= 2 或置信度 < 0.7 时
    return level


def classify_task_from_history(history_info: list) -> int:
    """从 Agent history_info 列表中提取最近用户任务并分类。

    遍历 history_info（反向），找到第一个 [USER] 条目作为任务描述。
    适用于 get_anchor_prompt 和 sph_pdca_instruction 中获取上下文。

    Args:
        history_info: handler.history_info 列表

    Returns:
        int: 0-6 的复杂度级别
    """
    if not history_info:
        return 0
    for entry in reversed(history_info):
        if entry.startswith('[USER]'):
            return classify_task(entry.replace('[USER] ', '', 1))
    return 2  # 默认标准


def get_pdca_summary(task_description: str) -> dict:
    """一站式获取 PDCA 分级结果的所有信息。

    Args:
        task_description: 任务描述文本

    Returns:
        dict: 包含 level, name, desc, badge, instruction, max_turns
    """
    level = classify_task(task_description)
    info = TASK_LEVELS.get(level, TASK_LEVELS[2])
    return {
        "level": level,
        "name": info["name"],
        "desc": info["desc"],
        "badge": format_level_badge(level),
        "instruction": info["prompt_instruction"],
        "max_turns": info.get("max_turns", 15),
    }


# ── 5W2H 任务本体辅助 (Gliding Horse) ──

FIVE_W2H_KEYS = ["what", "why", "who", "when", "where", "how", "how_much"]
FIVE_W2H_LABELS = {
    "what": "任务内容 (What)",
    "why": "动机/原因 (Why)",
    "who": "执行者 (Who)",
    "when": "截止时间 (When)",
    "where": "工作路径 (Where)",
    "how": "方法/步骤 (How)",
    "how_much": "工作量预估 (How Much)",
}


def extract_5w2h_prompt(task_description: str) -> str:
    """生成让 LLM 提取 5W2H 的 prompt 指令。

    当 Agent 接收到标准或复杂任务时，可调用此函数生成指令，
    引导 LLM 填写 update_working_checkpoint 的 five_w2h 参数。

    Args:
        task_description: 原始任务描述

    Returns:
        str: 引导 LLM 提取 5W2H 的 prompt 文本
    """
    return (
        f"[P0/5W2H] 请将当前任务拆解为 5W2H 结构，"
        f"通过 update_working_checkpoint(five_w2h=...) 提交。\n"
        f"  原始任务: {task_description[:100]}\n"
        f"  5W2H 字段:\n"
        f"    what: 任务具体内容是什么\n"
        f"    why: 为什么做这个任务\n"
        f"    who: 谁执行\n"
        f"    when: 时间限制或截止点\n"
        f"    where: 涉及的文件或目录\n"
        f"    how: 执行方法或步骤\n"
        f"    how_much: 预估工作量\n"
        f"  格式: 调用 update_working_checkpoint 时传入 JSON 字符串"
    )


def format_5w2h(five_w2h) -> str:
    """格式化 5W2H 为可读文本。

    支持 dict 和 str 两种输入格式。

    Args:
        five_w2h: dict (7个字段) 或 str

    Returns:
        str: 格式化后的 5W2H 文本
    """
    if not five_w2h:
        return ""
    if isinstance(five_w2h, dict):
        parts = []
        for key in FIVE_W2H_KEYS:
            val = five_w2h.get(key)
            if val:
                parts.append(f"  {FIVE_W2H_LABELS.get(key, key)}: {val}")
        return "\n".join(parts) if parts else str(five_w2h)
    return str(five_w2h)


def validate_5w2h(five_w2h) -> tuple:
    """验证 5W2H 结构完整性。

    Args:
        five_w2h: dict 或 str

    Returns:
        (is_valid, missing_keys)
    """
    if not isinstance(five_w2h, dict):
        return False, FIVE_W2H_KEYS
    missing = [k for k in FIVE_W2H_KEYS if k not in five_w2h or not five_w2h.get(k)]
    return len(missing) <= 2, missing


def classify_task_from_history(history_info: list) -> int:
    """从历史记录 history_info 中提取最新用户任务并分级。

    prompt_utils.py 和 hooks_default.py 都调用此函数作为入口。
    history_info 格式: ['[USER] 请修改 ga.py', '[Agent] ...', ...]

    Args:
        history_info: GenericAgentHandler.history_info 列表

    Returns:
        int: 0-6 的复杂度级别
    """
    if not history_info:
        return 2  # 无历史记录时默认 L2 标准

    # 从 history 中提取最后一条用户消息
    user_tasks = [h for h in history_info if h.startswith('[USER]')]
    if not user_tasks:
        return 0

    latest = user_tasks[-1]
    # 去掉 '[USER] ' 前缀后分类
    task_desc = latest.replace('[USER]', '', 1).strip()
    return classify_task(task_desc)


if __name__ == "__main__":
    # 测试
    test_cases = [
        "几点了",
        "读取 ga.py 文件的前 50 行",
        "重构 user_auth.py 的 JWT 验证逻辑，增加 Token 刷新机制",
        "调研目前主流的 RAG 方案，对比 LangChain、LlamaIndex 和向量数据库的选型建议",
        "对整个项目做全量重构，把 Python 2 代码迁移到 Python 3",
        "线上用户认证失败，立即修复！",
        "分析最近一周的日志，找出导致性能下降的根本原因",
    ]
    for case in test_cases:
        level = classify_task(case)
        badge = format_level_badge(level)
        print(f"  L{level} | {badge}")
        print(f"       {case[:60]}")
        print()

    print("--- 5W2H 测试 ---")
    test_5w2h = {"what": "重构认证", "why": "安全漏洞", "who": "Agent",
                  "when": "本对话", "where": "ga/user_auth.py",
                  "how": "重写JWT", "how_much": "50-80行"}
    print(format_5w2h(test_5w2h))
    valid, missing = validate_5w2h(test_5w2h)
    print(f"  5W2H valid={valid}, missing={missing}")
    print(extract_5w2h_prompt("请重构用户认证模块")[:80])
