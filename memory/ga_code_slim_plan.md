---
skill: ga_code_slim
domain: code-refactoring
version: "1.0"
tags: [codegraph, refactoring, slimming, ga-tools]
cc_quick: "GA代码瘦身方案 — 用CodeGraph分析结果，分4阶段提取Ga_tools/"
cc_keywords: ["GA瘦身", "Ga_tools", "代码重构", "死代码清理", "archive"]
---

# GA 代码瘦身方案

> 基于 CodeGraph 分析 (6238节点/319文件/11498边)
> 目标: 提取核心工具到 `open_claw_agent/Ga_tools/`，清理冗余

---

## Phase 1: 直接清理（安全、无副作用）

### 1.1 删除已弃用的 llm_cache_rs 相关文件
| 文件 | 理由 |
|------|------|
| `tools/llm_cache_client.py` | 用户确认已弃用 |
| `tools/cache_monitor.py` | 仅服务于 llm_cache_rs |
| `memory/llm_cache_optimization_plan.md` | 对应 SOP |
| `temp/test_llm_cache_leak.py` | 测试文件 |
| `.llm_cache/` 目录 | 缓存数据目录 |

**验证**: codegraph_impact 确认这些文件零调用者 (dead code)

### 1.2 清理 _archives/ 目录
`GA/_archives/frontends/` 下 13 个文件，共 976 节点，全部是**已归档的前端版本**:
- tuiapp_v2.py, qtapp.py, tgapp.py, conductor.py, desktop_bridge.py
- wechatapp.py, wecomapp.py, dcapp.py, stapp2.py, qqapp.py
- dingtalkapp.py, genericagent_acp_bridge.py, subagent_dashboard.py

**操作**: 整体移出 GA 目录到 `Beneh/archives/` 或直接删除

### 1.3 删除重叠/重复目录
| 目录 | 理由 |
|------|------|
| `skills_learning/` | 与 `tools/skill_learn_from_cases_full/` 重叠 |
| `knowledge-work-plugins/` | 仅 2 个文件，非核心 |

---

## Phase 2: 核心工具提取到 Ga_tools/

### 2.1 确定 Ga_tools/ 结构

```
Ga_tools/
├── llm/                    # LLM 相关
│   ├── llmcore.py          # 核心 LLM 交互
│   └── providers/          # provider 管理
│       ├── session.py
│       └── ...
├── mcp/                    # MCP 工具
│   ├── codegraph_db.py
│   ├── codegraph_mcp.py
│   ├── ontology_codegraph_bridge.py
│   ├── ontology_model.py
│   ├── gbrain_mcp.py
│   └── tool_definitions.py
├── ui/                     # UI/浏览器工具
│   ├── TMWebDriver.py
│   ├── gui_vision.py
│   └── vision_api.py
├── memory/                 # 记忆系统
│   ├── knowledge_graph.py
│   ├── mempalace_bridge.py
│   └── ...
├── agent/                  # Agent 框架
│   ├── diagnosis_agent.py
│   ├── registry.py
│   └── ...
├── observability/          # 可观测性
│   ├── tracer.py
│   ├── failure_tracker.py
│   ├── ga_watchdog.py
│   └── ...
├── reflection/             # 反思引擎
│   ├── reflection_engine.py
│   ├── reflection_optimizer.py
│   ├── step_detector.py
│   └── goal_nexus.py
├── utils/                  # 通用工具
│   ├── resource_version.py
│   └── ...
├── skills/                 # 技能系统
│   └── skill_review.py
├── curiosity/              # 好奇心引擎
│   └── inspiration_board.py
├── security/               # 安全
│   └── ...
├── history/                # 历史管理
│   └── session_compactor.py
└── pdca/                   # PDCA 循环
    └── ...
```

### 2.2 提取规则
1. **不复制，不移动** — 在 Ga_tools/ 下创建软链接或 import redirect
2. **保留 GA/ 内原有文件不动**，确保运行不中断
3. Ga_tools/ 作为**新项目的依赖基座**
4. 每个模块用 `__init__.py` 暴露公共 API

---

## Phase 3: 死代码扫描（CodeGraph 驱动的精准删除）

### 3.1 零调用者检测
使用 codegraph 找所有"无人调用"的模块:
```
codegraph query "callers:0"     # 找到所有入度为 0 的模块
codegraph impact <file>         # 确认修改无影响
```

### 3.2 候选文件
基于物理扫描的候选:
| 文件 | 节点数 | 可疑理由 |
|------|--------|----------|
| `assets/configure_mykey.py` | 44 | 一次性配置工具 |
| `tests/` 下 20 个文件 | 平均30+ | 一次性测试 |
| `temp/` 下 33 个 py 文件 | 不等 | 临时实验 |

### 3.3 验证步骤
对于每个候选:
1. `codegraph callers <symbol>` → 如果返回空 → 死代码
2. `codegraph impact <file>` → 如果返回"无影响" → 安全删除
3. `grep -r "import.*<mod>" GA/` → 确认无引用

---

## Phase 4: 新项目模板生成

### 4.1 生成 Ga_tools/ starter
```
open_claw_agent/
├── Ga_tools/          # 核心工具（本方案产出）
│   ├── requirements.txt
│   ├── setup.py
│   └── ...
├── Ga/                # 原项目（不动）
├── Beneh/             # 存档/文档
├── Mqtt_bbs_server/   # 独立服务（不动）
└── memory/            # 共享记忆
```

### 4.2 验证清单
- [ ] Ga_tools/ 内每个模块可独立 `import`
- [ ] 原有 GA/ 运行不受影响
- [ ] `codegraph sync` 后索引正常
- [ ] `codegraph status` 确认节点数合理减少（预计从319降到200左右）

---

## 附录: 关键发现汇总

| 指标 | 当前值 | 瘦身后预期 |
|------|--------|-----------|
| 文件数 | 319 | ~180 (-44%) |
| 节点数 | 6238 | ~4500 |
| archive 文件 | 13 (976节点) | 0 |
| 测试文件 | 20+ | 可独立管理 |
| temp/ 文件 | 33 | 0 |
| 核心 tools/ | ~50 文件 | Ga_tools/ 保留 |

**核心原则**: 不破坏现有 GA 运行，Ga_tools/ 作为**增量提取**，不是**暴力迁移**。
