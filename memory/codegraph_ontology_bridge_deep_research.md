# CodeGraph + OWL Ontology 融合深研

> 研究方向: 将 CodeGraph 的代码级图分析与 OWL 本体推理双向映射，
> 使 GA 能同时理解代码结构和领域语义，统一入口完成供应链深度研究。

## 一、CodeGraph 能力全景

### 索引层
| 命令 | 功能 | 输出 |
|------|------|------|
| `init -i` | 初始化索引 | 自动扫描 + 构建图 |
| `index/sync` | 全量/增量索引 | 节点/边/文件 |
| `status` | 索引统计 | Files, Nodes, Edges |
| `files` | 文件列表 | 按语言分组 |

### 查询层
| 命令 | 功能 | 供应链类比 |
|------|------|-----------|
| `query <symbol>` | 搜索代码符号 | 搜索公司名 |
| `callers <symbol>` | 谁调用此函数 | 谁依赖此公司 |
| `callees <symbol>` | 此函数调用谁 | 此公司供应谁 |

### 分析层
| 命令 | 功能 | 供应链类比 |
|------|------|-----------|
| `impact <symbol>` | 变更影响分析 | 节点失效传导 |
| `affected` | 测试影响分析 | 风险波及范围 |

### 集成层
| 命令 | 功能 |
|------|------|
| `serve --mcp` | MCP 服务器模式 (stdio transport) |
| `install/uninstall` | 安装到 Claude Code/Cursor 等 |

## 二、OWL 本体能力全景

### TBox (模式层)
- **类**: Company, SupplyChainRelation, Risk, HighDependencyRisk
- **对象属性**: suppliesTo, purchasesFrom
- **数据属性**: hasRatio (xsd:float), hasRiskLevel (xsd:string)
- **约束**: domain/range, subclass, disjoint

### ABox (实例层)
- 公司实例: 宁德时代, 比亚迪, 当升科技...
- 关系实例: 当升科技 suppliesTo 宁德时代 (30%)
- 风险推理: ratio>25% → HighDependencyRisk 实例

### 推理能力
| 推理类型 | 功能 | 示例 |
|---------|------|------|
| RDFS | 子类继承 | HighDependencyRisk ⊆ Risk |
| DL | 一致性检查 | 同时上游+下游 → 不一致 |
| SWRL | 规则推理 | ratio>25%+客户→高风险 |
| SameAs | 等价合并 | "比亚迪" = "BYD" = "深圳比亚迪供应链" |

## 三、双向映射方案

### 映射 A: CodeGraph → OWL

```
CodeGraph 代码图              OWL 本体
─────────────────────        ─────────────────
import 边 (模块依赖)      →   dependsOn (概念依赖)
call 边 (函数调用)         →   invokes (操作调用)
class 节点                 →   Company (类实例)
method 节点                →   Relation (方法实例)
file 分组 (按目录)         →   DomainSector (领域分类)
```

**实现**: 从 CodeGraph SQLite DB 读取节点/边，转化为 OWL 三元组
```python
# CodeGraph DB → OWL ABox
cg_db = ".codegraph/codegraph.db"
rows = query("SELECT * FROM nodes JOIN edges ON nodes.id=edges.source")
for row in rows:
    owl_graph.add((NS[row.name], SC.suppliesTo, NS[row.target]))
```

### 映射 B: OWL → CodeGraph

```
OWL 推理结果                    CodeGraph
─────────────────────         ─────────────────
风险推理 (HighDependencyRisk) → 派生边 (derived edge)
间接依赖 (A→B→C)             → 额外边 (transitive edge)
等价关系 (sameAs)             → 别名标签 (alias tag)
一致性违规 (上游+下游)        → 警告标记 (warning marker)
```

**实现**: OWL 推理器输出 → 注入 CodeGraph 的额外边
```python
# OWL reasoner → CodeGraph derived edges
for risk in owl_infer():
    cg_graph.add_derived_edge(
        source=risk.company,
        target="HighRisk",
        type="derived",
        reason=f"ratio {risk.ratio}% > 25%"
    )
```

## 四、架构实现

```
┌─────────────────────────────────────────────────────────┐
│                   GA Agent (统一入口)                      │
│  "分析这个供应链代码变更的风险"                            │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┼──────────────┐
        ▼              ▼              ▼
┌──────────────┐ ┌──────────┐ ┌──────────────┐
│ CodeGraph    │ │ OWL      │ │ FastAPI      │
│ serve --mcp  │ │ reasoner │ │ REST API     │
│ (stdio MCP)  │ │ (RDFLib) │ │ (data CRUD)  │
└──────┬───────┘ └─────┬────┘ └──────┬───────┘
       │               │             │
       ▼               ▼             ▼
  ┌────────┐    ┌──────────┐   ┌──────────┐
  │ CG DB  │    │ OWL TTL  │   │ Neo4j    │
  │ (sqlite)│   │ (rdflib) │   │ (graph)  │
  └────────┘    └──────────┘   └──────────┘
```

### MCP 协议集成

CodeGraph 的 `serve --mcp` 模式通过 stdio 暴露 MCP 协议工具：
```
tools:
  - codegraph_query(symbol)
  - codegraph_callers(symbol)
  - codegraph_callees(symbol)
  - codegraph_impact(symbol)
  
添加 OWL 推理工具:
  - owl_reason(ontology_ttl)
  - owl_consistency_check(ontology_ttl)
  - owl_infer_risks(data_graph)
```

## 五、应用场景

### 场景 1: 供应链代码变更风险管理
1. 开发者修改某 API 端点
2. `codegraph impact endpoint_name` → 找出受影响的所有调用方
3. OWL 推理: 调用方映射为供应链公司，推断受影响的风险
4. 输出: "API 变更影响 3 家公司 (当升科技/恩捷股份/天赐材料)，风险等级: 中"

### 场景 2: 代码级供应链溯源
1. 用户问"宁德时代的数据从哪里来的"
2. `codegraph callers "CATL"` → 找到所有引用 CATL 的函数
3. OWL sameAs 推理: "CATL" ≡ "宁德时代" → 合并所有来源
4. 输出: 可视化 call graph + supply graph 叠加

### 场景 3: 本体驱动的代码生成
1. OWL 模型定义 SupplyRelation 模式 (source/target/ratio)
2. 导出为 JSON Schema → FastAPI Pydantic 模型自动生成
3. OWL 约束转化为 API 校验规则 (ratio ∈ [0,100])
4. 输出: 模型变更 → 代码自动适配

## 六、实施计划

### 短期 (30min)
- [ ] 启动 CodeGraph serve --mcp
- [ ] 用 OWL TTL 文件初始化推理器
- [ ] 测试 import → dependsOn 映射

### 中期 (2h)
- [ ] 建立 CG ↔ OWL 自动同步脚本
- [ ] 实现 MCP 扩展: owl_reason / owl_consistency_check
- [ ] 验证风险传导路径

### 长期 (4h)
- [ ] 变更联动管线: git commit → cg affected → owl reason → risk report
- [ ] CodeGraph derived edges 持久化
- [ ] 可视化: CG 图 + OWL 推理叠加显示
