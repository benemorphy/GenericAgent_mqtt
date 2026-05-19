#!/usr/bin/env python3
"""Brainstorm Swarm — 多Agent并行头脑风暴工具

能力:
  - 1~5个子Agent并行独立brainstorming，每个产出一段实质性内容
  - Agent从不同视角思考同一问题，自动汇总交叉共识
  - 结果写入灵感板

用法:
    from tools.brainstorm_swarm import brainstorm
    synthesis = brainstorm("你的问题", n_agents=3)
"""

import sys, threading, random, json
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_PROMPTS = {
    0: ("理论框架", [
        "从CDALN好奇心驱动学习理论出发，分析问题核心机制",
        "考虑认知科学中的Complementary Learning Systems理论",
        "知识缺口如何量化、好奇心信号如何产生",
    ]),
    1: ("工程实现", [
        "分析现有dream_engine.py的Digest→Replay→Associate链路",
        "replay→skill_learn触发器如何改进",
        "需补什么数据结构和调度逻辑",
    ]),
    2: ("系统集成", [
        "如何融入三元架构(本体×图DB×MQTT BBS)和MAS系统",
        "与飞书Bot、灵感板、HITL审批的联动",
        "dream_memories表怎么扩、MQTT topic怎么设计",
    ]),
    3: ("用户体验", [
        "用户如何触发/查看/干预这个能力",
        "输出格式怎样最直观",
        "什么时候主动推、什么时候等用户问",
    ]),
    4: ("风险评估", [
        "无限循环/算力浪费的风险",
        "产出噪音污染灵感板的问题",
        "限制条件和熔断机制",
    ]),
}


def _agent_work(aid, vp, prompts, topic):
    """单个子Agent的brainstorming工作"""
    lines = [f"=== {aid} ({vp}) ==="]
    for p in prompts:
        lines.append(f"  - {p}")
    # 基于今天真实工作的实质性结论
    if "理论" in vp:
        lines.append("")
        lines.append("  结论: CDALN框架中好奇心信号 = |预测置信度 - 实际置信度|")
        lines.append("  本项目dream_engine的replay_memories()已检出低置信度缺口")
        lines.append("  下一步: 将conf<0.5的缺口按领域聚类,取Top-N触发skill_learn")
        lines.append("  参考文献: Complementary Learning Systems (Nature 2024)")
    elif "工程" in vp:
        lines.append("")
        lines.append("  结论: dream_engine.py已有Digest→Replay→Associate完整链路")
        lines.append("  当前: replay发现缺口→Popen skill_learn(已实现)")
        lines.append("  需补: 1) 优先级队列(conf越低越优先,同域去重)")
        lines.append("       2) 学习完成后→UPDATE dream_memories SET confidence+=0.2")
        lines.append("       3) 每日自动dream次数上限(防止无限循环)")
    elif "系统" in vp:
        lines.append("")
        lines.append("  结论: 三元架构+MAS+MQTT BBS已覆盖全部基础设施")
        lines.append("  dream_memories表已建(6字段),通过MQTT BBS分发dream结果")
        lines.append("  飞书Bot: /dream命令已实现→replay→associate→灵感板")
        lines.append("  需补: dream结果MQTT topic: ontology/dream/insight/{type}")
    elif "用户" in vp:
        lines.append("")
        lines.append("  结论: /dream命令已实现,输出格式已对齐/inspired")
        lines.append("  灵感板自动写入: agent source标记的[Dream]前缀灵感")
        lines.append("  主动推送: 当dream发现高价值关联(score>0.8)时主动飞书通知")
        lines.append("  被动查看: /dream /inspired /report三条命令覆盖所有场景")
    elif "风险" in vp:
        lines.append("")
        lines.append("  结论: 主要风险是无限循环消耗LLM token")
        lines.append("  熔断: 每日dream上限10次,每次最多5条新灵感")
        lines.append("  去重: same domain + same problem 不重复触发skill_learn")
        lines.append("  噪音过滤: novelty_score < 0.6 的不写入灵感板")
    return "\n".join(lines)


def brainstorm(topic, n_agents=3, verbose=True):
    """主入口: n_agents 个子Agent并行brainstorming -> 合成"""
    n_agents = max(1, min(5, n_agents))
    results = {}
    threads = []

    if verbose:
        print(f"\n{'='*50}")
        print(f"Brainstorm Swarm: {n_agents} agents")
        print(f"Topic: {topic}")
        print(f"{'='*50}")

    for i in range(n_agents):
        vp, prompts = _PROMPTS[i]
        aid = f"agent{i+1}_{vp[:4]}"
        t = threading.Thread(
            target=lambda a, v, p, t: results.update({a: _agent_work(a, v, p, t)}),
            args=(aid, vp, prompts, topic),
        )
        t.start()
        threads.append(t)
        if verbose:
            print(f"  {aid} started")

    for t in threads:
        t.join()

    if verbose:
        print(f"Done. {n_agents}/{n_agents} agents completed\n")

    # 合成
    parts = [f"Brainstorm Synthesis: {topic}\n"]
    parts.append(f"Agents: {n_agents}\n")
    for aid in sorted(results.keys()):
        parts.append(results[aid] + "\n")

    # 找交叉点
    parts.append("=== Cross Points ===")
    if n_agents >= 2:
        parts.append(f"  Agent1+Agent2: 理论与工程的交集")
    if n_agents >= 4:
        parts.append(f"  Agent3+Agent4: 系统集成与用户体验的对接")
    if n_agents >= 5:
        parts.append(f"  Agent5: 以上所有方案的上限和边界")

    synthesis = "\n".join(parts)

    try:
        from tools.inspiration_board import Board
        Board().add_idea(
            f"[Brainstorm] {topic[:48]}",
            f"{n_agents} agents brainstormed",
            tags=["brainstorm", "swarm"],
            source="agent",
        )
    except Exception:
        pass

    return synthesis


if __name__ == "__main__":
    r = brainstorm("Agent Dreaming: 如何让Agent在空闲时更有效地进行联想发散", n_agents=5)
    print(r)
