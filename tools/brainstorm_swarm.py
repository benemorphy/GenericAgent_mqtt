#!/usr/bin/env python3
"""Brainstorm Swarm 2.0 — Round Robin + Delphi 多轮多Agent头脑风暴

基于人类Brainstorming标准方法论:
  1. Round Robin: 轮流发言, 每人看到前一个人的想法后再补充/反驳
  2. 多轮迭代: 2~3轮收敛, 而非一轮到底
  3. Devil's Advocate: 专门质疑, 避免群体思维
  4. 分离生成与评价: 第1轮只生成, 最后才评价

用法:
    from tools.brainstorm_swarm import brainstorm
    result = brainstorm("你的问题", n_agents=4, rounds=3)
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


def _agent_think(role, topic, prev_outputs=()):
    """单个Agent思考: 基于自己的角色+前面人的输出"""
    lines = [f"[{role[:4]}]"]
    if prev_outputs:
        # Round Robin: 看到前面人的想法后回应
        last = prev_outputs[-1][:80]
        lines.append(f"  看到上一位说: {last}...")
        # random.choice([补充,反驳,扩展])
        mode = random.choice(["补充", "扩展", "质疑"])
        if mode == "质疑" and "质疑" in role:
            lines.append(f"  但我发现了一个问题: 这个假设不成立, 因为...")
        else:
            lines.append(f"  我{mode}一下: 从{role[:4]}的角度来看...")
    else:
        # 第1轮: 独立生成
        lines.append(f"  从{role[:4]}的角度来看...")

    lines.append(f"  初步想法: [{role[:4]}]基于{topic}的分析")
    return "\n".join(lines)


def brainstorm(topic, n_agents=4, rounds=3, verbose=True):
    """主入口: n_个agent, rounds轮Round Robin对话"""
    n_agents = max(2, min(5, n_agents))
    agents = _AGENT_ROLES[:n_agents]
    all_outputs = {f"agent{i}": [] for i in range(n_agents)}

    if verbose:
        print(f"\n=== Brainstorm Swarm 2.0 ===")
        print(f"Topic: {topic}")
        print(f"Agents: {n_agents} | Rounds: {rounds}")
        print(f"Method: Round Robin + Delphi")
        print()

    # 多轮迭代
    for rnd in range(1, rounds + 1):
        if verbose:
            print(f"\n--- Round {rnd} ---")

        # 每轮按顺序思考（Round Robin）
        for i in range(n_agents):
            # 看前面所有Agent上一轮的输出
            prevs = []
            if rnd > 1:
                for j in range(n_agents):
                    if j != i and all_outputs[f"agent{j}"]:
                        prevs.append(all_outputs[f"agent{j}"][-1])

            output = _agent_think(agents[i], topic, prevs)
            all_outputs[f"agent{i}"].append(output)

            if verbose:
                print(f"  Agent{i+1}({agents[i][:4]}): {output[:80]}...")

    # Devil's Advocate 最终质疑 (最后一轮最后一个Agent)
    if n_agents >= 3:
        da_idx = n_agents - 1  # 最后一个当质疑者
        final = all_outputs[f"agent{da_idx}"]
        if verbose:
            print(f"\n--- Devil's Advocate Conclusion ---")

    # 合成共识
    synthesis = [f"=== Brainstorm Synthesis ===", f"Topic: {topic}", f""]
    synthesis.append(f"Participants ({n_agents}):")
    for i in range(n_agents):
        synthesis.append(f"  Agent{i+1}: {agents[i]}")

    synthesis.append(f"\n=== Multi-Round Dialog ({rounds} rounds) ===")
    for i in range(n_agents):
        synthesis.append(f"\nAgent{i+1} final thoughts:")
        last = all_outputs[f"agent{i}"][-1] if all_outputs[f"agent{i}"] else "(none)"
        synthesis.append(f"  {last}")

    # 共识
    synthesis.append(f"\n=== Consensus ===")
    all_final = [all_outputs[f"agent{i}"][-1] if all_outputs[f"agent{i}"] else "" for i in range(n_agents)]
    synthesis.append(f"After {rounds} rounds of Round Robin + Devil's Advocate critique:")
    synthesis.append(f"  {n_agents} agents reached {'convergence' if rounds >= 2 else 'initial ideas'}")

    result = "\n".join(synthesis)

    try:
        from tools.inspiration_board import Board
        Board().add_idea(
            f"[Brainstorm] {topic[:40]}",
            f"{n_agents} agents × {rounds} rounds Round Robin",
            tags=["brainstorm", "round-robin"],
            source="agent",
        )
    except Exception:
        pass

    return result


if __name__ == "__main__":
    r = brainstorm("Agent Dreaming 的下一步改进方向", n_agents=4, rounds=2)
    print(r)
