# 本体 × 图数据库 × MQTT BBS — 三元协同架构

> 融合灵感#7(Palantir本体论×MQTT BBS) + skills_learning/ontology/rev4(16个本体知识模式) + 图数据库持久化语义层
>
> 核心命题：**如何让智能体协作系统同时具备"语义理解"、"持久记忆"和"实时响应"三种能力？**

---

## 0. 问题驱动

| 单一方案 | 短板 | 三元协同如何补足 |
|:--------:|:----:|:----------------:|
| 纯MQTT BBS | 消息无持久化关联查询能力，topic树难以表达复杂关系 | 图数据库补足：实体间多跳关系查询、历史追溯 |
| 纯本体(OWL/RDF) | 推理计算重，实时性差，Agent协作需额外通信机制 | MQTT BBS补足：事件驱动实时分发、pub/sub解耦 |
| 纯图数据库 | 被动查询，无主动通知机制 | MQTT BBS补足：变更订阅、Agent心跳、LWT离线检测 |
| skills_learning/本体 | 学到的模式固化在json中，无运行时动态应用 | 图数据库补足：模式作为图约束实时生效 |

---

## 1. 三元模型（Triad Model）

```
┌─────────────────────────────────────────────────────────┐
│                  应用层 (飞书Bot / WebUI / CLI)          │
└──────────────────────┬──────────────────────────────────┘
                       │
┌──────────────────────▼──────────────────────────────────┐
│              语义协作层 (Semantic Collaboration)          │
│                                                          │
│  ┌─────────────────┐  ┌──────────────┐  ┌────────────┐ │
│  │   本体层         │  │  图数据库层   │  │ MQTT BBS层 │ │
│  │  (What things    │  │ (How stored  │  │ (How comm) │ │
│  │   mean)          │  │  & queried)  │  │            │ │
│  │                  │  │              │  │            │ │
│  │  • OWL/RDF模式   │  │ • Neo4j/     │  │ • 主题树   │ │
│  │  • 类层次/属性   │  │   ArangoDB   │  │ • pub/sub  │ │
│  │  • 关系约束      │  │ • 节点/边    │  │ • Retain   │ │
│  │  • 推理规则      │  │ • 多跳查询   │  │ • LWT/心跳 │ │
│  │  • 命名空间      │  │ • 全文索引   │  │ • QoS 2    │ │
│  └────────┬─────────┘  └──────┬───────┘  └──────┬─────┘ │
│           │                   │                  │       │
│           └───────────────────┴──────────────────┘       │
│                         │ 三元桥接层                      │
│              (Schema↔Graph↔Topic 三重映射)               │
└──────────────────────────┬───────────────────────────────┘
                           │
┌──────────────────────────▼───────────────────────────────┐
│           数据/执行层 (Data Sources / Workers)             │
│   Agent  │  API  │  DB  │  ERP  │  CRM  │  MES          │
└──────────────────────────────────────────────────────────┘
```

### 每层的核心职责

| 层 | 核心模型 | 存储形态 | 查询方式 | 更新方式 |
|:--:|:--------:|:--------:|:--------:|:--------:|
| **本体层** | 类(Class)、属性(Property)、关系(Relation)、约束(Constraint) | OWL/RDF Schema (可存于图DB) | 描述逻辑推理 | skills_learning持续学习+人工精调 |
| **图数据库层** | 节点(Node)、边(Edge)、属性(Property)、标签(Label) | 原生图存储 (邻接表) | Cypher/SPARQL/Gremlin | MQTT事件驱动同步 |
| **MQTT BBS层** | 主题(Topic)、消息(Message)、Retain、QoS | 内存+持久化(消息) | 主题匹配+语义路由 | Pub/Sub实时推送 |

---

## 2. 三重映射：实体在三层中的统一表示

一个业务实体（如飞机 A001）在三层中各有投影，但通过**实体ID**保持一致性：

### 2.1 飞机 A001 的三层投影

```yaml
# ── 实体ID: aircraft:A001 (全局唯一) ──

### 本体层投影 ###
Class: Aircraft
SuperClass: Vehicle → Asset
Properties:
  - registration: string        # 注册号
  - model: string               # 型号 (约束: 必须在 AircraftModel 枚举中)
  - status: {PARKED, FLYING, MAINTENANCE, DELAYED}
  - max_range: integer          # 最大航程(km)
  - capacity: integer           # 座位数
Relations:
  - located_at -> Airport       # 当前所在机场 (1:1)
  - assigned_to -> Flight       # 当前执飞航班 (0:1)
  - maintained_by -> Team       # 维护团队 (n:1)
  - has_part -> Part            # 包含部件 (1:n)
Constraints:
  - status=FLYING → assigned_to 必须存在
  - model=321neo → max_range=6500, capacity=195

### 图数据库层投影 ###
Node: aircraft:A001
Labels: ["Aircraft", "Vehicle", "Asset"]
Properties:
  registration: "B-1234"
  model: "321neo"
  status: "PARKED"
  max_range: 6500
  capacity: 195
Edges:
  - [aircraft:A001] -[:LOCATED_AT]-> [airport:PEK]
  - [aircraft:A001] -[:MAINTAINED_BY]-> [team:MRO_3]
  - [aircraft:A001] -[:HAS_PART]-> [part:ENGINE_01]
  - [aircraft:A001] -[:HAS_PART]-> [part:ENGINE_02]

### MQTT BBS层投影 ###
主题树:
  ontology/entities/aircraft/A001/
    +-- status            # [Retain] "PARKED"
    +-- properties        # [Retain] {"registration": "B-1234", "model": "321neo"}
    +-- relations/
    |   +-- located_at    # [Retain] {"target": "airport:PEK", "type": "LOCATED_AT"}
    |   +-- maintained_by # [Retain] {"target": "team:MRO_3", "type": "MAINTAINED_BY"}
    +-- events/           # 事件流（非Retain）
    |   +-- status_change # {"from": "FLYING", "to": "PARKED", "ts": "..."}
    +-- actions/          # 行动入口
        +-- request       # 向该实体发送操作请求
```

### 2.2 三层之间的数据流

```
状态变更事件流（例：A001 降落 → status=FLYING → PARKED）

  传感器/ADS-B
      │
      ├──→ MQTT: ontology/entities/aircraft/A001/events/status_change
      │       payload: {"from":"FLYING", "to":"PARKED", "ts":"2026-05-18T15:30:00Z"}
      │
      ├──→ MQTT Bridge (三元桥接器)
      │       │
      │       ├──→ 图数据库: MATCH (a:Aircraft {id:"A001"}) SET a.status="PARKED"
      │       │            CREATE (a)-[:HAS_EVENT {type:"landing", ts:"..."}]->(e:Event)
      │       │
      │       └──→ 本体推理引擎: 检查约束 → 通知相关Agent
      │               • 维护Agent: 检查是否需要例行维护（根据飞行小时数）
      │               • 调度Agent: 检查下一航班是否受影响
      │
      └──→ Agent Board (MQTT BBS)
              • 新状态通过Retain消息持久化
              • Worker Agent 按capability订阅 → 触发后续任务
```

---

## 3. 三元桥接器（Triad Bridge）设计

桥接器是三层之间的"翻译官"，负责三类转换：

### 3.1 Ontology → Graph DB (Schema同步)

```python
# 伪代码：本体模式 → 图数据库约束
class OntologyToGraphBridge:
    def sync_schema(self, ontology_schema: dict):
        """将OWL类层次映射为图DB标签和约束"""
        for cls in ontology_schema['classes']:
            # 类 → 标签
            graph_db.create_label(cls.name, super_labels=cls.parents)
            # 数据属性 → 节点属性约束
            for prop in cls.data_properties:
                graph_db.add_property_constraint(cls.name, prop.name, prop.type)
            # 对象属性 → 边类型
            for rel in cls.object_properties:
                graph_db.create_edge_type(rel.name, rel.domain, rel.range)
            # 约束 → 图DB的assertion/trigger
            for constraint in cls.constraints:
                graph_db.add_assertion(constraint.expression)
```

### 3.2 MQTT BBS → Graph DB (事件同步)

```python
class MqttToGraphBridge:
    """MQTT消息 → 图数据库写入"""
    
    ROUTING = {
        'ontology/entities/+/+/status': {
            'action': 'update_node_property',
            'extract': lambda topic, payload: {
                'type': topic.split('/')[2],    # aircraft
                'id': topic.split('/')[3],       # A001
                'property': 'status',
                'value': payload
            }
        },
        'ontology/entities/+/+/events/+': {
            'action': 'create_event_edge',
            'extract': lambda topic, payload: {
                'source_type': topic.split('/')[2],
                'source_id': topic.split('/')[3],
                'event_type': topic.split('/')[5],
                'payload': json.loads(payload)
            }
        },
        'ontology/actions/+/request': {
            'action': 'create_action_node',
            'extract': lambda topic, payload: {...}
        }
    }
    
    def on_message(self, topic, payload):
        route = self.match_topic(topic)
        if route:
            data = route['extract'](topic, payload)
            getattr(self, route['action'])(data)
```

### 3.3 Graph DB → MQTT BBS (查询结果推送)

```python
class GraphToMqttBridge:
    """图数据库查询结果 → MQTT主题发布"""
    
    def query_and_publish(self, query: str, response_topic: str):
        """执行Cypher查询，结果发布到MQTT"""
        result = graph_db.run(query)
        mqtt.publish(response_topic, json.dumps(result), retain=False, qos=2)
    
    # ── 典型查询模板 ──
    
    def find_affected_entities(self, entity_id: str, depth: int = 2):
        """发现某实体变更影响的关联实体（多跳查询）"""
        query = f"""
        MATCH (e {{id: '{entity_id}'}})-[*1..{depth}]-(affected)
        RETURN affected.id, affected.type, 
               labels(affected) as types,
               relationships(e) as connections
        """
        return self.query_and_publish(query, f"ontology/query/{entity_id}/affected")
    
    def find_capable_agents(self, task_type: str, location: str):
        """基于关系网络查找有能力且就近的Agent"""
        query = f"""
        MATCH (a:Agent {{capability: '{task_type}'}})
        WHERE a.location = '{location}' OR a.is_remote = true
        RETURN a.id, a.status, a.load
        ORDER BY a.load ASC
        LIMIT 3
        """
        return self.query_and_publish(query, f"agent/board/task/dispatch/candidates")
    
    def trace_entity_lifecycle(self, entity_id: str):
        """追溯实体的全生命周期"""
        query = f"""
        MATCH (e {{id: '{entity_id}'}})-[:HAS_EVENT]->(evt:Event)
        RETURN evt.type, evt.ts, evt.detail
        ORDER BY evt.ts DESC
        """
        return self.query_and_publish(query, f"ontology/trace/{entity_id}")
```

---

## 4. 基于关系网络的语义路由（超越Topic匹配）

### 4.1 传统MQTT路由 vs 图增强语义路由

```
传统MQTT路由:
  topic: agent/task/repair
  Worker订阅 → 收到所有维修任务 → 自己判断能不能做

图增强语义路由:
  1. 任务发布: ontology/actions/repair/request
     payload: {object: "aircraft:A001", fault: "engine_vibration"}
  
  2. 三元桥接器收到 → 查询图数据库:
     MATCH (a:Aircraft {id:"A001"})-[:MAINTAINED_BY]->(t:Team)<-[:MEMBER_OF]-(w:Worker)
     WHERE w.capabilities CONTAINS "engine"
     AND w.status = "idle"
     RETURN w.id, w.skill_level
     ORDER BY w.skill_level DESC
  
  3. 桥接器 → 发布到特定Worker的专属主题:
     agent/node/worker_alpha/task/incoming
     payload: {task_id: "...", priority: "high", ...}
  
  4. 而不是广播给所有Worker
```

### 4.2 语义路由矩阵

| 条件维度 | 来源 | 示例 |
|:--------:|:----:|:----:|
| **实体类型** | 本体层Class定义 | 只有 Aircraft → MRO Agent |
| **地理位置** | 图数据库关系查询 | located_at=PEK → 北京团队 |
| **能力匹配** | 图数据库属性索引 | capabilities CONTAINS "engine" |
| **历史经验** | 图数据库事件追溯 | 曾维修过同型号 → 优先 |
| **当前负载** | MQTT BBS node status | load < 3 的Worker |
| **信任等级** | 本体层认证属性 | cert_level >= 2 |

> **核心变化**: 从"发布-订阅"的广播模型，升级为"发布-查询-定向投递"的语义路由模型。

---

## 5. Skills Learning 作为本体进化引擎

### 5.1 学习→应用闭环

```
skills_learning/ontology 学习新知识模式
         │
         ▼
    新模式转化为本体层Schema更新
         │
         ▼
    三元桥接器同步到图数据库约束
         │
         ▼
    通过MQTT BBS广播给所有Agent:
    ontology/meta/schema/update
         │
         ▼
    Agent按需更新自身行为模式
         │
         ▼
    运行时新数据验证新模式有效性
         │
         ▼ (反馈)
    再次触发skills_learning迭代
```

### 5.2 从16个知识模式中提取的图DB映射

| knowledge_ patterns 中的模式 | 图数据库映射 | MQTT BBS映射 |
|:---------------------------:|:-----------:|:------------:|
| **本体设计原则与最佳实践** (95%) | 图DB标签命名规范、索引策略 | topic命名规范一致 |
| **RDF/OWL语言** (85%) | 节点=资源, 边=谓词, 属性=字面量 | topic=URI, payload=序列化三元组 |
| **关系相关技术** (77%) | 边类型设计、多跳查询优化 | 关系变更事件发布 |
| **知识图谱** (77%) | 实体消歧、图融合、Neo4j/ArangoDB选型 | 图谱变更订阅 |
| **本体评估与维护** (87%) | 图一致性检查、数据质量监控 | schema版本管理主题 |
| **特定领域本体** (89%) | 为领域定制图模式（金融/工程/医疗） | 领域专属topic树 |

### 5.3 模式版本化与演进

```yaml
# ontology/meta/schema/version  [Retain消息]
current_version: "v1.2.0"
history:
  - version: "v1.0.0"
    changes: ["初始本体模式"]
    timestamp: "2026-05-01"
  - version: "v1.1.0"
    changes: ["新增Aircraft类", "新增LOCATED_AT关系"]
    source: "skills_learning/ontology/rev3"
    timestamp: "2026-05-10"
  - version: "v1.2.0"
    changes: ["新增约束: status=FLYING必须有assigned_to", "新增HAS_EVENT事件边"]
    source: "skills_learning/ontology/rev4 + 实践经验"
    timestamp: "2026-05-18"
```

---

## 6. 图数据库选型与集成方案

### 6.1 候选方案对比

| 方案 | 适合场景 | 集成难度 | 推理能力 | 与MQTT集成 |
|:----:|:--------:|:--------:|:--------:|:----------:|
| **Neo4j** (嵌入式+APOC) | 复杂关系查询、图算法 | 中 | OWL 2 RL级(需插件) | MQTT→Neo4j Trigger via APOC |
| **ArangoDB** (多模型) | 文档+图混合场景 | 中 | 内置 | Foxx微服务作为BBS Bridge |
| **RDFox** (内存推理) | 高吞吐推理、实时更新 | 高 | OWL 2 DL全支持 | 原生RDF+MQTT双写 |
| **SQLite + RDF视图** (轻量) | 原型验证、嵌入式 | 低 | 无 | 最简单集成 |
| **RedisGraph** (内存图) | 低延迟查询、缓存层 | 低 | 有限 | 内存性能优势 |

### 6.2 推荐方案：Neo4j + APOC + MQTT 插件

```
┌──────────────────────────────────────┐
│              MQTT Broker              │
│   (RMQTT v0.20.0)                    │
└──────────┬───────────────────────────┘
           │ MQTT Subscribe (桥接器)
           ▼
┌──────────────────────────────────────┐
│     MQTT→Neo4j Bridge (Python)       │
│                                      │
│  1. 订阅 ontology/entities/#         │
│  2. 解析payload → Cypher MERGE      │
│  3. 执行触发的事件处理链             │
│  4. 查询结果 → 发布回MQTT            │
└──────────────────────────────────────┘
           │ Bolt协议
           ▼
┌──────────────────────────────────────┐
│           Neo4j 图数据库              │
│                                      │
│  • 本体Schema图 (标签/关系类型定义)  │
│  • 实体实例图 (节点/边)             │
│  • 事件历史图 (时间线)               │
│  • Agent能力图谱                     │
│                                      │
│  插件: APOC (过程库)                 │
│        Graph Algorithms (路径分析)   │
│        全文索引 (FTS)                │
└──────────────────────────────────────┘
```

### 6.3 关键Cypher查询模板

```cypher
// ── 1. 实体的完整关系网络（多跳查询）──
MATCH (a:Aircraft {id: "A001"})-[*1..3]-(connected)
RETURN a, connected,
       relationships(a) AS direct_rels
LIMIT 100

// ── 2. 基于关系的任务分配 ──
MATCH (a:Aircraft {id: "A001"})-[:MAINTAINED_BY]->(t:Team)
MATCH (t)<-[:MEMBER_OF]-(w:Worker)
WHERE w.status = "idle" AND w.capabilities CONTAINS $fault_type
RETURN w.id, w.skill_level
ORDER BY w.skill_level DESC
LIMIT 1

// ── 3. 事件链追溯 ──
MATCH (a:Aircraft {id: "A001"})-[:HAS_EVENT]->(e:Event)
WHERE e.ts >= datetime() - duration('P7D')
RETURN e.type, e.ts, e.detail
ORDER BY e.ts DESC

// ── 4. 相似实体发现 ──
MATCH (a:Aircraft {model: "321neo"})
MATCH (a)-[:LOCATED_AT]->(ap:Airport)
MATCH (ap)<-[:LOCATED_AT]-(similar:Aircraft)
WHERE similar.id <> a.id
RETURN similar.id, similar.status, 
       ap.name AS location
```

---

## 7. 完整工作流示例：飞机故障处理

```
场景: A001 报告发动机振动异常

步骤 1: 传感器 → MQTT (事件检测)
  PUB ontology/entities/aircraft/A001/events/fault
  payload: {"type":"engine_vibration", "severity":4, "ts":"2026-05-18T15:30:00Z"}

步骤 2: MQTT Bridge → 图数据库 (关系查询)
  MATCH (a:Aircraft {id:"A001"})-[:MAINTAINED_BY]->(t:Team)
  MATCH (t)<-[:MEMBER_OF]-(w:Worker {specialty:"engine"})
  RETURN w.id, w.status
  
  结果: ["worker_alpha"(idle), "worker_beta"(busy)]

步骤 3: 桥接器 → MQTT BBS (定向派发)
  PUB agent/node/worker_alpha/task/incoming
  payload: {
    "task_id": "fault_A001_001",
    "type": "diagnose",
    "object": "aircraft:A001",
    "fault": "engine_vibration",
    "context_topic": "ontology/entities/aircraft/A001/#"
  }

步骤 4: Worker Alpha 执行诊断
  SUB ontology/entities/aircraft/A001/properties
  → 获取飞机型号、机龄、维修历史
  
  查询图数据库:
  MATCH (a:Aircraft {id:"A001"})-[r:HAS_PART]->(p:Part)
  WHERE p.type = "engine"
  RETURN p.id, p.hours_since_overhaul
  
  结果: 左发距离大修还有200小时，右发已超期50小时

步骤 5: Worker Alpha → MQTT (诊断结果)
  PUB agent/board/task/fault_A001_001/output
  payload: {
    "diagnosis": "右发轴承磨损",
    "severity": "critical",
    "recommendation": "更换右发",
    "estimated_downtime": "4h"
  }

步骤 6: 三元桥接器 → 图数据库 (知识沉淀)
  // 创建故障事件
  CREATE (e:Event {type:"fault", ts:"...", detail:"engine_vibration"})
  MATCH (a:Aircraft {id:"A001"})
  CREATE (a)-[:HAS_EVENT]->(e)
  
  // 创建诊断经验（后续可被skills_learning学习）
  CREATE (p:Pattern {type:"fault_diagnosis", engine_type:"321neo"})
  SET p.description = "engine_vibration → bearing_wear"
  MATCH (a:Aircraft {id:"A001"})
  CREATE (p)-[:APPLIES_TO]->(a)

步骤 7: 闭环 → 本体进化
  该故障案例 → skills_learning 下次学习时纳入
  → 形成新的知识模式: "engine_vibration模式识别"
  → 更新本体层: Aircraft类新增 vibration_threshold 属性
  → 通过MQTT广播新模式: ontology/meta/schema/update
```

---

## 8. 架构收益与风险

### 收益

| 维度 | 纯MQTT BBS | + 本体层 | + 图数据库 | 三元协同 |
|:----:|:----------:|:--------:|:----------:|:--------:|
| 语义表达 | 弱 (topic字符串) | 强 (OWL类层次) | 中 (图标签) | **极强** |
| 关系查询 | 需全量扫描topic | 仅推理 | 多跳毫秒级 | **多模式** |
| 实时性 | 高 (Pub/Sub) | 低 (推理计算) | 中 (索引查询) | **分层平衡** |
| 持久化 | Retain有限 | RDF Store | 原生持久化 | **互补** |
| 学习进化 | 人工加topic | Skills Learning | 图模式更新 | **全链路** |
| Agent协作 | 广播+认领 | 语义匹配 | 关系发现 | **精准路由** |

### 风险与缓解

| 风险 | 级别 | 缓解措施 |
|:----:|:----:|:--------:|
| 架构复杂度增加 | 中 | 分阶段实施: MQTT→图DB桥接先做，本体推理后加 |
| 图DB与MQTT数据一致性 | 中 | 以MQTT消息为"source of truth"，图DB为物化视图；定期全量同步 |
| 本体推理性能 | 低 | 离线推理，推理结果缓存到图DB；在线仅用图查询 |
| 学习模式质量 | 中 | skills_learning的验证阶段(assess.py)确保模式>70%可信度才发布 |

---

## 9. 实施路线图

```
Phase 1 (1-2天): MQTT→轻量图DB桥接
  • 选用 SQLite + RDF视图 或 轻量Neo4j Embedded
  • 实现 MqttToGraphBridge: 订阅 ontology/entities/# → 写入图DB
  • 实现 GraphToMqttBridge: 图查询 → MQTT发布
  • 验证: A001飞机状态变更 → 图DB同步 → 查询

Phase 2 (2-3天): 本体Schema同步
  • 将 skills_learning/ontology/rev4 的16个模式 → 图DB标签/约束
  • 实现 OntologyToGraphBridge.sync_schema()
  • 实现 schema版本管理 (ontology/meta/schema/#)
  • 验证: 新类定义 → 自动创建图DB标签 + 属性约束

Phase 3 (3-5天): 语义路由 + 完整工作流
  • 实现基于图查询的Agent分配 (替代广播-认领)
  • 实现事件链追溯 (完整生命周期)
  • 集成 skills_learning 反馈循环
  • 验证: 完整故障处理工作流 (传感器→MQTT→图查询→派发→处理→沉淀)

Phase 4 (持续): 本体进化闭环
  • 自动从运行时数据提取学习案例
  • 定期触发 skills_learning 迭代新rev
  • 新模式自动部署到图DB + MQTT广播
```

---

## 10. 与现有系统的集成点

| 现有组件 | 在此架构中的角色 | 需要修改 |
|:--------:|:---------------:|:--------:|
| **RMQTT Broker** | 通信总线 | 无需修改 |
| **MQTT BBS** (bbs*.py) | Agent协作框架 | 扩展语义路由钩子 |
| **飞书Bot** (fsapp.py) | 用户入口 | 新增本体查询命令 |
| **skills_learning** | 知识进化引擎 | 新增图DB模式输出 |
| **inspiration_board** | 灵感管理 | 元认知层，无需修改 |
| **本体论 README** (docs/ontology_mqtt/) | 本文档前置阅读 | 本文为扩展 |

---

> **文档版本**: v1.0 | **创建**: 2026-05-18
> **来源**: inspiration#7 + skills_learning/ontology/rev4 + MQTT BBS架构 + 图数据库设计模式
> **三句总结**:
> 1. **本体层**告诉系统"世界是什么样"（语义蓝图）
> 2. **图数据库**让系统"记住并推理关系"（持久化+查询）
> 3. **MQTT BBS**让所有组件"实时协作"（事件驱动通信）
