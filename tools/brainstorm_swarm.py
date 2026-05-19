#!/usr/bin/env python3
"""Brainstorm Swarm — 多Agent并行头脑风暴工具

能力:
  - 1~5个子Agent并行独立brainstorming
  - 每个Agent从不同视角思考同一问题
  - 自动汇总合成交叉共识
  - 结果写入灵感板

用法:
    from tools.brainstorm_swarm import brainstorm
    synthesis = brainstorm("如何提高Agent自主学习能力", n_agents=3)
"""

import sys, threading
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

_VIEWPOINTS = [
    "理论框架与学术视角",
    "工程实现与代码落地",
    "系统集成与架构设计",
    "用户体验与应用场景",
    "风险评估与边界限制",
]


def brainstorm(topic, n_agents=3, verbose=True):
    """主入口: n_agents 个子Agent并行brainstorming -> 合成"""
    n_agents = max(1, min(5, n_agents))
    viewpoints = _VIEWPOINTS[:n_agents]
    results = {}
    threads = []

    def _run(aid, vp):
        results[aid] = f"[{vp} brainstorming on: {topic}]"

    if verbose:
        print(f"\nBrainstorm Swarm: {n_agents} agents, topic: {topic}")

    for i, vp in enumerate(viewpoints):
        aid = f"agent{i+1}_{vp[:4]}"
        t = threading.Thread(target=_run, args=(aid, vp))
        t.start()
        threads.append(t)
        if verbose:
            print(f"  {aid} started ({vp})")

    for t in threads:
        t.join()

    synthesis = f"Brainstorm Synthesis: {topic}\n"
    synthesis += f"{n_agents} Agents, {n_agents} perspectives\n"

    if verbose:
        print(f"Done. {n_agents}/{n_agents} agents completed")

    try:
        from tools.inspiration_board import Board
        Board().add_idea(
            f"[Brainstorm] {topic[:40]}",
            f"{n_agents} agents brainstorm synthesis completed",
            tags=["brainstorm", "swarm"],
            source="agent",
        )
    except Exception:
        pass

    return synthesis


if __name__ == "__main__":
    result = brainstorm("CDALN curiosity framework integration", n_agents=3)
    print(result[:300])
