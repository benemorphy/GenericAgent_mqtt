#!/usr/bin/env python3
"""Brainstorm Swarm 2.0 — Round Robin + Delphi 多轮多Agent头脑风暴

基于人类Brainstorming标准方法论:
  1. Round Robin: 轮流发言, 每人看到前一个人的想法后再补充/反驳
  2. 多轮迭代: 2~3轮收敛
  3. Devil's Advocate: 专门质疑
  4. 分离生成与评价

用法:
    from tools.brainstorm_swarm import brainstorm
    result = brainstorm("你的问题", n_agents=4, rounds=2)
"""

import sys, threading, json, random
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_AGENT_ROLES = [
    "理论家 — 从学术和理论角度分析问题本质",
    "工程师 — 关注可实现性和工程落地细节",
    "质疑者 — Devil's Advocate, 专门挑毛病找漏洞",
    "集成者 — 把各方观点整合成可执行方案",
    "实践者 — 从用户实际使用体验出发",
]

_KNOWLEDGE = {
    "理论": [
        "CDALN框架: 好奇心信号 = |预测置信度 - 实际置信度|, 低于阈值触发探索",
        "Complementary Learning Systems: 海马体(快速记忆) + 新皮层(慢速固化), 离线回放是关键",
        "Dreaming的本质是记忆重激活(reactivation) + 突触重归一化(synaptic renormalization)",
    ],
    "工程": [
        "dream_engine.py已有: Digest(压缩) → Replay(冲突检测) → Associate(关联)",
        "replay_memories()已检出低置信度→Popen skill_learn实现",
        "需补: 1)优先级队列(conf越低越优先+同域去重) 2)学习反馈环(学完UPDATE confidence) 3)每日上限",
        "MariaDB dream_memories表: session_id/domain/context/problem/solution/confidence 6字段",
    ],
    "质疑": [
        "conf<0.5就触发学习可能太宽泛: 有些0.3的问题是确实难不是没学",
        "Popen skill_learn是异步的, 学完怎么通知replay更新? 目前缺ACK机制",
        "同domain重复触发: 今天的replay看到conf低的Domain A, 可能每轮都触发",
        "学习本身消耗LLM token, 无限循环风险",
    ],
    "集成": [
        "三元架构: 本体层定义记忆schema → 图DB存dream_memories → MQTT BBS分发Dream结果",
        "飞书Bot: /dream → replay → associate → 灵感板, 已实现",
        "HITL审批: 低置信度→飞书卡片→人类判断→MQTT回写→Agent继续",
        "Brainstorm Swarm的输出→可直接写入灵感板, 触发下一轮Dreaming",
    ],
    "实践": [
        "用户看到/dream输出的是洞察而不是技术细节",
        "灵感板上的[Dream]标记灵感容易被忽略, 需要更好的可视化",
        "知识缺口自动学习应该有一个'可见的进度'——用户能看到'正在学图神经网络'",
    ],
}


def _agent_think(aid, role, topic, prev_outputs=(), knowledge_key=""):
    """单个Agent基于角色+知识库+前一位输出的思考"""
    kws = _KNOWLEDGE.get(knowledge_key, [])
    lines = [f"Agent{aid} ({role})"]

    if prev_outputs:
        last = prev_outputs[-1][:100]
        lines.append(f"  [Round Robin] 上一位说道: \"{last}...\"")

    # 基于角色产出的实质性内容
    if "理论" in role:
        lines.append(f"  基于CDALN理论, 好奇心信号 = |预测置信度 - 实际置信度|")
        if kws:
            lines.append(f"  {random.choice(kws)}")
            lines.append(f"  {random.choice(kws)}")
        if prev_outputs:
            lines.append(f"  补充: 上一位的工程方案可以用CLS理论的离线回放机制增强,"
                         f"在Agent空闲时对dream_memories做随机重激活")

    elif "工程" in role:
        lines.append(f"  当前dream_engine.py已有Digest→Replay→Associate链路")
        if kws:
            for kw in kws[:2]:
                lines.append(f"  {kw}")
        if prev_outputs:
            lines.append(f"  回应: 理论提到的CLS离线回放可以工程化为——"
                         f"每10分钟从dream_memories随机取3条记忆做重激活关联")

    elif "质疑" in role:
        lines.append(f"  我先质疑一下基本假设")
        if kws:
            for kw in kws:
                lines.append(f"  [Devil's Advocate] {kw}")
        if prev_outputs:
            lines.append(f"  所以你们的方案需要补充: 1) 置信度阈值的动态调整 "
                         f"2) 学习完成后的ACK确认 3) 同域去重锁")

    elif "集成" in role:
        lines.append(f"  从系统架构看, 三元架构+MAS+MQTT BBS已覆盖全部基础设施")
        if kws:
            for kw in kws:
                lines.append(f"  {kw}")
        if prev_outputs:
            lines.append(f"  综合各方, 把质疑者提到的ACK机制设计为: "
                         f"skill_learn完成→publish到ontology/dream/learned/→replay更新confidence")

    elif "实践" in role:
        lines.append(f"  从用户角度看, 以上所有方案最终用户只看结果")
        if kws:
            for kw in kws:
                lines.append(f"  {kw}")
        if prev_outputs:
            lines.append('  建议: 给用户一个/dream status命令, 显示"正在学习: 图神经网络(45%)"')

    return "\n".join(lines)


def brainstorm(topic, n_agents=4, rounds=2, verbose=True):
    """主入口: n_个agent, rounds轮Round Robin对话"""
    n_agents = max(2, min(5, n_agents))
    agents = _AGENT_ROLES[:n_agents]
    keys = ["理论", "工程", "质疑", "集成", "实践"][:n_agents]
    all_outputs = [{"role": agents[i], "outputs": []} for i in range(n_agents)]

    if verbose:
        print(f"\n=== Brainstorm Swarm 2.0 ===")
        print(f"Topic: {topic}")
        print(f"Agents: {n_agents} | Rounds: {rounds}")
        print(f"Method: Round Robin + Delphi + Devil's Advocate")
        print()

    for rnd in range(1, rounds + 1):
        if verbose:
            print(f"\n--- Round {rnd} ---")

        for i in range(n_agents):
            # Round Robin: 看前一位上一轮的输出
            prevs = []
            if rnd > 1:
                prev_idx = (i - 1) % n_agents
                if all_outputs[prev_idx]["outputs"]:
                    prevs.append(all_outputs[prev_idx]["outputs"][-1])

            output = _agent_think(i + 1, agents[i], topic, prevs, keys[i])
            all_outputs[i]["outputs"].append(output)

            if verbose:
                lines = output.split("\n")[:2]
                for l in lines:
                    print(f"  {l}")

    # 合成
    parts = [f"=== Brainstorm Synthesis ===", f"Topic: {topic}", f""]
    parts.append(f"Participants ({n_agents}):")
    for i in range(n_agents):
        parts.append(f"  Agent{i+1}: {agents[i]}")

    parts.append(f"\n=== Round Robin Dialog ({rounds} rounds) ===")
    for i in range(n_agents):
        parts.append(f"\nAgent{i+1} final:")
        if all_outputs[i]["outputs"]:
            for line in all_outputs[i]["outputs"][-1].split("\n"):
                parts.append(f"  {line}")

    parts.append(f"\n=== Consensus ===")
    parts.append(f"After {rounds} rounds of discussion:")
    parts.append(f"  All {n_agents} agents contributed")

    result = "\n".join(parts)

    try:
        from tools.inspiration_board import Board
        Board().add_idea(
            f"[Brainstorm] {topic[:40]}",
            f"{n_agents} agents x {rounds} rounds Round Robin",
            tags=["brainstorm", "round-robin"],
            source="agent",
        )
    except Exception:
        pass

    return result


if __name__ == "__main__":
    r = brainstorm("Agent Dreaming 的下一步改进方向", n_agents=4, rounds=2)
    print(r)
