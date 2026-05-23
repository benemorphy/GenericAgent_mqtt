# Deep Research: Agent 自主探索与自主学习最新进展 (2025-2026)

> WEB节点: Google (arXiv/ResearchGate/Frontiers/ACM/YouTube/o-mega/Tencent)
> 价值: 与本项目的Agent Dreaming + Deep Research + skill_learn 直接相关

---

## 1. 三个核心方向

| 方向 | 本质 | 2025-2026进展 |
|:-----|:------|:-------------|
| **好奇心驱动探索** | 主动发现未知，非被动等指令 | CDALN框架(Curiosity-Driven Autonomous Learning Networks) |
| **经验驱动终身学习** | 持续累积记忆→自我进化 | ELL框架(Experience-Driven Lifelong Learning) |
| **子Agent自主调度** | 动态生成子任务并行探索 | Kimi 2.5 / Claude Code / AutoGPT |

## 2. Curiosity-Driven Autonomous Learning Networks (CDALN)

```
Agent内部状态: 当前技能树 + 知识缺口图
    ↓ 好奇心信号: 预测误差最大的方向 = 最值得探索
Agent主动选择: "这个领域我不懂，去学一下"
    ↓ 自我设定课程: 从易到难，自动编排学习路径
Agent执行: 搜索→阅读→实践→压缩→合并到技能树
```

关键论文: **International Conference on AI Research 2025**

## 3. Experience-Driven Lifelong Learning (ELL)

| 能力 | 说明 | 本项目对应 |
|:-----|:------|:----------|
| 持久记忆 | 经验累积不丢失 | dream_memories表 |
| 经验回放 | 旧经验中发现新模式 | replay_memories() |
| 自我评估 | 对比预期vs实际 → 缺口 | 冲突检测 |
| 技能树更新 | 新知识合并到已有体系 | skills_learning + SOP |

论文: arXiv Jan 2026 "Building Self-Evolving Agents via Experience-Driven"

## 4. 子Agent自主调度

| 方式 | 代表 | 做法 |
|:-----|:------|:------|
| 单Agent拆分 | Claude Code | spawn子进程处理子任务 |
| 多Agent协同 | Kimi 2.5 | 并行子Agent共享上下文 |
| 动态生成 | AutoGPT | 运行时生成新Agent类型 |

## 5. 与GenericAgent的映射

| 自主探索能力 | 已有 | 缺口 |
|:------------|:----|:-----|
| 好奇心驱动 | Deep Research(用户触发) | ❌ 无主动好奇心信号 |
| 终身学习 | skills_learning + Dream Engine | ⚠️ 手动触发，非自动 |
| 技能树构建 | 32个技能已入库 | ✅ |
| 自我评估缺口 | replay冲突检测 | ⚠️ 只检出但没触发自动学习 |
| 子Agent调度 | MAS + WorkerAgent | ✅ |

## 6. 关键差距

**最大的差距不是技术，是"主动"二字**。

当前GenericAgent的所有学习行为都是被动的：
- skill_learn：用户说学才学
- Deep Research：用户说研究才研究
- Agent Dreaming：用户说/dream才dream

而CDALN的核心是**Agent自己觉得"这里我不懂，去学一下"**——
把好奇心信号（knowledge gap detection）从replay输出端接到skill_learn输入端，形成闭环。

---

> 参考文献: CDALN 2025 / ELL arXiv Jan 2026 / Kimi 2.5 / Claude Code / o-mega AI 2026 Guide