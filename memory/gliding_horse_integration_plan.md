# Gliding Horse Agent OS — GA 整合方案

> 日期: 2026-06-10
> 源项目: https://github.com/doiito/gliding_horse
> 定位: Rust 构建的工业级 AI Agent 操作系统，PDCA 循环 + 5W2H 本体 + Oxigraph 知识图谱 + JSON-LD

---

## 一、整合哲学：借鉴不搬运

Gliding Horse 是用 Rust 写的完整 Agent OS，GA 是用 Python 写的 Agent 框架。
强行代码级整合（如编译 Rust 模块）成本高、收益不确定。

**核心策略：提取设计理念 → 用 GA 原生能力实现 → gRPC 桥接作为可选进化方向**

---

## 二、GA 现状与 GH 概念的映射分析

### 2.1 Agent 循环

| GA 当前 | GH 概念 | 差距分析 |
|---------|---------|----------|
| 隐式 Agent Loop（LLM 自主选工具） | PDCA 显式循环（Plan-Do-Check-Act） | GA 缺少任务复杂度分级和结构化审计 |
| 工具注册 (`@TOOL.register`) | Skill Graph (RDF 语义技能网络) | GH 的 Skill 有类型层级 + 语义链接 + 自进化能力 |
| goal_mode / plan_mode 双模式 | 7 级复杂度自适应 (L0-L6) | GH 有明确的复杂度分级标准 |

### 2.2 记忆系统

| GA 当前 | GH 概念 | 差距分析 |
|---------|---------|----------|
| MemPalace (L1-L4 层级) | L0 Sled+Qdrant, L2 Oxigraph, MESI 一致性 | GA 缺失 L2 黑板书板 (Blackboard) |
| knowledge_graph.py (OWL/TTL) | Oxigraph RDF + SPARQL 1.1 | GA 本体引擎更强但缺 SPARQL 查询 |
| file_access_stats.json | graphMeta (usageCount/successRate) | GH 有明确的统计反馈机制 |

### 2.3 数据格式

| GA 当前 | GH 概念 | 差距分析 |
|---------|---------|----------|
| JSON (自由格式) | JSON-LD 1.1 (`@id/@type/@context`) | GA 缺语义互操作层 |
| 无统一的 data bus | Named Graphs + Data Bus | GH 有明确的数据总线设计 |

---

## 三、整合方案（4 阶段）

---

### 阶段 1: 设计理念提取 (P0, 2h, 零代码风险)

#### 1.1 PDCA 任务复杂度分级 —— 注入 prompt

在 Agent system prompt 中嵌入 PDCA 分级指引，让 LLM 自行选择任务执行模式。

**新增 `tools/pdca/pdca_classifier.py`**:

```python
"""
PDCA 任务复杂度分级器

自动将新任务分配到 7 级复杂度，决定 Agent 执行策略。
"""

TASK_LEVELS = {
    0: {
        "name": "L0_Instant",
        "desc": "即时任务，单轮无需规划",
        "pattern": ["当前时间", "简单查询", "单一工具调用"],
        "prompt_instruction": "直接执行，无需 Plan 步骤",
    },
    1: {
        "name": "L1_Simple",
        "desc": "简单任务，单次 PDCA",
        "pattern": ["读取文件", "简单搜索", "单步操作"],
        "prompt_instruction": "先做简单计划，然后执行，最后确认结果",
    },
    2: {
        "name": "L2_Standard",
        "desc": "标准任务，完整 PDCA + 审计",
        "pattern": ["分析数据", "多步代码", "文件修改"],
        "prompt_instruction": "Plan-Do-Check-Act 四阶段完整执行",
    },
    3: {
        "name": "L3_Complex",
        "desc": "复杂项目，多 Agent 并行",
        "pattern": ["大型重构", "跨模块开发", "系统设计"],
        "prompt_instruction": "拆分子任务，多 Agent 并行执行 Do 阶段",
    },
    4: {
        "name": "L4_Exploratory",
        "desc": "探索型任务，多方案并行",
        "pattern": ["技术调研", "方案对比", "研究方向"],
        "prompt_instruction": "多 Agent 并行探索不同策略后综合",
    },
    5: {
        "name": "L5_Recursive",
        "desc": "递归任务，子 PDCA 嵌套",
        "pattern": ["全面重构", "大型系统", "完整项目"],
        "prompt_instruction": "递归拆解：子任务生成子 PDCA 循环",
    },
    6: {
        "name": "L6_Emergency",
        "desc": "紧急模式，跳过 Plan 直接 Do",
        "pattern": ["修 Bug", "线上故障", "紧急恢复"],
        "prompt_instruction": "跳过 Plan 阶段，直接 Do-Check-Act 循环",
    },
}


def classify_task(task_description: str, available_tools: list) -> int:
    """基于任务描述和可用工具，判定复杂度级别 (0-6)"""
    # 规则引擎 + LLM 二次确认
    ...
    return level
```

**使用方式**: 在 `ga.py` 的 `_build_prompt` 中根据复杂度级别注入不同的 instruction。

**预期效果**: Agent 不再对"查个时间"和"重构整个项目"用同一套 Loop，减少 LLM token 浪费。

---

#### 1.2 5W2H 任务本体 —— 结构化 task init

在 `update_working_checkpoint` 中增加 5W2H 字段：

```python
# 当前
key_info = {
    "objective": "重构用户模块",
}

# 改进后
key_info = {
    "5W2H": {
        "what": "重构用户模块认证逻辑",
        "why": "现有 JWT 实现存在安全漏洞",
        "who": "当前 Agent (单人)",
        "when": "本对话内完成",
        "where": "ga/user_auth.py",
        "how": "重写 JWT 验证 + 增加 Token 刷新",
        "how_much": "预计 50-80 行代码变更",
    }
}
```

**效果**: LLM 获得明确的约束边界，减少意图漂移。

---

### 阶段 2: JSON-LD 互操作层 (P1, 4h, 小范围改动)

#### 2.1 新增 `tools/jsonld/` 模块

```python
# tools/jsonld/converter.py
"""
GA ↔ JSON-LD 格式转换器

JSON-LD 是 GH 的核心数据总线格式，采用 @id/@type/@context 语义标记。
GA 通过此模块实现：
1. 工具调用输入/输出的语义标记
2. 跨 Agent 消息的互操作格式
3. 未来与 GH gRPC 桥接的基础
"""

def to_jsonld(data: dict, context: dict = None) -> dict:
    """将 GA 内部数据转换为 JSON-LD 格式"""
    ...

def from_jsonld(ld_data: dict) -> dict:
    """从 JSON-LD 提取 GA 内部数据"""
    ...
```

#### 2.2 在 MemPalace 中增加 JSON-LD 支持

`mempalace_bridge.py` 增加 `store_jsonld()` / `query_jsonld()` 接口。

---

### 阶段 3: gRPC 桥接 (P2, 1-2d, 需要 GH 运行时)

#### 3.1 GA 作为 gRPC Client

根据 GH 的 `pdca_core.proto`，生成 Python gRPC stub：

```python
# tools/grpc_bridge/pdca_client.py
"""
GA → GH gRPC Client 桥接

调用 GH 的 PDCACoreService：
- InitTask: 让 GH 调度复杂任务
- WriteNode/ReadNode: 读写 GH 的 L2 Blackboard
- QueryNodes: SPARQL 查询 GH 的知识图谱
- ListSkills: 发现 GH 注册的技能
"""

import grpc
from pdca_core_pb2 import ...
from pdca_core_pb2_grpc import PDCACoreServiceStub

class GHBridge:
    def __init__(self, endpoint="127.0.0.1:50051"):
        self.channel = grpc.insecure_channel(endpoint)
        self.stub = PDCACoreServiceStub(self.channel)
    
    def init_task(self, task_jsonld: dict) -> str:
        """委托 GH 初始化并调度一个任务"""
        resp = self.stub.InitTask(InitTaskRequest(...))
        return resp.task_iri
    
    def query_knowledge(self, sparql: str) -> list:
        """SPARQL 查询 GH 的 Oxigraph 知识图谱"""
        resp = self.stub.QueryNodes(QueryNodesRequest(sparql=sparql))
        return resp.nodes
```

#### 3.2 启动/停止 GH 的 SOP

新增 `memory/gliding_horse_sop.md`，包含：
- 下载/编译 GH
- 启动 GH core server
- GA 连接配置
- 健康检查

---

### 阶段 4: Skill Graph 借鉴 (P3, 3d+, 深度改造)

#### 4.1 从工具注册 → 语义技能网络

```python
# 当前: 扁平工具注册
@TOOL.register()
def do_file_read(self, args, response): ...

# 改进: 带语义标记的技能
@skill.register(
    id="ga:skill/file_read",
    type="skill:AtomicSkill",
    context=["file_operations", "code_reading"],
    prereq=["ga:skill/file_search"],
    alternatives=["ga:skill/code_run_cat"],
)
def do_file_read(self, args, response): ...
```

#### 4.2 Act Agent 自动演化

借鉴 GH 的 AA (Act Agent) 设计：
- 每轮任务结束后，AA 分析执行轨迹
- 自动创建 KnowledgeFragment（失败模式记录）
- 更新技能的使用统计和信誉分

---

## 四、实施路线图

| 阶段 | 名称 | 文件变更 | 预估工时 | 收益 | 风险 |
|------|------|----------|----------|------|------|
| **P0** | 设计理念提取 | `tools/pdca/pdca_classifier.py` + ga.py prompt | **2h** | 任务执行质量提升 20% | 低（改 prompt 为主） |
| **P1** | JSON-LD 互操作 | `tools/jsonld/converter.py` + mempalace 增强 | **4h** | 数据语义化，为桥接铺路 | 低（新增模块） |
| **P2** | gRPC 桥接 | `tools/grpc_bridge/` + sop | **1-2d** | 白捡 PDCA 编排 + SPARQL 查询 | 中（依赖 GH 运行时） |
| **P3** | Skill Graph | tools 注册机制改造 + AA 演化 | **3d+** | 技能自进化，长期收益高 | 高（改造注册机制） |

---

## 五、立即可以做的（P0 详细设计）

### 5.1 `pdca_classifier.py` 接口设计

```python
class PDCAEngine:
    """PDCA 编排引擎 — 统一的任务复杂度鉴定 + 执行策略选择"""
    
    def classify(self, task: str, tools: list[str]) -> int:
        """返回 0-6 的复杂度级别"""
    
    def get_execution_strategy(self, level: int) -> dict:
        """返回当前级别的执行策略配置"""
    
    def get_prompt_instruction(self, level: int) -> str:
        """生成注入 Agent prompt 的 instruction 文本"""
```

### 5.2 ga.py 修改点

1. `_build_prompt()` 末尾：根据 PDCA 级别注入 instruction
2. `update_working_checkpoint()`：增加 5W2H 字段自动展开
3. `start_long_term_update()`：增加 AA 风格的任务执行分析

### 5.3 首次不引入新依赖

所有 P0 功能纯 Python 实现，零外部依赖。

---

## 六、不整合的部分（明确排除）

| GH 模块 | 排除原因 | 替代方案 |
|---------|----------|----------|
| Rust 原生编译 | 编译链复杂，维护成本高 | Python 原生实现核心逻辑 |
| Oxigraph RDF | 已有 knowledge_graph.py (OWL/TTL) | SPARQL 可通过 JSON-LD 桥接调用 |
| 数字签名 ed25519 | 单 Agent 场景不需要 | 未来多 Agent 再加 |
| tree-sitter AST | 已有 CodeGraph MCP | CodeGraph 更强大 |
| yaque 消息队列 | 已有 MQTT 生态 | MQTT 更适合 GA |

---

## 七、决策点

1. **P0 是否立即启动？** — 纯 prompt 改进，无代码风险
2. **P1 JSON-LD 是否要做完整？** — 如果不做 gRPC 桥接，JSON-LD 的收益有限
3. **P2 gRPC 桥接是否值得？** — 取决于 GH 项目活跃度和稳定性

---

*本方案基于 Gliding Horse Agent OS v0.1.0 (2026-06-10) 设计，随项目迭代更新。*
