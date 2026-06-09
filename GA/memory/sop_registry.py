"""
SOP 注册表 — 自动化 SOP 发现与关键词匹配

用法:
    from memory.sop_registry import match_sop, list_unregistered

    # 关键词匹配
    results = match_sop("压测10w消息看看BoardService性能")
    for score, name in results:
        print(f"  [{score}] {name}")

    # 检查未注册的 SOP
    unreg = list_unregistered()
    if unreg:
        print(f"未注册: {unreg}")
"""

import os
from pathlib import Path

# ── SOP 目录路径 ──
_MEMORY_DIR = Path(__file__).parent

# ══════════════════════════════════════
# SOP 注册表
# ══════════════════════════════════════
# 格式: 名称 -> {"keywords": [...], "path": "...", "category": "..."}
# keywords 是匹配关键词列表，匹配越多分数越高
# 新增 SOP 时在此添加一行即可自动注册

SOP_REGISTRY: dict[str, dict] = {
    # ── 开发运维 ──
    "git_push": {
        "keywords": ["推送", "push", "git", "PR", "合并", "squash", "merge"],
        "path": "git_push_sop.md",
        "category": "devops",
    },
    "push_cleanup": {
        "keywords": ["推送", "清理", "分支", "branch", "cleanup"],
        "path": "push_cleanup_sop.md",
        "category": "devops",
    },
    "github_contribution": {
        "keywords": ["贡献", "contribution", "github", "commit"],
        "path": "github_contribution_sop.md",
        "category": "devops",
    },

    # ── MQTT / BBS ──
    "board_stress": {
        "keywords": ["压测", "stress", "benchmark", "性能", "压力测试", "MQTT"],
        "path": "board_stress_sop.md",
        "category": "testing",
    },
    "emqtt_design": {
        "keywords": ["emqtt", "erlang", "mqtt", "设计原则", "设计模式"],
        "path": "emqtt_design_principles.md",
        "category": "architecture",
    },
    "sqlite_to_mariadb": {
        "keywords": ["迁移", "migrate", "sqlite", "mariadb", "数据库", "DB"],
        "path": "sqlite_to_mariadb_sop.md",
        "category": "data",
    },

    # ── Agent 核心 ──
    "goal_mode": {
        "keywords": ["目标", "goal", "预算", "自驱", "持续", "开放目标"],
        "path": "goal_mode_sop.md",
        "category": "agent",
    },
    "autonomous_operation": {
        "keywords": ["自主", "空闲", "autonomous", "idle", "TODO", "空闲行动"],
        "path": "autonomous_operation_sop.md",
        "category": "agent",
    },
    "agent_dreaming": {
        "keywords": ["做梦", "dreaming", "dream", "联想", "发散", "创意", "灵感"],
        "path": "agent_dreaming_sop.md",
        "category": "agent",
    },
    "failure_driven_learning": {
        "keywords": ["失败", "错误", "学习", "复盘", "lesson", "learned"],
        "path": "failure_driven_learning_sop.md",
        "category": "agent",
    },
    "spaced_repetition": {
        "keywords": ["复习", "间隔", "重复", "巩固", "spaced", "repetition"],
        "path": "spaced_repetition_sop.md",
        "category": "agent",
    },
    "shutdown": {
        "keywords": ["关机", "下班", "shutdown", "结束", "退出"],
        "path": "shutdown_rule.md",
        "category": "agent",
    },

    # ── 计划与执行 ──
    "plan": {
        "keywords": ["计划", "规划", "plan", "多步", "协同", "依赖"],
        "path": "plan_sop.md",
        "category": "execution",
    },
    "subagent": {
        "keywords": ["子代理", "subagent", "委托", "delegate", "后台"],
        "path": "subagent.md",
        "category": "execution",
    },
    "supervisor": {
        "keywords": ["监察", "监督", "supervisor", "监控", "watchdog"],
        "path": "supervisor_sop.md",
        "category": "execution",
    },
    "scheduled_task": {
        "keywords": ["定时", "调度", "cron", "schedule", "周期"],
        "path": "scheduled_task_sop.md",
        "category": "execution",
    },

    # ── 前端 / UI ──
    "vue3_component": {
        "keywords": ["vue", "组件", "component", "前端", "UI", "JS"],
        "path": "vue3_component_sop.md",
        "category": "frontend",
    },
    "tmwebdriver": {
        "keywords": ["浏览器", "web", "selenium", "TMWebDriver", "自动化"],
        "path": "tmwebdriver_sop.md",
        "category": "frontend",
    },
    "web_setup": {
        "keywords": ["web", "初始化", "工具链", "playwright", "setup"],
        "path": "web_setup_sop.md",
        "category": "frontend",
    },
    "web_testing": {
        "keywords": ["测试", "web", "playwright", "e2e", "浏览器"],
        "path": "web_testing_sop.md",
        "category": "testing",
    },
    "aesthetic_design": {
        "keywords": ["审美", "设计", "UI", "样式", "css", "颜色", "布局"],
        "path": "aesthetic_design_sop.md",
        "category": "frontend",
    },

    # ── 视觉 / OCR ──
    "vision": {
        "keywords": ["视觉", "vision", "截图", "截图", "图像", "识别"],
        "path": "vision_sop.md",
        "category": "vision",
    },
    "clipboard_ocr": {
        "keywords": ["ocr", "剪贴板", "识别", "文字提取", "截图"],
        "path": "clipboard_ocr_sop.md",
        "category": "vision",
    },
    "ljqctrl": {
        "keywords": ["键鼠", "鼠标", "键盘", "坐标", "click", "移动"],
        "path": "ljqCtrl_sop.md",
        "category": "vision",
    },
    "procmem_scanner": {
        "keywords": ["内存", "进程", "scan", "memory", "procmem"],
        "path": "procmem_scanner_sop.md",
        "category": "debug",
    },

    # ── 通信 ──
    "feishu_connect": {
        "keywords": ["飞书", "feishu", "lark", "机器人", "bot", "通知"],
        "path": "feishu_connect_sop.md",
        "category": "communication",
    },
    "qq_deploy": {
        "keywords": ["qq", "机器人", "部署", "napcat", "onebot"],
        "path": "qq_deploy_sop.md",
        "category": "communication",
    },

    # ── 记忆 / 学习 ──
    "skills_learning": {
        "keywords": ["技能", "学习", "案例", "skill", "learn", "CLI"],
        "path": "skills_learning_sop.md",
        "category": "learning",
    },
    "memory_cleanup": {
        "keywords": ["记忆", "归档", "整理", "压缩", "cleanup", "archive"],
        "path": "memory_cleanup_sop.md",
        "category": "learning",
    },
    "memory_management": {
        "keywords": ["记忆管理", "SOP", "meta", "元记忆"],
        "path": "memory_management_sop.md",
        "category": "learning",
    },
    "code_review": {
        "keywords": ["代码审查", "code review", "质量", "重构"],
        "path": "code_review_principles.md",
        "category": "quality",
    },
    "verify": {
        "keywords": ["验证", "verify", "校验", "检查"],
        "path": "verify_sop.md",
        "category": "quality",
    },
    "search_skills": {
        "keywords": ["搜索", "search", "查找", "谷歌", "web"],
        "path": "search_skills_sop.md",
        "category": "research",
    },
    "dream_command": {
        "keywords": ["梦境", "dream", "命令", "命令映射", "指令"],
        "path": "dream_command_rule.md",
        "category": "agent",
    },
    "morphling": {
        "keywords": ["吞噬", "吸收", "外部项目", "morphling", "能力迁移", "对标", "复刻"],
        "path": "morphling_sop.md",
        "category": "methodology",
    },
    "gbrain_integration": {
        "keywords": ["gbrain", "知识库", "大脑", "知识检索", "brain", "知识图谱", "推理"],
        "path": "gbrain_integration_sop.md",
        "category": "integration",
    },
}


# ── 功能函数 ──

def match_sop(query: str, top_k: int = 3) -> list[tuple[int, str, dict]]:
    """
    查询 → 按匹配分数排序的 SOP 列表。

    Args:
        query: 自然语言查询，如 "压测10w消息"
        top_k: 返回 top-k 结果

    Returns:
        [(score, name, entry), ...]  按分数降序
    """
    results = []
    for name, entry in SOP_REGISTRY.items():
        score = sum(1 for kw in entry["keywords"] if kw in query.lower())
        if score > 0:
            results.append((score, name, entry))
    results.sort(key=lambda x: x[0], reverse=True)
    return results[:top_k]


def list_unregistered() -> list[str]:
    """
    扫描 memory/ 目录，返回未注册的 SOP 文件名列表。
    用于提醒：新增 SOP 后忘记注册到 SOP_REGISTRY 的情况。
    """
    registered = {entry["path"] for entry in SOP_REGISTRY.values()}
    unregistered = []
    for f in sorted(os.listdir(_MEMORY_DIR)):
        if not f.endswith('_sop.md') and f not in ('subagent.md', 'shutdown_rule.md',
            'dream_command_rule.md', 'emqtt_design_principles.md', 'code_review_principles.md',
            'verify_sop.md', 'global_mem.txt', 'global_mem_insight.txt'):
            continue
        if f not in registered:
            unregistered.append(f)
    return unregistered


def get_all_categories() -> dict[str, list[str]]:
    """按分类组织 SOP 列表"""
    cats: dict[str, list[str]] = {}
    for name, entry in SOP_REGISTRY.items():
        cat = entry["category"]
        if cat not in cats:
            cats[cat] = []
        cats[cat].append(name)
    return cats


if __name__ == "__main__":
    print(f"SOP 注册表: {len(SOP_REGISTRY)} 条, {len(get_all_categories())} 类\n")

    unreg = list_unregistered()
    if unreg:
        print(f"⚠ 未注册 SOP: {unreg}")
    else:
        print("✓ 所有 SOP 已注册\n")

    # 测试匹配
    tests = [
        "压测10w消息看看BoardService性能",
        "git推送，创建PR，自动合并",
        "我对这个任务没什么思路，先发散一下",
        "定时每3小时检查一次",
        "截图这个窗口然后OCR识别",
    ]
    for q in tests:
        results = match_sop(q)
        print(f"  \"{q}\"")
        for score, name, entry in results:
            print(f"    [{score}] {name} ({entry['category']})")
        print()
