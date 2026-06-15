# GA (Beneh) 架构改进路线图 — P0 至 P4

> 日期: 2026-06-04
> 参考: Autogenesis (AGP协议) 架构对比分析
> 原则: 保持 GA 前端生态广度优势，补齐协议层 + 自进化深度

---

## 概览

| 优先级 | 改进项 | 核心问题 | 预期效果 | 工作量 |
|--------|--------|---------|---------|--------|
| **P0** | CodeGraph CLI → SQLite 原生 | subprocess 500ms/次，经常超时 | 速度 **500x**，零依赖 | ~200LOC |
| **P1** | 统一 Registry 注册中心 | ga.py 中 14+ do_* 手动分发 | 消除硬编码，工具自动发现 | ~300LOC |
| **P2** | 自进化闭环 | 无系统性反思/优化机制 | Agent 从"执行"升级为"进化" | ~400LOC |
| **P3** | Heartbeat 自动记忆提纯 | 记忆系统是工具型，无自动管道 | 记忆自适应压缩/提纯 | ~250LOC |
| **P4** | Tracer + Version 打通 | 追踪/版本分散，无 lineage 审计 | 全链路可审计、可回滚 | ~350LOC |

---

## P0: CodeGraph CLI → SQLite 原生调用

> 目标: 从 `subprocess("codegraph CLI")` 改为直接读 `.codegraph/codegraph.db`
> 速度提升: **500x** (500ms → 1ms)

### 现状分析

当前调用链路:
```
LLM → ga.py:do_codegraph()
  → tools/codegraph_mcp.py:codegraph_call()
    → _run_cli() → subprocess.run("codegraph query ...")
      → 等待 CLI 启动 (~200ms) + 查询 (~300ms)
```

痛点: CLI 可能不可用、每次冷启动、超时截断、JSON 解析脆弱。

### 设计

新建 `tools/codegraph_db.py` (~200LOC)，提供与 `codegraph_call()` 兼容的接口:

| 工具名 | SQL 实现 |
|--------|---------|
| `codegraph_get_symbol_info` | `SELECT * FROM nodes WHERE name LIKE ?` |
| `codegraph_get_callers` | `SELECT n.* FROM edges e JOIN nodes n ON e.source=n.id WHERE e.kind='calls'` |
| `codegraph_get_callees` | 反向 JOIN |
| `codegraph_get_module_summary` | `SELECT * FROM files` |
| `codegraph_find_by_imports` | `SELECT * FROM nodes WHERE kind='import'` |

回退策略: SQLite 失败时自动回退 CLI。

### 性能对比

| 操作 | CLI | SQLite | 提升 |
|------|-----|--------|------|
| symbol_search | ~800ms | ~2ms | 400x |
| files 列表 | ~500ms | ~1ms | 500x |
| 100次批量查询 | ~50s | ~0.2s | 250x |

### 文件清单

```
新建: GA/tools/codegraph_db.py    (~200LOC)
修改: GA/tools/codegraph_mcp.py   (~30行 — SQLite优先逻辑)
微调: GA/ga.py                    (0-10行 — 可选优化)
```

---

## P1: 统一 Registry 注册中心

> 目标: 消除 ga.py 中 14+ do_* 手动分发 + 前端 30+ handle_* 硬编码
> 参考: Autogenesis 的 mmengine Registry + 15 实例模式

### 现状分析

GA 当前的工具分发模式:
```python
# ga.py — 14 个 do_* 方法手动 if-elif
def do_ask_user(self, args, response): ...
def do_code_run(self, args, response): ...
def do_file_read(self, args, response): ...
def do_file_write(self, args, response): ...
def do_web_scan(self, args, response): ...
# ... 共 14 个，每个需要手动注册到 tool_schema
```

同时前端中 30+ 个 `handle_*` 分散在各文件中。

当前有 3 处"注册发现"机制但各自独立:
1. `memory/skill_search/` — 技能搜索
2. `memory/ljqCtrl` — 键盘鼠标
3. `Mqtt_bbs_server/` — BBS 注册

缺少统一的注册中心。

### 设计

创建 `tools/registry.py`，提供全局注册:

```python
# tools/registry.py
from mmengine.registry import Registry

TOOL = Registry("tool", locations=["GA.tools", "GA.frontends", "GA.memory"])
AGENT = Registry("agent", locations=["GA.agents"])
FRONTEND = Registry("frontend", locations=["GA.frontends"])
MEMORY = Registry("memory", locations=["GA.memory"])
```

迁移路径:
```
Phase 1: 创建 Registry + 注册所有 do_* 方法 (2小时)
Phase 2: 前端 handle_* 函数逐个注册 (4小时)
Phase 3: 工具自动发现替代 ga.py 手动 if-elif (2小时)
```

### 收益

| 指标 | 当前 | 改进后 |
|------|------|--------|
| 新增工具需改文件数 | 2-3 处 (ga.py + schema) | 1 处 (注册即可) |
| 工具发现 | 编译时静态 | 运行时自动 |
| 跨模块引用 | 显式 import | 按 name 查找 |

### 文件清单

```
新建: GA/tools/registry.py          (~80LOC)
修改: GA/ga.py                       (~100行 — 替换 do_* 分发为 registry 查表)
修改: GA/agentmain.py                (~30行 — load_tool_schema 改为从 registry 动态生成)
新增: 各 tools/*.py + frontends/*.py 添加 @TOOL.register() 装饰器
```

---

## P2: 自进化闭环 (Reflection Optimizer)

> 目标: 让 Agent 从"执行指令"升级为"从执行中学习并自我优化"
> 参考: Autogenesis 的 GrpoOptimizer / ReflectionOptimizer

### 现状分析

GA 仅有 5 个与学习相关的符号，且全是"从案例中学习技能"的单向管道:
```
GA/tools/learn_skill_from_cases/        — 从案例学技能
GA/tools/skill_learn_from_cases_full/   — 全量版本
GA/tools/skill_review.py               — 技能复习
```

无:
- 执行轨迹记录与分析
- 反思/自我批评机制
- 策略优化循环
- A/B 测试或策略回滚

### 设计

**Phase 1: 轨迹记录器 (Tracer)**
```python
class TurnTracer:
    """记录每次 agent 执行的完整轨迹"""
    def __init__(self):
        self.turns: list[TurnRecord] = []
        self.db: sqlite3.Connection  # 持久化到 trace.db
    
    def record(self, turn_id, prompt, tool_calls, results, reward): ...
    def replay(self, turn_id) -> TurnRecord: ...
    def search(self, query) -> list[TurnRecord]: ...
```

**Phase 2: 反思优化器**
```python
class ReflectionOptimizer:
    """基于执行轨迹的反思式优化"""
    
    def reflect_on_turn(self, turn: TurnRecord) -> Reflection:
        """分析单次执行的得失"""
        ...
    
    def extract_patterns(self, history: list[TurnRecord]) -> list[Pattern]:
        """从历史中提取成功/失败模式"""
        ...
    
    def generate_improvement(self, pattern: Pattern) -> Suggestion:
        """生成具体的 prompt/tool 改进建议"""
        ...
```

**Phase 3: 闭环集成**
```
Agent 执行 → Tracer 记录 → Reflection 分析 → 策略更新
   ↑                                              |
   └──────────── 下一轮使用新策略 ───────────────┘
```

### 文件清单

```
新建: GA/tools/tracer.py              (~150LOC) — 轨迹记录+回放
新建: GA/tools/reflection_optimizer.py (~200LOC) — 反思分析+改进
修改: GA/agentmain.py                 (~30行) — 集成 tracer
修改: GA/llmcore.py                   (~20行) — 集成反思信号
```

---

## P3: Heartbeat 自动记忆提纯

> 目标: 从"手动管理记忆"升级为"自动心跳摘要 → 洞察 → 压缩"管道
> 参考: Autogenesis HeartbeatMemorySystem (320LOC)

### 现状分析

GA 的 memory/ 目录:
```
memory/
├── ljqCtrl.py        — 键盘鼠标控制 (工具型)
├── keychain.py       — 密钥管理 (配置型)
├── ocr_utils.py      — OCR (工具型)
├── clipboard_ocr.py  — 剪贴板 OCR (工具型)
├── adb_ui.py         — ADB (工具型)
├── procmem_scanner.py— 进程内存扫描 (工具型)
└── skill_search/     — 技能搜索 (检索型)
```

所有模块都是"工具型/配置型"，无自动记忆管理。当前的记忆系统依赖:
- `global_mem.txt` + `global_mem_insight.txt` — 手动维护
- `L4_raw_sessions/` + `compress_session.py` — 手动压缩
- 无自动提纯管道

### 设计

```python
class HeartbeatMemorySystem:
    """基于心跳的自动记忆管理"""
    
    async def heartbeat(self, session_state):
        # 1. 提取关键事件
        events = self._extract_events(session_state)
        
        # 2. 生成摘要 vs 上次心跳
        summary = self._summarize(events, self.last_summary)
        
        # 3. 提取洞察 (模式/趋势/反常)
        insights = self._extract_insights(summary, self.history)
        
        # 4. 合并: 决定保留/丢弃/升级
        self._consolidate(summary, insights)
        
        # 5. 更新全局记忆
        self._sync_to_global_memory()
```

三层管道:
```
原始事件 → HeartbeatSummary (压缩编码)
               ↓
         HeartbeatInsight (模式提取)
               ↓
         HeartbeatCombinedMemory (合并写入 L2 记忆)
```

### 与现有系统集成

```
[当前]  L4_raw_sessions/  →  compress_session.py (手动)  →  global_mem.txt
[改进]  HeartbeatMemorySystem (自动)  →  HeartbeatInsight  →  global_mem_insight.txt
                                              ↕
                                     skill_search/ (自动检索)
```

### 文件清单

```
新建: GA/tools/heartbeat_memory.py       (~200LOC) — 核心心跳管道
新建: GA/tools/memory_types.py           (~50LOC)  — HeartbeatSummary/Insight 类型
修改: GA/agentmain.py                    (~20行)   — 集成心跳到主循环
修改: GA/llmcore.py                      (~15行)   — 每个 turn 后触发 heartbeat
```

---

## P4: Tracer + Version 打通

> 目标: 建立全链路可审计 Lineage + 版本化资源管理
> 参考: Autogenesis Tracer (~419LOC) + Version (~342LOC)

### 现状分析

GA 当前追踪/版本相关代码:
```
* 完全无:
  - 执行轨迹追踪 (trace/lineage)
  - 版本化资源注册
  - 审计日志
  - 回滚能力

* 仅有的边缘:
  GA/tools/skill_review.py      — 技能复习 (追踪复习计划)
  GA/tools/failure_tracker.py   — 失败追踪 (记录失败计数)
  GA/tools/security_audit.py    — 安全审计 (文件审计)
  GA/plugins/langfuse_tracing.py— Langfuse 外部追踪 (仅 LLM 调用)
```

### 设计

**Phase 1: Tracer — 执行轨迹审计**

```python
class LineageTracer:
    """全链路执行轨迹追踪"""
    
    def trace_turn(self, turn_id, parent_id, agent, action, context):
        """记录一次 agent 执行到 lineage DAG"""
        db.execute("INSERT INTO lineage ...")
    
    def trace_tool_call(self, turn_id, tool, args, result):
        """记录工具调用的输入输出"""
    
    def get_lineage(self, turn_id) -> list:
        """回溯某次执行的全链路"""
    
    def find_regressions(self, since_version) -> list:
        """查找从某版本后的回归"""
```

**Phase 2: Version — 资源版本管理**

```python
class ResourceVersionManager:
    """Prompt/Tool/Agent 版本化"""
    
    def snapshot(self, resource_type, resource_id):
        """创建资源快照"""
    
    def compare(self, v1, v2) -> Diff:
        """版本间差异对比"""
    
    def rollback(self, resource_type, resource_id, target_version):
        """回滚到指定版本"""
    
    def promote(self, version, stage: Stage):
        """提升版本阶段: dev → staging → production"""
```

**Phase 3: 打通集成**

```
LineageTracer ←→ Registry (版本化注册)
     ↕
ResourceVersionManager ←→ HeartbeatMemory (版本化记忆)
     ↕
Rollback ←→ 所有 stateful 操作
```

### 与 Autogenesis 差距对比

| 特性 | Autogenesis | GA 当前 | GA 目标 |
|------|-------------|---------|---------|
| 执行追踪 | Tracer (419LOC) | 无 | Tracer |
| 版本管理 | Version (342LOC, 3 files) | 无 | VersionManager |
| 回滚 | 未实现 (论文声称) | 无 | Rollback |
| 审计 lineage | Tracer 可追踪 | 无 | LineageTracer |
| 与 registry 打通 | 未集成 | 无 | 全集成 |

### 文件清单

```
新建: GA/tools/lineage_tracer.py        (~150LOC) — 执行链追踪
新建: GA/tools/resource_version.py      (~150LOC) — 资源版本管理
新建: GA/db/lineage_schema.sql          (~50LOC)  — lineage DAG 数据库 schema
修改: GA/ga.py                           (~20行)   — tracer 埋点
修改: GA/tools/registry.py               (~30行)   — 版本化注册
```

---

## 实施路线图

### 总工期估算: 5-7 天 (单人)

```
Week 1                    Week 2
┌────┬────┬────┬────┬────┬────┬────┐
│ P0 │ P0 │ P1 │ P1 │ P2 │ P2 │ P3 │
│ DB │ 集 │ 注 │ 前 │ Tra│ Ref│ Hea│
│ 设 │ 成 │ 册 │ 端 │ cer│ lec│ rt │
│ 计 │ 测 │ 中 │ 迁 │ 设 │ 优 │ bea│
│    │ 试 │ 心 │ 移 │ 计 │ 化 │ t  │
├────┼────┼────┼────┼────┼────┼────┤
│    P0 done    │    P1 done   │ P3 │ P4 │
│                                  done│ done│
```

### 依赖关系

```
P0 [SQLite]   ← 无依赖, 可最先做
P1 [Registry] ← 无依赖, 可与 P0 并行
P2 [Tracer]   ← 依赖 P1 (工具注册)
P3 [Heartbeat]← 无依赖, 可与 P1 并行
P4 [Version]  ← 依赖 P1 (版本化注册)
                 依赖 P2 (lineage 追踪)
```

### 关键节点

| 里程碑 | 交付物 | 验收标准 |
|--------|--------|---------|
| P0 完成 | `tools/codegraph_db.py` | 100 次 SQLite 查询 < 500ms |
| P1 完成 | `tools/registry.py` + 迁移 | 新增工具只需 1 行 `@TOOL.register()` |
| P2 完成 | `tools/tracer.py` + `reflection_optimizer.py` | Agent 可基于历史轨迹自我改进 |
| P3 完成 | `tools/heartbeat_memory.py` | 自动提纯全局记忆，无需手动维护 |
| P4 完成 | `tools/lineage_tracer.py` + `resource_version.py` | 全链路可审计，支持版本回滚 |
