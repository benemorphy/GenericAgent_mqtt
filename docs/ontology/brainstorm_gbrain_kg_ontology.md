# 多Agent脑暴：gbrain知识图谱与本体模型

> 执行方式：按照 brainstorming_sop（发散-收敛式头脑风暴）
> 日期：2026-06-09

---

## Phase 1: 问题定义

**核心问题**：如何将 gbrain 的知识检索/图谱能力与 GA 现有的本体模型（ontology_model + ontology_codegraph_bridge + 经脉论研究）深度融合，形成一套"可推理的活体知识系统"？

**约束条件**：
- gbrain 是 bun/TypeScript CLI，通过 subprocess 调用
- GA 本体模型是 Python，通过 rdflib/OWL 表达
- 已有 CodeGraph 桥接层（代码图→本体映射）
- 已有跨学科本体论研究（经脉论、过程本体论、时变图）
- 需要保持可维护性，不要过度工程化

**成功标准**：
- 能回答"代码变更会影响哪些领域概念"这种跨层问题
- 能融合 gbrain 的检索结果与 GA 的推理能力
- 可增量演化，不一次性大重构

---

## Phase 2: 发散 — 5个 Agent 视角

### Agent A: 架构集成师 (Architecture)
> 关注点：如何把两个系统拼在一起而不断裂

**想法 A1 — MCP 双向桥接**
在 gbrain MCP 层（gbrain_mcp.py）新增 `gbrain_ontology_query` 函数，在 gbrain 的 `graph-query` 之上叠加 OWL 推理：当 gbrain 返回知识图谱节点时，自动用 rdflib 推理展开其父子类/属性继承关系。GA Agent 收到的不再是扁平节点列表，而是"带推理路径的语义树"。

**想法 A2 — 本体注入（Ontology Injection）**
将 GA 的 OWL 本体（TBox）序列化为 JSON-LD，作为 gbrain 的一个特殊 source（如 `source=ontology`），通过 `gbrain put` 写入 gbrain 知识库。这样 gbrain 的 query/search 能直接检索到本体概念，Agent 的 gbrain 查询结果天然带有语义层。不需要改 gbrain 代码。

**想法 A3 — 反省管道（Reflection Pipeline）**
在 GA 的 ontology_model.py 中新增一个反省函数：Agent 每次调用 gbrain 后，结果经过一个 OWL 推理管线（类似现有的 `diagnose_system`），自动将 gbrain 返回的扁平结果转化为带推理的三元组。这样不改 gbrain 任何代码，纯 GA 侧增强。

**想法 A4 — 双向同步 gbrain ↔ OWL**
建立一个 cron 级别的双向同步：gbrain 的 pages 变化 → 更新 OWL ABox；OWL 推理出的新关系 → 写回 gbrain 作为派生 page。让两者互为投影。但这需要解决冲突检测和循环更新问题。

---

### Agent B: 知识图谱工程师 (Knowledge Graph)
> 关注点：图数据模型、遍历性能、查询表达力

**想法 B1 — gbrain 的 graph-query 增强**
当前 `gbrain graph-query` 只做 2 层 BFS 遍历。可以扩展为：支持 Cypher-like 模式匹配（如 `(page)-[:references]->(concept)-[:subclass_of]->(thing)`）。但这需要改 gbrain 源码。更务实的做法：在 GA 侧实现一个"模式匹配引擎"，对 gbrain 返回的扁平图在内存中做二次匹配。

**想法 B2 — 时变知识图谱（TKG）层**
借鉴 `ontology_model_evolution.md` 中的第二代动态知识图谱思路，给 gbrain 的节点打时间戳（`created_at` / `valid_until`），让 graph-query 支持时间窗口过滤："2026年5月之前的哪些概念已被废弃？" 这可以用 gbrain 已有的 `source` 机制做：不同时间片的数据放在不同 source 中，按 source 查即可。

**想法 B3 — 多速率演化图谱**
借鉴经脉论的"三层次速率"（万年不变的结构层 / 日季节可调的功能层 / 分钟级的状态层），在 gbrain 中建立三层 source：`source=structure`（缓慢变化的实体定义）、`source=function`（中速变化的实例数据）、`source=state`（快速变化的运行状态）。查询时可指定速率层 `--rate-layers structure,function` 来过滤。

**想法 B4 — 图谱嵌入 + 语义搜索**
gbrain 已经有 embedding-based search。可以在 gbrain 的 graph-query 结果上进行 embedding 重排序：用 gbrain 已有的检索结果 + ontology 概念之间的 embedding 相似度，做混合排序（hybrid search）。这不需要改 gbrain，只需要在 GA 侧对查询结果做后处理。

---

### Agent C: 本体论学者 (Ontologist)
> 关注点：形式化语义、推理完备性、跨本体映射

**想法 C1 — 经脉本体 × gbrain 的双向映射**
现有 `meridian_ontology.md` 已经建立了经脉论到本体的映射规则。可以将这套映射注册为 gbrain 的一个 skillpack 或推理包：当查询涉及"某某病机"时，自动唤醒经脉推理管线，在 gbrain 的检索结果上叠加"经络辨证"的推理路径。输出结果不再是扁平节点，而是"带经络推理链的语义树"。

**想法 C2 — OWL 推理器作为 gbrain 的 reranker**
gbrain 的 search 返回 TOP-K 结果后，经过 OWL 推理器做二次过滤：对每个候选结果，用 OWL 推理检查其与查询概念之间的语义距离（通过 subclass/property chains 计算推理距离）。语义距离近的排在前面。实现方式：在 `gbrain_mcp.py` 的 `gbrain_search` 函数中增加一个 `ontology_rerank=True` 参数。

**想法 C3 — 概念版本演化本体**
借鉴 `ontology_model_evolution.md` 中的"本体进化"理念，在 gbrain 中建立概念的版本历史。当 GA Agent 发现一个 ontology 概念需要更新时，不直接修改，而是创建一个新版本——旧概念标记为 `deprecated`，新概念继承旧概念的大部分属性。gbrain 的 `graph-query` 返回时，按时间戳返回当前有效版本。

> 这是本体演化的核心难题在 gbrain 中的实践：时间和演化成为本体的构成性维度，而非背景属性。

**想法 C4 — 跨本体对齐网关**
gbrain 的 source 机制天然支持多源。可以创建"对齐 layer"——一个特殊的 source 专门存跨本体的等价关系（equivalentClass, sameAs）。当查询跨越两个 source（如 `source=code_ontology` 和 `source=meridian_ontology`）时，对齐 layer 自动建立桥梁。这正是 ontology_model_evolution 中的"跨领域本体对齐"技术方向。

---

### Agent D: 实践派工程师 (Practitioner)
> 关注点：MVP、不破坏现有系统、快速验证

**想法 D1 — 最小可行：Ontology Reranker**
基于 A3（Reflection Pipeline）的最简实现：在 `gbrain_skill.py` 的 `gbrain_query_agent` 函数中，对 gbrain 返回的结果做一层 ontology 后处理。从结果中提取实体名 → 在 `ontology_model.py` 的静态 ENTITIES 中查找 → 附加语义标签。实现成本：约 50 行 Python，不改任何现有代码。

**想法 D2 — 本体作为 gbrain source（Ontology as a Source）**
基于 A2（本体注入）：写一个脚本 `sync_ontology_to_gbrain.py`，将 `ontology_model.py` 中定义的 ENTITIES/RELATIONS 序列化为 markdown pages，通过 `gbrain put` 写入 gbrain 的 `source=ga_ontology`。之后 Agent 直接用 `gbrain search` 就能查到本体概念。成本：约 80 行 Python。

**想法 D3 — 图查询 + 本体推理的二阶段管道**
将 gbrain 的 `graph-query` 输出作为 OWL 推理器的 ABox 输入。具体流程：
1. Agent 调用 `gbrain.graph_query(slug)` → 获得 {nodes, edges}
2. GA 侧将 nodes/edges 转换为 OWL individuals/properties
3. OWL 推理器（rdflib）运行推理 + 展开 transitive properties
4. 返回推理增强后的图谱

实现方式：在 `gbrain_mcp.py` 中新增 `gbrain_graph_query_with_reasoning()` 函数，组合上述步骤。约 100 行 Python。

**想法 D4 — 先做 search 增强，再考虑 graph**
实际上 80% 的 Agent 查询走的是 `gbrain_query`（搜索），而非 `graph-query`（图遍历）。所以优先做搜索增强：在 `gbrain_search` 返回后，用 ontology 的 know entity names 做实体链接（entity linking），标记出结果中的已知概念。这给 Agent 的后续推理提供了语义锚点。约 60 行 Python。

---

### Agent E: 远见者 (Visionary)
> 关注点：3-5年后的图景、范式突破

**想法 E1 — 从"检索知识"到"演化知识"**
当前的 gbrain + ontology 是"检索"范式——知识已经存在，我们去查。真正的跃迁是"演化"范式：Agent 使用 gbrain 的过程本身就是对 ontology 的验证和修正。当 Agent 反复查询某个概念但找不到好结果时，ontology 应该自动建议分裂或合并概念。这是 ontology_model_evolution.md 中"第三代向量本体"的自然延伸。

**想法 E2 — 本体即 Agent 的认知脚手架**
gbrain 不只是一个知识库，它可以是 Agent 的"认知脚手架"——当 Agent 面对陌生领域时，ontology 提供概念骨架，gbrain 提供实例填充，两者结合让 Agent 能像人类一样"先建立概念框架，再填充细节"。这对应 gbrain 的 `think` 功能 + ontology 的 TBox 推理。

**想法 E3 — 神经网络-符号主义混合推理**
在 gbrain 的 embedding search（神经网络）和 ontology 的 OWL 推理（符号主义）之间建立双向反馈环：
- 神经网络端：gbrain 搜索找到语义相似的概念
- 符号端：OWL 推理检查这些概念之间的逻辑一致性
- 不一致时触发"好奇心"——Agent 主动探索并补充知识

这正是 ontology_model_evolution 中"第三代"神经符号融合的实践版本。

**想法 E4 — 多 Agent 共享本体拓扑**
在 Hive 多 Worker 模式下（`goal_hive_sop`），每个 Worker 有自己独立的 gbrain session，但共享一个 ontology backbone。当 Worker A 发现了新的概念关系，通过 MQTT 广播给 ontology 层，ontology 层校验后传播给其他 Worker。这使 gbrain 从一个"单人大脑"进化为"群体认知系统"。

---

## Phase 3: 收敛 — 按标准筛选

### 评估维度

| 想法 | 可行性 | 影响力 | 风险 | 新颖度 | 总分 |
|------|--------|--------|------|--------|------|
| **D1: Ontology Reranker** | 5/5 | 3/5 | 1/5 | 2/5 | 11 |
| **D2: Ontology as Source** | 5/5 | 4/5 | 1/5 | 3/5 | 13 |
| **D3: 二阶段图+推理** | 4/5 | 4/5 | 2/5 | 3/5 | 13 |
| **D4: Search优先增强** | 5/5 | 4/5 | 1/5 | 2/5 | 12 |
| **B2: TKG时间层** | 3/5 | 3/5 | 2/5 | 4/5 | 12 |
| **B3: 多速率演化图谱** | 3/5 | 4/5 | 2/5 | 5/5 | 14 |
| **A2: 本体注入** | 5/5 | 4/5 | 1/5 | 3/5 | 13 |
| **C2: OWL作为reranker** | 4/5 | 3/5 | 2/5 | 4/5 | 13 |
| **C4: 跨本体对齐** | 3/5 | 5/5 | 2/5 | 5/5 | 15 |
| **E4: 多Agent本体共享** | 2/5 | 5/5 | 3/5 | 5/5 | 15 |
| **A4: 双向同步** | 2/5 | 4/5 | 4/5 | 4/5 | 14 |
| **E1: 知识演化** | 1/5 | 5/5 | 3/5 | 5/5 | 14 |

### 聚类分组

**第一梯队（立即实施，≤1天）**：
- D2/A2: 本体注入 gbrain source — 最好上手、影响力高
- D1/D4: 搜索增强 + ontology reranker — 最小改动、立即见效
- D3: 二阶段图+推理管道 — 中等成本，知识图谱侧的杀手功能

**第二梯队（短期，1-2周）**：
- B3: 多速率演化图谱（三层source）— 新颖度高、经脉论实践
- C2: OWL推理器作为reranker — 结合第一梯队
- B2: TKG时间窗口 — 自然的演化步骤

**第三梯队（中长期，1月+）**：
- C4: 跨本体对齐网关 — 打通经脉论+代码本体的桥梁
- E4: 多Agent本体共享 — Hive集成
- E1: 知识演化 — 范式跃迁

---

## Phase 4: 形成建议

### 建议一（MVP）：Ontology as Source + Search Reranker

**描述**：双管齐下——将 ontology 注入 gbrain 成为可检索的 source + 对 gbrain 搜索结果做 ontology 增强后处理

**可行性**：5/5 — 纯 GA 侧代码，不改 gbrain
**风险**：极低 — 不触及任何现有功能
**影响力**：高 — 从此 Agent 的每次 gbrain 查询都能感知本体概念
**实施计划**：
1. 写 `tools/skills/ontology_to_gbrain_sync.py` — 将 ENTITIES 序列化为 markdown，`gbrain put` 写入
2. 在 `gbrain_skill.py` 的 `gbrain_search_agent` 中增加 ontology reranker 逻辑
3. 在 `gbrain_mcp.py` 中新增 `gbrain_search_with_ontology()` 组合函数

**预期产出**：Agent 说"查一下 MQTT 相关的组件"，gbrain 返回的不仅是文本匹配，还有 `(MQTT Broker) --depends_on--> (BoardService)` 这样的结构化推理路径。

---

### 建议二（中程）：多速率演化图谱

**描述**：将 gbrain 的 source 机制映射为三层次速率模型（结构层/功能层/状态层），让查询支持按"演化速率"过滤

**可行性**：3/5 — 需要设计 source 命名约定 + 查询路由
**风险**：低 — gbrain 的 source 已是成熟特性
**影响力**：高 — 直接实践 ontology_model_evolution 的核心理论
**实施计划**：
1. 设计三层 source 命名规范（如 `ga_structure`, `ga_function`, `ga_state`）
2. 修改 `gbrain_search` 和 `gbrain_graph_query` 支持 `--rate-layer` 参数
3. 在 `ontology_model.py` 中新增速率层归属标注

---

### 建议三（远景）：跨本体对齐网关 + 多Agent共享

**描述**：建立 GA 内部多本体（代码本体、经脉本体、供应链本体）之间的对齐层，并通过 MQTT 在 Hive Worker 间共享本体演化信息

**可行性**：2/5 — 需要显著的架构设计
**风险**：中 — 多 Agent 竞争写入需要冲突解决
**影响力**：5/5 — 真正实现"群体认知"
**实施计划**：
1. 在 gbrain 中创建 `source=ontology_alignment` 专门存等价关系
2. 在 `goal_hive_sop` 中增加 ontology 同步管道
3. 在 gbrain 的 think 功能之上建立"本体演化提案"机制

---

### 执行优先级总结

```
立即（今天）
├── D2 + A2: Ontology as Source ─────────────────→ 预期0.5天
├── D1 + D4: Search Reranker ───────────────────→ 预期0.5天
└── D3: 二阶段图+推理 ────────────────────────→ 预期1天

短期（本周）
├── B3: 多速率演化图谱 ──────────────────────→ 预期3天
├── C2: OWL推理器作为reranker ──────────────→ 预期2天
└── B2: TKG时间窗口 ────────────────────────→ 预期2天

中长期（本月）
├── C4: 跨本体对齐 ─────────────────────────→ 预期1周
├── E4: 多Agent本体共享 ───────────────────→ 预期2周
└── E1: 知识演化环路 ──────────────────────→ 预期1月+
```

---

## 脑暴总结

```
gbrain知识图谱（现有）
    │
    │  D2: 注入(Ontology as Source)
    ▼
gbrain知识图谱（增强版） ←─── D1/D4: 搜索后处理
    │
    │  D3: 图查询+推理
    ▼
推理增强图谱 ─── B3: 多速率层 → C4: 跨本体对齐 → E4: 多Agent共享
    │
    │  E1: 知识演化环路
    ▼
自我演化的群体认知系统
```

核心洞察：**gbrain 的 source 机制是现成的本体隔离方案，三速率层可以直接映射到 source 命名空间。不需要侵入式改造，只需要在 GA 侧做好编排和推理后处理。**
