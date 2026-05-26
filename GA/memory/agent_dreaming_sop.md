# Agent Dreaming SOP — 基于历史对话的联想发散与创意孵化

> 触发：已完成一天工作/积累大量历史对话，空闲时激活
> 产出：新灵感/跨域关联/创造性方案/Simulation & Imagination
> 核心理念：Agent在空闲时对历史对话进行"做梦"式的再处理，类似人类睡眠中记忆整合+联想发散

---

## 核心流程 (DREAM 循环)

```
┌─────────────────────────────────────────────────────────┐
│                     Agent Dreaming                        │
│                                                          │
│  Digest → Replay → Expand → Associate → Morph            │
│  消化     回放     扩展     关联      变形               │
│                                                          │
│  Digest:  压缩当天对话为结构化记忆块                      │
│  Replay:  随机抽取记忆块重放，标记冲突/缺口               │
│  Expand:  对缺口展开Deep Research                         │
│  Associate: 跨域连接（如：环形子图→深海电磁发射结构）      │
│  Morph:   变形为新灵感 → 写入灵感板                       │
└─────────────────────────────────────────────────────────┘
```

## Phase 1: Digest (消化)

*将当天历史对话压缩为结构化记忆块*

```python
def digest_conversation(history):
    """压缩一天对话为记忆块"""
    memories = []
    for turn in history:
        # 关键模式: 问题→方案→决策
        if turn.has_key_decision:
            memories.append({
                "context": turn.summary,      # 50字内
                "problem": turn.problem,       # 核心问题
                "solution": turn.solution,     # 采用的方案
                "rejected": turn.rejected,     # 否决的方案
                "artifacts": turn.files,       # 产生的文件
                "confidence": turn.score       # 0-1
            })
    save_memories(memories)
```

## Phase 2: Replay (回放)

*随机抽取记忆块重放，标记冲突/缺口*

```python
def replay(memories):
    insights = []
    for pair in random_pairs(memories, k=3):
        # 找冲突: 类似的problem用了不同solution
        if pair[0].problem == pair[1].problem and \
           pair[0].solution != pair[1].solution:
            insights.append({
                "type": "conflict",
                "desc": f"{pair[0].solution} vs {pair[1].solution}",
                "recommend": "需要统一策略"
            })
        # 找缺口: problem没有完整solution
        if pair[0].confidence < 0.5:
            insights.append({
                "type": "gap",
                "desc": f"{pair[0].problem} 置信度低",
                "recommend": "启动Deep Research"
            })
    return insights
```

## Phase 3: Expand (扩展)

*对标记的缺口展开Deep Research (按DeepResearch SOP)*

```python
def expand_gaps(insights):
    for gap in insights:
        if gap["type"] == "gap":
            # 启动子Agent进行Deep Research
            sub_agent_research(gap["desc"])
    # 结果回写记忆库
```

## Phase 4: Associate (关联)

*跨域连接——Agent Dreaming的核心*

```python
def associate(memories):
    """跨域联想：将不同领域的记忆块组合"""
    combinations = []
    # 随机组合两个不相关的领域
    for a, b in itertools.combinations(memories, 2):
        if a.domain != b.domain:
            combo = {
                "domain_a": a.domain,
                "domain_b": b.domain,
                "bridge": find_common_abstraction(a, b),
                "novelty_score": score_novelty(a, b)
            }
            combinations.append(combo)
    
    # 今天实战案例: 环形子图(风控) + 深海电磁发射(机械)
    # → 共同抽象: "闭环检测" → 环形资金流 ↔ 环形管道结构
    # → 新灵感: 用图数据库环形检测算法优化管道布局
```

**跨域联想示例（基于今天工作）**:

```
领域A: 环形子图风控 (图数据库)
领域B: 深海电磁发射(管道结构)
↓
共同抽象: "闭环检测"
↓
新灵感: 用风控环形检测算法优化深海管道应力分布
```

## Phase 5: Morph (变形)

*将联想结果变形为可执行灵感*

```python
def morph(association):
    """将跨域联想变形为可执行的灵感/方案"""
    if association.novelty_score > 0.7:
        # 写入灵感板
        inspiration_board.add(
            title=f"{association.domain_a} × {association.domain_b}",
            detail=f"共同抽象: {association.bridge}",
            tags=[association.domain_a, association.domain_b, "dream"]
        )
        # 可选: 构造原型方案
        return draft_prototype(association)
```

## 触发时机

| 时机 | 触发条件 | 深度 |
|:-----|:---------|:----:|
| 空闲复盘 | 连续10分钟无用户指令 | Digest + Replay |
| Deep Research 后 | 刚完成一轮Deep Research | Expand |
| 灵感板为空 | 所有灵感已implemented | Associate + Morph |
| 隔夜重启 | 每次启动后 | 全流程 |

## 与记忆系统的关系

```
Agent Dreaming
  ↓ Digest
记忆块 (short-term)
  ↓ Replay (筛选+压缩)
记忆模式 (long-term, 写入 global_mem)
  ↓ Associate
灵感板 (inspiration_board)
  ↓ Morph
新技能/skills_learning
```

## 避坑指南

- **禁止循环**: Dreaming产出要写入固定topic，防止同一段历史被反复dream
- **质量阈值**: novelty_score < 0.5 的不写入灵感板，避免噪音
- **不占用用户时间**: Dreaming在空闲后台做，不打断用户
- **不改变已确认的决策**: Dreaming只能提议，不能覆写历史决策

---

> **文档版本**: v1.0 | 创建: 2026-05-19
> **技能库**: `skills_learning/agentDreaming/rev1` (9模式, 100分)
> **来源**: DeepResearch SOP + 多智能体协同梦境 + 经验回放与提炼
