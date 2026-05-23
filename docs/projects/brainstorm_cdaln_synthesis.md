# Multi-Agent Brainstorming: CDALN × replay→skill_learn

> 方法: 3子Agent并行brainstorming + 汇总合成
> 日期: 2026-05-19

---

## Agent1 — 理论视角

Curiosity-Driven Autonomous Learning理论框架：CDALN的核心机制是好奇心信号=预测置信度与实际置信度的差距。Agent自主选择知识缺口最大的方向去探索。

## Agent2 — 工程视角

当前dream_engine.py的replay_memories()已检出低置信度缺口并触发Popen skill_learn。需要补优先级队列防止多个缺口同时触发。

## Agent3 — 集成视角

gap detected → extract domain → skill_learn → Dreaming verify → confidence up。闭环已通，只需落地优先级调度。

## 共同结论

```
Curiosity → Learn → Verify → Master
```
