# neograph_review 本体论建模 — 实现构想与方案

> 基于现有: Neo4j图数据库 + MariaDB + MySQL
> 范围: 环形网络分析，不考虑与贷款系统兼容
> 日期: 2026-05-25

---

## 目录

1. [总体架构](#1-总体架构)
2. [数据源与输入](#2-数据源与输入)
3. [本体模型设计](#3-本体模型设计)
4. [推理与分析](#4-推理与分析)
5. [输出与呈现](#5-输出与呈现)
6. [实施路线图](#6-实施路线图)

---

## 1. 总体架构

### 1.1 架构概览

```
┌──────────────┐  ┌──────────────┐  ┌──────────────┐
│   Neo4j       │  │   MariaDB     │  │   MySQL      │
│   图数据库    │  │  heilongjiang │  │credit_finger│
│   bolt:7687  │  │  127.0.0.1    │  │ 10.46.8.202  │
├──────────────┤  ├──────────────┤  ├──────────────┤
│ Client       │  │ orders_data  │  │ loan_orders  │
│ Address      │  │ credential_img│  │ customers   │
│ License      │  │ (class_label) │  │ applications │
│ User/QRCode  │  │               │  │              │
│ (图拓扑+标记) │  │ (风险标签)    │  │ (业务详情)   │
└──────┬───────┘  └──────┬───────┘  └──────┬───────┘
       │                 │                 │
       │     ┌───────────┴───────────┐     │
       │     │                       │     │
       ▼     ▼                       ▼     ▼
┌─────────────────────────────────────────────────────┐
│            本体推理引擎 (Python)                      │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  TBOX: 本体模式定义                           │   │
│  │  ┌──────────┐ ┌──────────┐ ┌──────────┐   │   │
│  │  │ 节点类    │ │ 关系属性  │ │ 派生类   │   │   │
│  │  │ Client   │ │hasAddress│ │HighRisk  │   │   │
│  │  │ Address  │ │hasLicense│ │Ring      │   │   │
│  │  │ License  │ │ isSpouse │ │Connector │   │   │
│  │  │ User     │ │isManaged │ │Node      │   │   │
│  │  └──────────┘ └──────────┘ └──────────┘   │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  推理规则 (SWRL风格)                        │   │
│  │  Rule1: 地址共享xN → 隐藏网络               │   │
│  │  Rule2: 环+正标签 → 高风险环                │   │
│  │  Rule3: AD环桥+多标签 → 地址风险桥梁        │   │
│  └─────────────────────────────────────────────┘   │
│                                                     │
│  ┌─────────────────────────────────────────────┐   │
│  │  SPARQL风格查询                             │   │
│  │  环形拓扑查询 / 桥接节点排名 / 风险分类     │   │
│  └─────────────────────────────────────────────┘   │
└─────────────────────────┬───────────────────────────┘
                          │
                          ▼
       ┌─────────────────────────────────────┐
       │         输出层                       │
       ├─────────────────────────────────────┤
       │  API服务: 本体查询 + 推理结果        │
       │  Dashboard: 环形拓扑 + 风险热力图    │
       │  报表: 风险分类 + 桥接节点排名      │
       │  告警: 高风险环检测 → 推送           │
       └─────────────────────────────────────┘
```

### 1.2 关键技术决策

| 决策点 | 选择 | 理由 |
|:---|:---|:---|
| 本体存储 | **内置Python引擎**（非GraphDB） | 不引入新数据库，直接读Neo4j |
| 推理方式 | **Python规则引擎**（SHACL/SWRL风格） | 轻量，与现有Python脚本栈一致 |
| 数据同步 | **实查询**（不复制数据） | 三数据库已就绪，ETL增加复杂度 |
| 接口协议 | **FastAPI REST** | 与已有项目一致，便于集成Dashboard |
| 呈现层 | **Vue3 + Cytoscape.js** | 图可视化最适配环形网络拓扑 |

---

## 2. 数据源与输入

### 2.1 三数据库输入总览

```
┌────────────────────────────────────────────────────────────────────┐
│                        本体模型的输入                               │
│                                                                   │
│  Neo4j (图拓扑)      MariaDB (风险标签)     MySQL (业务详情)       │
│  ─────────────       ─────────────────     ─────────────────       │
│  节点:               orders_data表:        credit_finger_bank:    │
│    7,391 Client      order_id (PK)         loan_order表           │
│    4,681 Address     class_label(0/1/2)     order_id              │
│    等                302唯一订单            applicant_id            │
│                                             product_type           │
│  边:                 credential_image表:    loan_amount             │
│    8,060条          order_id (FK)           apply_date              │
│    HAS_ADDRESS       image_url                                     │
│    HAS_LICENSE       image_type             customer表              │
│    SPOUSE_OF         upload_time             applicant_id           │
│    MANAGER_OF                              name                     │
│    CLIENT_OF                               id_card                 │
│                                            phone                   │
│  节点属性:                                 industry                 │
│    node_id                                                          │
│    if_hidden_net                                                   │
│    times_in_blacknet                                               │
│    banks_ids                                                        │
│    had_been_single                                                  │
│                                                                   │
│  环检测结果(JSON):    class_label分布:                              │
│    176条环形路径      48正标签(7.7%)       (可后续扩展)             │
│    155个涉及客户      573零标签(92.3%)                              │
│    75个组合子图                                                     │
│    296个连接节点                                                   │
└────────────────────────────────────────────────────────────────────┘
```

### 2.2 各数据库的实体与字段映射

#### Neo4j — 图结构本体映射

| Neo4j标签 | 本体类 | 关键属性 → 数据属性 | 说明 |
|:---|:---|:---|---:|
| `Client` | `:Client` | `node_id` / `if_hidden_net` / `times_in_blacknet` / `banks_ids` | 申请人节点 |
| `Address` | `:Address` | `node_id` / `if_hidden_net` | 地址瓦片节点 |
| `License` | `:License` | `node_id` / `if_hidden_net` | 营业执照节点 |
| `User` | `:User` | `node_id` / `if_hidden_net` | 客户经理节点(行为实体) |
| `QRCode` | `:QRCode` | `node_id` / `if_hidden_net` | 二维码节点 |

| Neo4j关系 | 本体对象属性 | 定义域→值域 | 边属性 |
|:---|:---|:---|---:|
| `HAS_ADDRESS` | `:hasAddress` | Client→Address | `order_id` |
| `HAS_LICENSE` | `:hasLicense` | Client→License | `order_id` |
| `SPOUSE_OF` | `:isSpouseOf` | Client↔Client (对称) | `order_id` |
| `MANAGER_OF` | `:isManagerOf` | User↔Client | `order_id` |
| `CLIENT_OF` | `:isClientOf` | Client↔User | `order_id` |

#### MariaDB(heilongjiang) — 风险标签映射

| MariaDB字段 | 本体数据属性 | 值域 | 说明 |
|:---|:---|:---:|:---|
| `order_id` | `:hasOrderId` | xsd:string | 订单号(与图边关联) |
| `class_label` | `:hasRiskLabel` | xsd:integer | 0=正常, 1=轻度, 2=严重 |
| `image_url` | `:hasCredentialImage` | xsd:string | 凭证图片URL |

#### MySQL(credit_finger_bank) — 业务详情映射

| MySQL字段 | 本体数据属性 | 值域 | 说明 |
|:---|:---|:---:|:---|
| `order_id` | `:hasOrderId` | xsd:string | 订单号 |
| `applicant_id` | `:hasApplicantId` | xsd:string | 申请人ID |
| `product_type` | `:hasProductType` | xsd:string | 贷款产品类型 |
| `loan_amount` | `:hasLoanAmount` | xsd:decimal | 贷款金额 |
| `apply_date` | `:hasApplyDate` | xsd:dateTime | 申请日期 |
| `name` | `:hasName` | xsd:string | 客户姓名 |
| `industry` | `:hasIndustry` | xsd:string | 行业 |

---

## 3. 本体模型设计

### 3.1 TBOX — 类层次结构

```
:GraphEntity                (图实体 - 根类)
  ├── :NodeEntity           (节点实体)
  │   ├── :Client           (贷款申请人)
  │   ├── :Address          (地址瓦片)
  │   ├── :License          (营业执照)
  │   ├── :User             (客户经理) ← 行为实体
  │   └── :QRCode           (二维码)
  │
  ├── :RingEntity           (环形实体 - 派生)
  │   ├── :CircularPath     (环形路径)
  │   ├── :CombinedSubgraph (组合子图)
  │   └── :ConnectorNode    (桥接节点)
  │
  └── :OrderEntity          (订单实体)
      ├── :LoanOrder        (贷款订单)
      └── :RiskLabel        (风险标签)

:BehaviorEntity             (行为实体 - 根类)
  ├── :User                 (客户经理 - 也可作为行为实体)
  └── :ReviewAction         (审查动作 - 可扩展)
```

### 3.2 对象属性

| 属性 | 定义域 | 值域 | 特性 |
|:---|:---|:---|:---|
| `:hasAddress` | Client | Address | 多值 |
| `:hasLicense` | Client | License | 多值 |
| `:isSpouseOf` | Client | Client | `对称`、`传递`? |
| `:isManagerOf` | User | Client | 多值 |
| `:isClientOf` | Client | User | 多值 |
| `:hasOrder` | NodeEntity | LoanOrder | 通过边订单号关联 |
| `:hasRiskLabel` | LoanOrder | RiskLabel | 函数属性(1对1) |
| `:inRing` | NodeEntity | CircularPath | 属于某个环 |
| `:connects` | ConnectorNode | CircularPath | 桥接节点连接多个环 |
| `:hasCredential` | LoanOrder | xsd:string | 凭证图片URL |

### 3.3 SWRL风格推理规则

```
# ──── R1: 地址共享检测(替代Cypher条件1) ────
Client(?c1) ∧ Client(?c2) ∧ hasAddress(?c1, ?addr) ∧ 
hasAddress(?c2, ?addr) ∧ swrlb:differentFrom(?c1, ?c2)
→ Address(?addr) ∧ isHiddenNetwork(?addr, true)

# ──── R2: 执照共享检测(替代Cypher条件2) ────
Client(?c1) ∧ Client(?c2) ∧ hasLicense(?c1, ?lic) ∧ 
hasLicense(?c2, ?lic) ∧ swrlb:differentFrom(?c1, ?c2)
→ License(?lic) ∧ isHiddenNetwork(?lic, true)

# ──── R3: 多配偶关联(替代Cypher条件3+4) ────
Client(?c) ∧ isSpouseOf(?c, ?s1) ∧ isSpouseOf(?c, ?s2) ∧
swrlb:differentFrom(?s1, ?s2)
→ Client(?c) ∧ isHiddenNetwork(?c, true)

# ──── R4: 多银行检测(替代Cypher条件8) ────
Client(?c) ∧ bankCount(?c, ?cnt) ∧ swrlb:greaterThan(?cnt, 1)
→ Client(?c) ∧ isHiddenNetwork(?c, true)

# ──── R5: 高风险环定义 ────
CircularPath(?ring) ∧ hasNode(?ring, ?node) ∧ 
hasOrder(?node, ?order) ∧ hasRiskLabel(?order, ?label) ∧
swrlb:greaterThan(?label, 0)
→ HighRiskRing(?ring)

# ──── R6: 地址风险桥梁定义 ────
Address(?addr) ∧ isHiddenNetwork(?addr, true) ∧
connects(?addr, ?ring1) ∧ connects(?addr, ?ring2) ∧
swrlb:differentFrom(?ring1, ?ring2) ∧
HighRiskRing(?ring1)
→ AddressRiskBridge(?addr)

# ──── R7: 桥接节点风险浓度推理 ────
ConnectorNode(?node) ∧ hasConnectedOrders(?node, ?total) ∧
hasPositiveOrders(?node, ?pos) ∧
swrlb:divide(?ratio, ?pos, ?total) ∧
swrlb:greaterThan(?ratio, 0.3)
→ HighRiskConnector(?node)
```

### 3.4 SHACL风格约束规则

```
# ──── C1: 完整环必须有至少3个节点 ────
:CircularPathShape a sh:NodeShape ;
  sh:targetClass :CircularPath ;
  sh:property [
    sh:path :nodeCount ;
    sh:minInclusive 3 ;
    sh:message "环形路径至少需要3个节点" ;
  ] .

# ──── C2: 标记为隐藏网络的节点必须有证据 ────
:HiddenNetEvidenceShape a sh:NodeShape ;
  sh:targetClass :NodeEntity ;
  sh:filterShape [
    sh:property [
      sh:path :isHiddenNetwork ;
      sh:hasValue true ;
    ]
  ] ;
  sh:property [
    sh:path :hiddenNetReason ;
    sh:minCount 1 ;
    sh:message "隐藏网络标记必须附原因" ;
  ] .

# ──── C3: 高风险环必须有正标签订单 ────
:HighRiskRingShape a sh:NodeShape ;
  sh:targetClass :HighRiskRing ;
  sh:property [
    sh:path (:hasNode / :hasOrder / :hasRiskLabel) ;
    sh:minCount 1 ;
    sh:message "高风险环至少包含一个正标签订单" ;
  ] .
```

---

## 4. 推理与分析

### 4.1 推理流程

```
输入: 订单号 ORDER-XXXXXX
  │
  ▼
┌──────────────────────────────────────────────────────┐
│ 阶段1: 数据聚合                                       │
│  Neo4j查询节点+边属性 → Client/Address/License实例   │
│  MariaDB查询class_label → 订单风险标签                │
│  MySQL查询业务详情 → 贷款信息补充                     │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│ 阶段2: 环形检测(复用现有成果)                          │
│  从Neo4j运行Cypher找环 → 得到176条环形路径            │
│  映射为 :CircularPath 实例                             │
│  组合子图合并 → :CombinedSubgraph + :ConnectorNode    │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│ 阶段3: 规则推理(SWRL引擎)                              │
│  R1~R4: 隐藏网络标记验证                              │
│  R5: 识别高风险环 → 标注:HighRiskRing                  │
│  R6: 识别地址风险桥梁 → 标注:AddressRiskBridge         │
│  R7: 桥接节点风险浓度排序                              │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│ 阶段4: 约束验证(SHACL)                                │
│  C1: 环完整性校验                                     │
│  C2: 隐藏网络标记原因追溯                              │
│  C3: 高风险环正标签验证                                │
└──────────────────────┬───────────────────────────────┘
                       ▼
┌──────────────────────────────────────────────────────┐
│ 阶段5: 结果输出                                       │
│  风险分类: 高/中/低                                  │
│  桥接节点排名: 前10高风险地址                         │
│  告警: 新发现的高风险环                                │
└──────────────────────────────────────────────────────┘
```

### 4.2 关键查询示例

#### 查询1: 某地址关联的所有高风险环

```sparql
# 风格: SPARQL → 实际用Python实现
SELECT ?address ?ring ?labelCount ?ringSize
WHERE {
  ?address a :Address ;
           :isHiddenNetwork true .
  ?address :connects ?ring .
  ?ring a :HighRiskRing .
  ?ring :hasNode ?client .
  ?client :hasOrder ?order .
  ?order :hasRiskLabel ?label .
  FILTER(?label > 0)
}
GROUP BY ?address ?ring
ORDER BY DESC(COUNT(?label))
```

#### 查询2: 高风险桥接节点TOP10

```sparql
SELECT ?node ?type ?positiveRatio ?totalOrders
WHERE {
  ?node a :ConnectorNode .
  ?node :positiveRatio ?ratio .
  ?node :totalConnectedOrders ?total .
  FILTER(?ratio > 0.2)
}
ORDER BY DESC(?ratio)
LIMIT 10
```

#### 查询3: 新订单的风险预判

```sparql
SELECT ?order ?connectedClients ?hiddenNetRatio ?riskPrediction
WHERE {
  # 输入新订单的申请人
  :Client_XXX :hasOrder ?order .
  
  # 查申请人所在的环形网络
  ?order :inRing ?ring .
  ?ring :hasNode ?connectedClient .
  
  # 统计环内隐藏网络比例
  ?connectedClient :isHiddenNetwork true .
}
```

---

## 5. 输出与呈现

### 5.1 输出体系

| 输出类型 | 内容 | 格式 | 使用方 |
|:---|:---|:---|:---|
| **API服务** | 本体查询/推理/验证结果 | JSON (REST API) | 前端/其他系统 |
| **Dashboard** | 环形拓扑图 + 风险热力图 | Web (Vue3) | 风控人员 |
| **风险分类报告** | 每个环形子图的风险等级 | JSON/PDF | 风控/管理层 |
| **桥接节点排名** | 高风险地址/客户TOP榜 | 表格 | 运营人员 |
| **告警推送** | 新高风险环检测 | WebSocket/消息 | 实时监控 |
| **约束违反日志** | SHACL验证不通过的记录 | JSON(审计日志) | 审计 |

### 5.2 Dashboard设计

#### 页面1: 环形网络总览

```
┌──────────────────────────────────────────────────────────────┐
│  neograph 本体运营监控                          [刷新] [设置]  │
├──────────────────────────────────────────────────────────────┤
│ ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐  │
│ │ 环形子图    │ │ 涉及客户   │ │ 高风险环    │ │ AD桥梁节点 │  │
│ │ 75个       │ │ 155个      │ │ 19个(25.3%)│ │ 94个(31.9%)│  │
│ └────────────┘ └────────────┘ └────────────┘ └────────────┘  │
│                                                               │
│ ┌─────────────────────────────────────────────────────────┐  │
│ │  环形拓扑可视化 (Cytoscape.js)                          │  │
│ │                                                         │  │
│ │    [Client]───HAS_ADDRESS───[Address]                   │  │
│ │       │                        │                        │  │
│ │   SPOUSE_OF                 HAS_LICENSE                  │  │
│ │       │                        │                        │  │
│ │    [Client]───HAS_LICENSE───[License]                   │  │
│ │       │                        │                        │  │
│ │   CLIENT_OF                 LICENSE_OF                   │  │
│ │       │                        │                        │  │
│ │     [User]                    [Client]                  │  │
│ │                                                         │  │
│ │  ● 普通节点  ● 隐藏网络  ● 高风险环  ● AD桥梁         │  │
│ └─────────────────────────────────────────────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│ ┌─── 桥接节点排名 ──────┐ ┌─── 高风险环列表 ────────────┐  │
│ │ 节点     比例  金额   │ │ 环ID    节点数 标签  等级   │  │
│ │ AD1614  100%  ¥XX万  │ │ R001     4    2/3   ★★★   │  │
│ │ AD1216   50%  ¥XX万  │ │ R002     4    1/4   ★★    │  │
│ │ CL3aa4d 100%  ¥XX万  │ │ R003     3    1/3   ★★    │  │
│ │ CL65566 100%  ¥XX万  │ │ ...                         │  │
│ └──────────────────────┘ └──────────────────────────────┘  │
├──────────────────────────────────────────────────────────────┤
│ ┌─── 风险分布 ─────────────────────────────────────────┐  │
│ │  高风险环 ●●    28%                                  │  │
│ │  中风险环 ●●●●  53%                                  │  │
│ │  低风险环 ●●    19%                                  │  │
│ └──────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────┘
```

#### 页面2: 单环深度分析

```
┌──────────────────────────────────────────────────────────────┐
│  环形路径 #R001 深度分析                                      │
├──────────────────────────────────────────────────────────────┤
│                                                               │
│  环拓扑:                                                      │
│    CL_A ──HAS_ADDRESS──→ AD_001                              │
│     │                        ↑                                │
│     │                    LICENSE_OF                           │
│     ↓                        ↑                                │
│    LC_001 ←──HAS_LICENSE─── CL_B                              │
│                                                               │
│  节点详情:                                                     │
│  ┌────────┬────────┬──────────┬──────────┬──────────┐       │
│  │ 节点   │ 类型   │隐藏网络  │关联订单  │正标签   │       │
│  ├────────┼────────┼──────────┼──────────┼──────────┤       │
│  │ CL_A   │ Client │ true     │ 3        │ 2 (67%) │       │
│  │ CL_B   │ Client │ true     │ 2        │ 1 (50%) │       │
│  │ AD_001 │ Address│ true     │ 5        │ 3 (60%) │       │
│  │ LC_001 │ License│ false    │ 2        │ 0 (0%)  │       │
│  └────────┴────────┴──────────┴──────────┴──────────┘       │
│                                                               │
│  推理结果:                                                     │
│    [OK] R1: 地址共享 → AD_001标记为隐藏网络                    │
│    [OK] R2: 执照共享 → LC_001正常                              │
│    [OK] R5: 高风险环 → 环内67%订单带正标签                     │
│    [OK] R6: 地址风险桥梁 → AD_001连接2个环                     │
│                                                               │
│  关联订单:                                                     │
│  ┌──────────┬──────────┬────────┬──────────┬────────┐       │
│  │ order_id│ class_lbl│ 金额   │ 申请人   │ 行业   │       │
│  ├──────────┼──────────┼────────┼──────────┼────────┤       │
│  │ ORD-001  │ 2(严重)  │ ¥50万  │ CL_A     │ 餐饮   │       │
│  │ ORD-002  │ 1(轻度)  │ ¥30万  │ CL_A     │ 餐饮   │       │
│  │ ORD-003  │ 1(轻度)  │ ¥20万  │ CL_B     │ 批发   │       │
│  └──────────┴──────────┴────────┴──────────┴────────┘       │
│                                                               │
└──────────────────────────────────────────────────────────────┘
```

### 5.3 告警机制

| 告警类型 | 触发条件 | 推送方式 | 优先级 |
|:---|:---|:---|:---:|
| 新高风险环 | 新环形路径检测到 >50%正标签 | WebSocket+邮件 | P0 |
| AD桥梁浓度超阈值 | AD节点正标签 >30% | Dashboard标记 | P1 |
| 约束违反 | SHACL验证不通过 | 日志+告警 | P2 |
| 隐藏网络蔓延 | 新节点被标记为隐藏网络 | 周报汇总 | P3 |

---

## 6. 实施路线图

### Phase 1: 本体定义与数据接入 (2周)

| 任务 | 内容 | 产出 |
|:---|:---|---:|
| TBOX定义 | 类层次+对象属性+数据属性 | `ontology/tbox.py` (Python类) |
| 数据适配器 | Neo4j/MariaDB/MySQL三源读取 | `ontology/adapters/` 三个模块 |
| 规则引擎 | SWRL风格规则解释器 | `ontology/reasoner.py` |
| 约束引擎 | SHACL风格验证器 | `ontology/validator.py` |
| 实例化 | 现有176条环+155客户→本体实例 | `ontology/abox.py` |

### Phase 2: 推理与验证 (2周)

| 任务 | 内容 | 产出 |
|:---|:---|---:|
| 规则实现 | R1~R7推理规则 | `rules/` 规则配置文件 |
| 约束实现 | C1~C3约束规则 | `constraints/` 约束配置文件 |
| 查询层 | SPARQL风格查询接口 | `ontology/query.py` |
| 结果缓存 | 推理结果持久化 | `ontology/cache.py` |
| 批量验证 | 对全部75个组合子图运行推理 | 风险分类结果集 |

### Phase 3: 呈现层 (2周)

| 任务 | 内容 | 产出 |
|:---|:---|---:|
| API服务 | FastAPI本体查询+REST接口 | `api/main.py` |
| Dashboard | Vue3+Cytoscape.js环形拓扑可视化 | `ui/` 前端项目 |
| 桥接节点排名 | TOP榜+搜索 | Dashboard组件 |
| 告警推送 | WebSocket实时通知 | `api/ws.py` |
| 运营报告 | PDF自动生成(风险分类+桥接节点) | `api/reports.py` |

### 技术栈

| 组件 | 选型 | 用途 |
|:---|:---|---:|
| 后端框架 | FastAPI (已有.venv) | API服务 |
| 图查询 | Neo4j Python Driver | 读取图拓扑 |
| 关系查询 | pymysql / mysql-connector | MariaDB+MySQL |
| 本体引擎 | **自研** (Python规则引擎) | 轻量OWL-like推理 |
| 图可视化 | Cytoscape.js | 环形拓扑展示 |
| 前端框架 | Vue3 | Dashboard |
| 部署 | Docker Compose | 整合部署 |

### 项目目录结构

```
neograph_review/
  ├── ontology/
  │   ├── __init__.py
  │   ├── tbox.py            # 类/属性/关系定义
  │   ├── abox.py            # 实例化(从三数据库加载)
  │   ├── reasoner.py        # SWRL规则推理引擎
  │   ├── validator.py       # SHACL约束验证引擎
  │   ├── query.py           # 查询接口
  │   ├── cache.py           # 推理结果缓存
  │   └── adapters/
  │       ├── neo4j_adapter.py   # Neo4j读取
  │       ├── mariadb_adapter.py # MariaDB读取
  │       └── mysql_adapter.py   # MySQL读取
  ├── rules/
  │   ├── hidden_net_rules.yaml  # R1~R4 隐藏网络规则
  │   ├── risk_rules.yaml        # R5~R7 风险分类规则
  │   └── constraint_rules.yaml  # C1~C3 约束规则
  ├── api/
  │   ├── main.py            # FastAPI入口
  │   ├── routes.py          # API路由
  │   ├── ws.py              # WebSocket告警
  │   └── reports.py         # 报告生成
  ├── ui/                    # (前端 - 可选)
  │   ├── src/
  │   │   ├── Dashboard.vue
  │   │   ├── RingDetail.vue
  │   │   └── TopologyView.vue
  │   └── package.json
  ├── src/                   # (现有分析脚本,保持不变)
  └── docs/
      └── 本体建模实现方案.md  # 本文档
```
