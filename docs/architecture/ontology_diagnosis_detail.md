# 本体论模型与系统诊断 — 详细说明

> 日期: 2026-05-23 | 基于 GenericAgent_mqtt 项目实际代码和运行环境

---

## 一、本体模型概述

### 1.1 何为"本体"？

在本项目中，本体是**系统组件之间逻辑联系的正式描述**。它不是 UML 类图，也不是 ER 图——而是从**实际交互经验**中提取的、经过**执行验证**的知识体系。

### 1.2 四层结构

```
Layer 1: 实体 (Entities)
  系统中存在哪些组件？
  例: BoardService, Mosquitto, MariaDB, Agent, BoardClient...
  来源: 代码文件扫描 + 运行服务检测
  文件: tools/ontology_model.py → ENTITIES 列表 (17个)

Layer 2: 关系 (Relations)
  实体之间如何连接？
  例: BoardService --depends-on--> Mosquitto
       BoardClient --publishes-to--> BoardService
  来源: 从 100+ 轮交互中提取的已验证连接
  文件: tools/ontology_model.py → RELATIONS 列表 (16条)

Layer 3: 约束 (Constraints)
  成立的前提条件是什么？
  例: 密码文件不能有空行
       jwtencoded 必须 default-features=false
  来源: 从 30+ 次失败诊断中提取的教训
  文件: tools/ontology_model.py → CONSTRAINTS 列表 (9条)

Layer 4: 推理 (Inferences)
  从前提可以推出什么结论？
  例: 替换 BoardService → 吞吐量 42x 提升 (置信度 0.95)
       配置文件修改→服务未重启→新配置不生效 (置信度 0.99)
  来源: 从成功/失败经验中总结的因果规律
  文件: tools/ontology_model.py → INFERENCES 列表 (6条)
```

---

## 二、诊断系统架构

### 2.1 三组件协作

```
┌───────────────────┐     ┌───────────────────┐     ┌───────────────────┐
│  ontology_model   │     │  diagnosis_agent  │     │ reflection_engine │
│  (本体模型)       │────→│  (诊断服务)       │     │  (反省引擎)       │
│                   │     │                   │     │                   │
│  17 实体          │     │  1. 订阅真实数据   │     │  1. 扫描代码库    │
│  16 关系          │     │  2. 约束检查       │     │  2. 对比本体模型  │
│  9 约束           │     │  3. LLM 分析       │     │  3. 检测偏差      │
│  6 推理           │     │  4. 发布诊断帖子   │     │  4. 更新本体      │
└───────────────────┘     └────────┬──────────┘     └───────────────────┘
                                   │
                          ┌────────▼──────────┐
                          │   BBS 诊断板       │
                          │  board/diagnosis   │
                          │                   │
                          │  http://localhost  │
                          │  :8000/boards      │
                          │  /diagnosis        │
                          └───────────────────┘
```

### 2.2 数据流

```
真实系统 ──→ 诊断 Agent 采集 ──→ 约束检查 ──→ 诊断帖子 ──→ BBS 看板
     ↑                            │
     └── 反省引擎扫描 ←─────── 本体模型 ←──── 更新偏差
```

### 2.3 诊断帖子的格式

每一条诊断结果是一条标准 BBS 帖子，发布到 `board/diagnosis/`：

```json
{
  "type": "anomaly",           // anmaly / info / warning /
  "severity": "critical",      // critical / warning / info
  "source": "real_data",       // real_data / 3sigma / constraint / inference / llm / reflection
  "component": "BoardService", // 涉及组件
  "status": "degraded",        // healthy / degraded / down / inferred
  "detail": "BoardService healtheck: not_ready",
  "llm_analysis": "根因: MariaDB 连接池已满\n建议: 增大 max_connections",
  "evidence_count": 3,
  "timestamp": 1719050400.0
}
```

---

## 三、各文件详细说明

### 3.1 `tools/ontology_model.py`

核心本体模型，所有实体/关系/约束/推理的单一数据源。

**使用方式**:
```python
from tools.ontology_model import ENTITIES, RELATIONS, CONSTRAINTS, INFERENCES
from tools.ontology_model import query_relations, chain_inference

# 查询某实体的所有关系
for r in query_relations("BoardService"):
    print(f"{r.source} --{r.relation_type}--> {r.target}")

# 推理
results = chain_inference("替换")
for i in results:
    print(f"{i.premise} → {i.conclusion} (置信度{i.confidence})")
```

**扩展方式**:
```python
# 新增实体
ENTITIES.append(Component(
    name="NewModule",
    component_type="service",
    language="rust",
    status="active",
    location="tools/new_module",
    verified_interactions=0
))

# 新增约束
CONSTRAINTS.append(Constraint(
    description="新模块必须通过 test",
    severity="error",
    source="developer",
    fix="运行 cargo test",
    check_condition="test_exit_code == 0"
))
```

### 3.2 `tools/diagnosis_agent.py`

自主诊断服务，独立进程运行。

**启动方式**:
```bash
# 规则模式 (无 LLM)
python -m tools.diagnosis_agent

# LLM 增强模式
SKILL_LLM_ENABLE=1 LLM_API_KEY=sk-... python -m tools.diagnosis_agent
```

**诊断周期 (每 30 秒)**:
1. 采集 `system/healthcheck/+/response` 最新 120 条
2. 采集 `node/+/status` 全部节点状态
3. 采集 `events/+/error` 最近 50 条
4. 3σ 滑动窗口异常检测 (最近 10 个样本)
5. 约束检查 (CONSTRAINTS)
6. 推理规则 (INFERENCES)
7. LLM 根因分析 (如有可用)
8. 发布诊断帖子到 `board/diagnosis/post/`
9. 发布概览到 `board/diagnosis/summary` (retain)

**数据源订阅**:
| 主题 | 用途 | 更新频率 |
|------|------|---------|
| `system/healthcheck/+/response` | 服务状态 + 延迟 | 每次 BoardService 响应 |
| `node/+/status` | 节点在线/离线 | 状态变化时 |
| `events/+/error` | 错误事件 | 错误发生时 |

### 3.3 `tools/reflection_engine.py`

反省引擎，比对本体模型与实际系统的偏差。

**启动方式**:
```bash
# 一次反省
python -m tools.reflection_engine

# 持续监控 (等待自进化模式启用)
python -m tools.reflection_engine --watch
```

**反省周期内容**:
1. 扫描 `mqtt_bbs/*.py` 和 `tools/*_rs/src/**/*.rs`
2. 扫描运行服务 (tasklist + 端口检测)
3. 扫描 `skills_learning/` 目录
4. 对比本体模型的 17 实体 vs 实际 52+ 代码模块
5. 输出偏差报告: 新增/消失/变化
6. 自动更新 `ontology_model.py` 的实体列表

**偏差类型**:
| 类型 | 含义 | 示例 |
|------|------|------|
| `[新增]` | 代码中存在但模型未记录 | `file_transfer` 模块在代码中但不在 ENTITIES |
| `[消失]` | 模型中存在但代码未发现 | 概念实体 (如 `BoardService`) 因文件名不匹配被漏扫 |
| `[运行中]` | 实际在运行但模型未记录 | Gateway(HTTP) 和 BoardService(Rust) |
| `[知识]` | 已掌握的技能 | 40 个 skills_learning 技能 |
| `[活动]` | 文件大小/修改时间变化 | 活跃模块检测 |

---

## 四、已发现的偏差（反省引擎输出）

首次运行发现 **63 处偏差**，模型覆盖度约 27% (17/63+17)：

| 类别 | 数量 | 重点项 |
|------|------|--------|
| 代码存在→本体缺失 | 37 | `file_transfer`, `dag`, `whiteboard`, `bbs.py` 等核心模块未建模 |
| 本体存在→代码未扫 | 16 | 概念实体 (如 `BoardClient`) 被文件名精确匹配遗漏 |
| 服务运行→本体缺失 | 2 | Gateway(HTTP), BoardService(Rust) |
| 技能已掌握→本体缺失 | 40 | skills_learning 技能库未与本体关联 |

---

## 五、改进方向

### 近期 (下次迭代)

- **实体匹配优化**: 文件名 `board_service.py` 应匹配概念 `BoardService`（下划线→驼峰映射）
- **约束自动化**: `check_condition` 字符串 eval 改为可执行函数
- **技能关联**: skills_learning 的 40 个技能自动注册为 Agent 的知识本体

### 远期

- **自进化闭环**: 反省引擎检测偏差 → 自动更新本体 → 诊断 Agent 使用新本体 → 刷新诊断板
- **跨实例本体同步**: 多实例运行时，本体通过 `agent/ontology/` 主题 publish 自动同步
- **LLM 本体推理**: 用 LLM 分析代码变更，自动生成新的关系/约束/推理
