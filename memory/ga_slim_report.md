# GA 代码瘦身项目 — 执行报告

> 日期: 2026-06-11
> 基于 CodeGraph (6238节点/319文件/11498边)

## Phase 1: 安全清理

| 项目 | 操作 | 状态 |
|------|------|------|
| llm_cache_client.py | 删除 | 完成 |
| cache_monitor.py | 删除 | 完成 |
| llm_cache_optimization_plan.md | 删除 | 完成 |
| .llm_cache/ (30条目) | 删除 | 完成 |
| _archives/frontends/ (13文件, 976节点) | 移入 Beneh/archives/ | 完成 |
| skills_learning/ | 删除 | 完成 |
| knowledge-work-plugins/ | 删除 | 完成 |

## Phase 2: Ga_tools/ 提取

| 工具域 | 文件数 | 路径 |
|--------|--------|------|
| 根级工具 | 15 | Ga_tools/*.py |
| utils/ | 12 | Ga_tools/utils/ |
| mcp/ | 7 | Ga_tools/mcp/ |
| agent/ | 7 | Ga_tools/agent/ |
| observability/ | 6 | Ga_tools/observability/ |
| llm/ | 5 | Ga_tools/llm/ |
| curiosity/ | 4 | Ga_tools/curiosity/ |
| reflection/ | 4 | Ga_tools/reflection/ |
| skills/ | 3 | Ga_tools/skills/ |
| security/ | 3 | Ga_tools/security/ |
| history/ | 3 | Ga_tools/history/ |
| ui/ | 1 | Ga_tools/ui/ |
| **总计** | **74** | **Ga_tools/** |

## Phase 3: 死代码候选 (23个零调用文件)

### 高风险（可安全删除）
| 文件 | 理由 |
|------|------|
| persistence.py | 已迁移到 Rust 版 |
| test_auth_flow.py | 测试文件，非生产 |
| board_db.py | 与 persistence.py 重叠 |
| plugin_manager.py | 从未加载 |

### 中等风险（需人工确认）
| 文件 | 理由 |
|------|------|
| knowledge_graph.py | mempalace_bridge 替代 |
| board_handlers.py, board_core.py | 可能被动态加载 |
| mempalace_mcp_launcher.py | MCP server |

### 低风险（虽零调用但功能重要）
| 文件 | 理由 |
|------|------|
| gbrain_mcp.py | HMR 动态引用 |
| ontology_codegraph_bridge.py | 本体桥接 |
| diagnosis_agent.py | 事件驱动诊断 |
| clipboard_ocr.py | 工具函数 |

## 文件数变化

| 指标 | 瘦身前 | 瘦身后 | 变化 |
|------|--------|--------|------|
| 项目文件 | 319 | ~273 | -46 (-14%) |
| 代码节点 | 6238 | ~5262 | -976 |
| archive 文件 | 13 | 0 | -13 |
