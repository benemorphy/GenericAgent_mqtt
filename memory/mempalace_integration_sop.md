# MemPalace 集成 SOP — 独立整合版

> 本文件整合了三部分内容：集成计划 + 使用 SOP + META-SOP 强制规则

---

## 目录

- [Part A: 集成计划（做了什么）](#part-a-集成计划做了什么)
- [Part B: META-SOP 强制规则（必须遵守）](#part-b-meta-sop-强制规则必须遵守)
- [Part C: 日常使用指南（怎么用）](#part-c-日常使用指南怎么用)
- [附录：故障排查](#附录故障排查)

---

## Part A: 集成计划（做了什么）

### 架构原则

- **File-Based 为 Source of Truth**，MemPalace 为只读增强层
- 不破坏现有 Action-Verified 原则
- 不修改现有 L1/L2/L3 层级结构，仅追加

### Phase 1: 基础安装 + 索引 [完成]

- [x] `uv pip install` mempalace (v3.4.0)
- [x] `mempalace init GA/memory/` → `mempalace.yaml` 配置 (1 wing / 6 rooms)
- [x] Mine L1/L2/L3 → Palace: **2526 drawers, 6 rooms**
- [x] `mempalace_bridge.py` — 语义搜索桥接模块
- [x] 验证: `ga_mqtt_bbs_scenarios.md` 命中 cosine=0.695

### Phase 2: 语义搜索增强 [完成]

- [x] `search_skills_sop.md` — MemPalace 设为搜索首选工具
- [x] `global_mem_insight.txt` L3 — 添加 `mempalace_bridge(语义搜索优先)`
- [x] 验证: "BoardService 故障诊断" → 0.695, "SQLite到MariaDB迁移" → 0.564

### Phase 3: 知识图谱集成 [完成]

- [x] 从 `global_mem.txt` 提取 15 个实体
- [x] 注入 KnowledgeGraph (SQLite: `.knowledge_graph.db`)
- [x] API: `query_entity()` / `query_relations()` / `search_entities()`
- [x] `knowledge_graph.py` — 知识图谱模块

### Phase 4: MCP Server + 自动保存 [完成]

- [x] `mempalace_mcp_launcher.py` — start/stop/status/save/tools
- [x] MCP Server 后台进程管理 (PID 文件 + taskkill)
- [x] Auto-save hook: `python mempalace_mcp_launcher.py save`
- [x] 32 个 MCP 工具可用

### 产出文件清单

| 文件 | 功能 |
|------|------|
| `GA/memory/mempalace_bridge.py` | 语义搜索桥接 (semantic_search/quick_search/palace_status) |
| `GA/memory/knowledge_graph.py` | 知识图谱 (KnowledgeGraph 类) |
| `GA/memory/mempalace_mcp_launcher.py` | MCP Server 启动器 + 自动保存 |
| `GA/memory/.mempalace/palace/` | Palace 数据 (chroma.sqlite3, ~28MB) |
| `GA/memory/.knowledge_graph.db` | 知识图谱 SQLite 数据库 |
| `GA/memory/mempalace.yaml` | Palace 房间配置 (1 wing, 6 rooms) |
| `GA/memory/search_skills_sop.md` | 搜索优先级指南 |

### 6 个 Palace Rooms

| Room | Drawers | 内容 |
|------|---------|------|
| `l4_raw_sessions` | 1935 | 历史会话原始数据 |
| `general` | 461 | 通用 SOP/配置/规则 |
| `inspirations` | 40 | 灵感记录 |
| `autonomous_operation_sop` | 39 | 自主运维 SOP |
| `learning_log` | 29 | 学习日志 |
| `skill_search` | 22 | 技能搜索记录 |

---

## Part B: META-SOP 强制规则（必须遵守）

### 来源

这条规则是 `memory_management_sop.md` (L0 META-SOP) 的**第 5 条核心公理**，具有最高优先级。

### 规则原文

```
5.  **MemPalace 优先检索 (MemPalace-First Retrieval)**
    *   **定义**：在 L3 检索前，必须先调用
        `from memory.mempalace_bridge import semantic_search`
        进行语义搜索定位，再根据结果精确 `file_read`。
    *   **禁止**：禁止无引导的猜测路径遍历或
        全量扫描文件目录来找 L3 记忆文件。
    *   **例外**：已知精确路径、文件名或 SOP 名时，
        可直接 `file_read`。
    *   **理由**：Palace 已索引 2526 drawers / 6 rooms，
        语义搜索 < 500ms，远快于目录遍历。
```

### L1 索引同步

`global_mem_insight.txt` RULE #13:

```
13. MemPalace优先检索: 任何记忆读取前先
    from memory.mempalace_bridge import semantic_search
    做语义搜索定位, 再精确 file_read;
    已知精确路径/SOP名可跳过
```

### 搜索优先级队列

```
     Agent 检索请求
          │
          ▼
   ┌──────────────────────────────┐
   │   搜索优先级队列 (META-SOP #5) │
   │                              │
   │  ① MemPalace 语义搜索 ← 首选  │
   │     (cosine向量, 2526抽屉)     │
   │                              │
   │  ② KnowledgeGraph 实体查询    │
   │     (SQLite, 15实体)          │
   │                              │
   │  ③ Metaso API / es.exe / Bing│
   └──────────────────────────────┘
          │
          ▼
    File-Based 记忆 (Source of Truth)
```

---

## Part C: 日常使用指南（怎么用）

### C1. 语义搜索 (首选)

```python
from memory.mempalace_bridge import semantic_search, quick_search, palace_status

# 结构化搜索 -- 返回 list[dict]
results = semantic_search("BoardService 消息丢失排查", n_results=5)
# 每项: {"source": "mqtt_service_config.md", "room": "general",
#         "cosine": 0.575, "bm25": 2.533, "content": "..."}

# 快速搜索 -- 返回格式化字符串
print(quick_search("Caddy 反向代理配置"))

# 状态检查
s = palace_status()
# {"available": True, "drawers": 2526, "rooms": ["general", ...]}
```

**查询技巧**:

| 场景 | 示例查询 | 预期 cosine |
|------|----------|-------------|
| 模糊记忆 | `"BoardService 收不到消息"` | 0.55-0.70 |
| 技术问题 | `"SQLite 迁移到 MariaDB 报错"` | 0.50-0.65 |
| 工具方法 | `"如何用 uv 安装包"` | 0.45-0.60 |

**注意**:
- 首次查询因 ONNX 模型加载需 ~2s，后续 < 500ms
- cosine < 0.35 的结果大多不相关
- n_results 默认 5，最多 20
- 中文搜索建议中英文混合 (all-MiniLM-L6-v2 非中文优化)

### C2. 知识图谱查询 (次选)

```python
from memory.knowledge_graph import KnowledgeGraph

kg = KnowledgeGraph()

# 查询实体
entity = kg.query_entity("GATEWAY")
# {"name": "GATEWAY", "description": "...", "properties": {...}}

# 查询关系
rels = kg.query_relations("MQTT_BBS")
# [{"source": "MQTT_BBS", "target": "MQTT_STRESS",
#    "relation": "co_domain", "weight": 1.0}]

# 搜索实体
results = kg.search_entities("mqtt")
```

**数据源**: 从 `global_mem.txt` 的 `## [SECTION_NAME]` 自动提取。
**关系类型**: `co_domain` (同命名域前缀), `references` (跨域引用), `depends_on` (显式依赖)。

### C3. MCP Server 管理

```bash
# 启动 (后台)
python GA/memory/mempalace_mcp_launcher.py start

# 停止
python GA/memory/mempalace_mcp_launcher.py stop

# 查看状态
python GA/memory/mempalace_mcp_launcher.py status

# 自动保存 (mine 增量同步)
python GA/memory/mempalace_mcp_launcher.py save --session "2026-06-08_session"
```

MCP Server 暴露 32 个工具 (SSE 传输):

| 类别 | 工具 |
|------|------|
| 状态 | `tool_status`, `tool_list_wings`, `tool_list_rooms`, `tool_get_taxonomy` |
| 搜索 | `tool_search`, `tool_search_wing`, `tool_search_room` |
| 管理 | `tool_mine`, `tool_mine_session`, `tool_sweep`, `tool_compress` |
| 图谱 | `tool_entity_query`, `tool_relation_query` |

### C4. 项目集成触发点

| 触发点 | 动作 | 位置 |
|--------|------|------|
| 项目启动 | MCP Server 后台启动 | `start_all.ps1` section 13 |
| 会话结束 | `mempalace mine` 增量同步 | 手动 `python mempalace_mcp_launcher.py save` |
| 检索记忆 | `semantic_search()` 先于 `file_read` | META-SOP 公理 #5 |
| 启动服务 | Everything 服务 + MCP PID 管理 | `start_all.ps1` section 10 + 13 |

### C5. 维护

**重建知识图谱** — 当 `global_mem.txt` 的 `## [SECTION]` 新增或修改时:

```python
from memory.knowledge_graph import KnowledgeGraph
KnowledgeGraph().rebuild()
```

**重新 mine** — 当 `GA/memory/` 下新增 SOP 文件，或需强制重建时:

```bash
# 1. 停止 MCP Server
python GA/memory/mempalace_mcp_launcher.py stop

# 2. 删除旧 Palace
rm -rf GA/memory/.mempalace

# 3. 重新 init + mine
python -m mempalace init --yes GA/memory/
python -m mempalace mine GA/memory/

# 4. 重启 MCP Server
python GA/memory/mempalace_mcp_launcher.py start
```

**添加新房间** — 编辑 `GA/memory/mempalace.yaml`，新增 room 配置后重新 mine:

```yaml
rooms:
- name: my_new_room
  description: Files from my_new_room/
  keywords:
  - my_new_room
```

---

## 附录：故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 搜索返回空/低质量 | Palace 未 mine 或模型未下载 | 确认 `palace_status()['available']==True` |
| MCP Server 启动失败 | `mempalace-mcp.exe` 未找到 | 确认 `.venv/Scripts/` 下存在 |
| KnowledgeGraph 实体不全 | L2 未同步 | `KnowledgeGraph().rebuild()` |
| 中文搜索效果差 | all-MiniLM-L6-v2 非中文优化 | 中英文混合查询 |
| `GBK` 编码错误 | Windows 终端编码 | `set PYTHONIOENCODING=utf-8` |
| 提示 `ModuleNotFoundError: No module named 'click'` | 早期 streamlit 依赖缺失 | `uv pip install click` |

---

## 完整的文件关系图

```
global_mem_insight.txt (L1) ──索引──▶ memory_management_sop.md (L0, 公理#5)
                                           │
                                           ├─强制▶ semantic_search() ← mempalace_bridge.py
                                           │                │
                                           │           (subprocess) mempalace CLI
                                           │                │
                                           │           .mempalace/palace/ (chroma.sqlite3)
                                           │
                                           ├─备选▶ KnowledgeGraph.query_entity()
                                           │                │
                                           │           .knowledge_graph.db (SQLite)
                                           │
                                           └─外部▶ MCP Server (mempalace-mcp.exe, SSE)
                                                               │
                                                         32 tools 对外暴露
```
