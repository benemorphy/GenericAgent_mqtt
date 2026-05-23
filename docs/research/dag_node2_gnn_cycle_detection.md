# Deep Research DAG 序贯执行 — 节点2: GNN异常环检测

> 轮次: 第1轮 | 节点类型: WEB
> 来源: Google Search (NVIDIA / IEEE / arXiv / ScienceDirect / ResearchGate)

---

## 核心发现

**GNN是环形资金流检测的最优技术：多跳关系分析 + 时序追踪 + 可解释性**

## 1. GNN vs 传统方法

| 维度 | 规则引擎 | NetworkX | GNN |
|:-----|:---------|:---------|:----|
| 环检测 | 固定规则 | 精准枚举 | 学习+检测 |
| 未知模式 | ❌ | ❌ | ✅ GNN学习 |
| 时序 | ❌ | ❌ | ✅ 时间衰减 |
| 可解释 | ✅ | ✅ | ✅ XAI模块 |

## 2. 关键架构 (2024-2025)

| 架构 | 优势 | 论文/来源 |
|:-----|:-----|:----------|
| **Heterogeneous GNN** | 多关系类型(正常vs关联方) | ScienceDirect 2026 |
| **FraudGNN-RL** | GNN+强化学习自适应 | IEEE 2025 (82引用) |
| **时间注意力** | 动态时序图 | PMC 2026 |
| **Graph Transformer** | 替代GAT的消息传递 | NVIDIA/arXiv 2024 |

## 3. 环形子图检测流程

```
原始交易图 → GNN编码 → 邻域聚合 → 节点异常评分
     ↓              ↓            ↓
时序边特征    多跳消息传递    子图提取
     ↓              ↓            ↓
if_hidden_net → 环检测评分 → XAI可视化
```

## 4. 与现有项目集成

| 现有 | GNN增强 |
|:-----|:--------|
| Oxigraph环形查询 | GNN预筛选可疑节点 → SPARQL精确查环 |
| NetworkX BFS | GNN评分Top-K节点 → 定向BFS |
| if_hidden_net标记 | GNN自动发现新隐藏节点 → 标记 |

---

> 节点状态: ✅ 完成 | 参考: safe-github/graph-fraud-detection-papers