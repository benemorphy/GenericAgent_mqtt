# MemPalace 集成 SOP — 语义搜索 + 知识图谱 + MCP Server

> Palaca: 2526 drawers, 6 rooms | 集成状态: Phase 1-4 全部完成

---

## 0. 架构总览

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
   │     (SQLite, 15实体, co_domain)│
   │                              │
   │  ③ Metaso API / es.exe / Bing│
   └──────────────────────────────┘
          │
          ▼
    File-Based 记忆 (Source of Truth)
```

**核心原则**: MemPalace 是**只读增强层**, 不修改 L1/L2/L3 文件系统。

---

## 1. 组件清单

| 文件 | 作用 | 使用方式 |
|------|------|----------|
| `mempalace_bridge.py` | Python API: 语义搜索 | `from memory.mempalace_bridge import semantic_search` |
| `mempalace_mcp_launcher.py` | MCP Server 管理 | `python ... start\|stop\|status\|save` |
| `knowledge_graph.py` | Python API: 知识图谱 | `from memory.knowledge_graph import KnowledgeGraph` |
| `mempalace.yaml` | Palace 房间配置 (1 wing, 6 rooms) | 自动生成, 可手动编辑 |
| `.mempalace/palace/` | Palace 数据 (chroma.sqlite3) | 自动维护, 勿手动编辑 |
| `.knowledge_graph.db` | 知识图谱 SQLite | 自动维护, 可用 sqlite3 查询 |

---

## 2. 日常使用: 三层 API

### 2a. 语义搜索 (首选)

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
- 模糊记忆: `"BoardService 收不到消息"` → 余弦≈0.55-0.70
- 技术问题: `"SQLite 迁移到 MariaDB 报错"` → 找到相关 SOP
- 工具方法: `"如何用 uv 安装包"` → 找到 project 配置

**坑**:
- 首次查询因 ONNX 模型加载需 ~2s, 后续 < 500ms
- 低 cosine (< 0.35) 结果大多不相关
- n_results 默认 5, 最多 20
- 中文搜索建议中英文混合查询 (all-MiniLM-L6-v2 非中文优化)

### 2b. 知识图谱查询 (次选)

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
# [{"name": "MQTT_BBS", "section": "L2", ...}]
```

**数据源**: 从 `global_mem.txt` 的 `## [SECTION_NAME]` 自动提取。
**关系类型**: `co_domain` (同命名域前缀), `references` (跨域引用), `depends_on` (显式依赖)。

### 2c. MCP Server (外部工具)

```bash
# 启动
python GA/memory/mempalace_mcp_launcher.py start

# 停止
python GA/memory/mempalace_mcp_launcher.py stop

# 查看状态
python GA/memory/mempalace_mcp_launcher.py status

# 自动保存 (mine 增量同步)
python GA/memory/mempalace_mcp_launcher.py save --session "2026-06-08_debug"
```

MCP Server 暴露 32 个工具 (SSE 传输), 包括:
- `tool_status`, `tool_list_wings`, `tool_list_rooms`
- `tool_search`, `tool_search_wing`, `tool_search_room`
- `tool_mine`, `tool_sweep`, `tool_compress`
- `tool_entity_query`, `tool_relation_query`

---

## 3. 集成在项目中的触发点

| 触发点 | 动作 | 位置 |
|--------|------|------|
| 项目启动 | MCP Server 后台启动 | `start_all.ps1` section 13 |
| 会话结束 | `mempalace mine` 增量同步 | 手动 `python mempalace_mcp_launcher.py save` |
| 检索记忆 | `semantic_search()` 先于 `file_read` | META-SOP 公理 #5 + L1 RULE #13 |
| 启动服务 | Everything 服务 + MCP PID 管理 | `start_all.ps1` section 10 + 13 |

---

## 4. 维护

### 何时重建知识图谱
当 `global_mem.txt` 的 `## [SECTION]` 新增或修改时:
```python
from memory.knowledge_graph import KnowledgeGraph
KnowledgeGraph().rebuild()
```

### 何时重新 mine
当 `GA/memory/` 下新增 SOP 文件时。如需强制全部重 mine:
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

### 如何添加新房间
编辑 `GA/memory/mempalace.yaml`, 新增 room 配置后重新 mine.

---

## 5. 故障排查

| 问题 | 原因 | 解决 |
|------|------|------|
| 搜索返回空/低质量 | Palace 未 mine 或模型未下载 | 确认 `palace_status()['available']==True` |
| MCP Server 启动失败 | `mempalace-mcp.exe` 未找到 | 确认 `.venv/Scripts/` 下存在 |
| KnowledgeGraph 实体不全 | L2 未同步 | `KnowledgeGraph().rebuild()` |
| 中文搜索效果差 | all-MiniLM-L6-v2 非中文优化 | 中英文混合查询 |
| `GBK` 编码错误 | Windows 终端编码 | `set PYTHONIOENCODING=utf-8` |

---

## 6. 文件关系图

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

---

## 7. 更新日志

| 日期 | 变更 | 原因 |
|------|------|------|
| 2026-06-08 | META-SOP 新增公理 #5: MemPalace 优先检索 | 确保检索流程强制调用语义搜索 |
| 2026-06-08 | L1 RULES 新增 #13 | 同步索引可发现性 |
| (以前) | Phase 1-4 全部完成 | 集成计划 `mempalace_integration_plan.md` |
