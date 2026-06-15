# 城市水环境监测本体模型 — 水务 × 本体 × MQTT BBS 融合方案

> 日期: 2026-06-04
> 范围: 聚焦水务监测领域本体建模 + MQTT BBS 多Agent架构
> 参考: water_env_monitoring_scenarios.md, SOSA/SSN, WaterML2.0, HY_ONT

---

## 目录

1. [问题域：水环境监测的三大本体论鸿沟](#1-问题域水环境监测的三大本体论鸿沟)
2. [水务本体模型 TBOX 设计](#2-水务本体模型-tbox-设计)
3. [推理规则引擎](#3-推理规则引擎)
4. [MQTT BBS 架构集成](#4-mqtt-bbs-架构集成)
5. [本体引擎 × MQTT BBS 融合接口](#5-本体引擎--mqtt-bbs-融合接口)
6. [实施路线图](#6-实施路线图)

---

## 1. 问题域：水环境监测的三大本体论鸿沟

### 1.1 语义鸿沟 — 多源异构数据无法互操作

城市水环境监测涉及环保(水质)、水务(管网)、市政(排水)、水利(河道)四个部门，各自使用独立的数据标准和术语体系:

| 部门 | 监测数据 | 术语体系 | 采样频率 |
|:----|:---------|:---------|:---------|
| 生态环境局 | 地表水国控断面水质 | GB 3838-2002 标准 | 月/周 |
| 水务集团 | 管网压力/流量/水质 | CJJ 行业标准 | 分钟级 |
| 市政排水 | 排口/泵站运行状态 | 企业内部编码 | 实时 |
| 水利局 | 河道水位/流速 | SL 行业标准 | 小时级 |

**同一水体**在不同系统中被用不同ID、不同坐标系、不同时间粒度描述，无法形成统一的"水体健康画像"。

### 1.2 推理鸿沟 — 从数据到决策缺乏可解释链

当前架构: 传感器数据 → 阈值判断 → 报警

缺失环节:
- 超标值 → 什么原因? (污染源? 传感器故障? 自然变化?)
- 单点异常 → 是否影响下游? (传播路径? 时间窗口?)
- 多参数趋势 → 生态系统状态如何? (富营养化? 自净能力下降?)

### 1.3 协作鸿沟 — 跨部门应急响应缺乏协调本体

突发水污染事件中，环保溯源、水务调度、水利调控各自为政，因为缺乏一个**共享的事件本体**来描述"发生了什么→谁该做什么→信息如何流转"。

---

## 2. 水务本体模型 TBOX 设计

### 2.1 四层实体类层次

```
:WaterEntity                (水务实体 - 根类)
  ├── :WaterBody             (水体实体)
  │   ├── :River             (河道)
  │   ├── :Lake              (湖泊/水库)
  │   ├── :Groundwater       (地下水)
  │   └── :Estuary           (河口)
  │
  ├── :MonitoringEntity      (监测实体)
  │   ├── :Station           (固定监测站)
  │   ├── :Sensor            (在线传感器)
  │   │   ├── :ChemicalSensor  (化学参数传感器: COD/NH3-N/TP/TN)
  │   │   ├── :PhysicalSensor  (物理参数传感器: 温度/pH/浊度/DO)
  │   │   └── :BiologicalSensor(生物传感器: 藻类/叶绿素/大肠杆菌)
  │   ├── :SamplingPoint     (人工采样点)
  │   └── :RemoteSensing     (遥感观测)
  │
  ├── :EventEntity           (事件实体)
  │   ├── :PollutionIncident (污染事件)
  │   ├── :AbnormalReading   (异常读数)
  │   ├── :EquipmentFailure  (设备故障)
  │   └── :NaturalChange     (自然变化: 暴雨/藻华/枯水)
  │
  └── :GovernanceEntity      (治理实体)
      ├── :TreatmentPlant    (污水处理厂)
      ├── :PumpingStation    (泵站)
      ├── :Outfall           (排口/雨水口)
      └── :EmergencyResponse (应急响应)

:ObservationEntity          (观测实体 - 根类)
  ├── :Measurement           (单次测量: 时间+参数+值+单位)
  ├── :TimeSeries            (时间序列: 连续观测)
  ├── :Sample                (水样: 采样+运输+分析)
  └── :QualityReport         (水质报告: 综合评价)
```

### 2.2 对象属性 (Object Properties)

| 属性 | 定义域 | 值域 | 说明 |
|:----|:-------|:-----|:------|
| `:hasMonitoringStation` | WaterBody | Station | 水体上设有的监测站 |
| `:hasSensor` | Station | Sensor | 监测站部署的传感器 |
| `:observes` | Sensor | Parameter | 传感器观测的参数 |
| `:affects` | PollutionSource | WaterBody | 污染源影响的水体 |
| `:flowsInto` | WaterBody | WaterBody | 水体上下游连接 |
| `:triggers` | AbnormalReading | PollutionIncident | 异常读数触发事件 |
| `:respondedBy` | Incident | EmergencyResponse | 事件的应急响应 |
| `:monitoredBy` | Parameter | Sensor | 参数由传感器监测 |

### 2.3 数据属性 (Data Properties)

| 属性 | 值域 | 示例 |
|:----|:-----|:------|
| `:hasCOD` | xsd:decimal | 25.3 (mg/L) |
| `:hasNH3N` | xsd:decimal | 1.2 (mg/L) |
| `:hasDO` | xsd:decimal | 6.5 (mg/L) |
| `:hasPH` | xsd:decimal | 7.8 |
| `:hasTurbidity` | xsd:decimal | 15.2 (NTU) |
| `:hasWaterLevel` | xsd:decimal | 3.5 (m) |
| `:hasFlowRate` | xsd:decimal | 120.0 (m3/s) |
| `:hasWaterClass` | xsd:string | "I类", "II类", "III类", "IV类", "V类", "劣V类" |
| `:hasTimestamp` | xsd:dateTime | 2026-06-04T14:30:00 |
| `:hasLocation` | xsd:string | "WGS84: 113.27, 23.13" |
| `:hasAlertLevel` | xsd:integer | 1(蓝)/2(黄)/3(橙)/4(红) |

### 2.4 标准兼容性

本TBOX设计兼容以下国际标准:

| 标准 | 范围 | 映射 |
|:-----|:------|:-----|
| **SOSA/SSN (W3C)** | 传感器/观测/采样/驱动 | `Sensor` `Observation` `Sample` 直接复用 |
| **WaterML2.0 (OGC)** | 水文时间序列 | `TimeSeries` `Measurement` 对齐其观测模型 |
| **HY_ONT** | 47类水文实体 | `WaterBody` `River` 层次复用其分类 |
| **GB 3838-2002** | 中国地表水标准 | `WaterClass` 枚举 + 阈值规则映射 |

---

## 3. 推理规则引擎

### 3.1 规则分类

| 规则类 | 数量 | 说明 |
|:-------|:----:|:------|
| 水质评价规则 | 8条 | 基于GB 3838标准的单因子/多因子评价 |
| 异常检测规则 | 6条 | 时空联动异常识别 |
| 污染溯源规则 | 5条 | 基于上下游关系和参数特征的溯源推理 |
| 预警分级规则 | 4条 | 综合异常程度+影响范围+传播速度 |

### 3.2 核心规则示例 (SWRL风格)

**规则1: 水质类别判定 (基于GB 3838-2002)**
```
WaterBody(?w) ∧ hasCOD(?w, ?cod) ∧ hasNH3N(?w, ?n) ∧ hasDO(?w, ?do) ∧
swrlb:lessThan(?cod, 15) ∧ swrlb:lessThan(?n, 0.5) ∧ swrlb:greaterThan(?do, 7.5)
→ WaterClass(?w, "I类")
```

**规则2: 上下游关联异常传播**
```
AbnormalReading(?a) ∧ occursAt(?a, ?station1) ∧
monitors(?station1, ?param) ∧
WaterBody(?w) ∧ hasMonitoringStation(?w, ?station1) ∧
flowsInto(?w, ?w2) ∧ hasMonitoringStation(?w2, ?station2) ∧
swrlb:lessThan(timestamp(?a) - ?window, 3600)  (* 1小时窗口 *)
→ hasDownstreamRisk(?station2, true)
```

**规则3: 突发污染事件判定**
```
AbnormalReading(?a1) ∧ AbnormalReading(?a2) ∧
sameWaterBody(?a1, ?a2) ∧
swrlb:lessThan(diffMinutes(?a1.time, ?a2.time), 30) ∧
swrlb:greaterThan(countAffectedParams(?a1, ?a2), 2)
→ triggers(?a1, ?incident) ∧ PollutionIncident(?incident)
```

**规则4: 预警等级自动分级**
```
PollutionIncident(?i) ∧ affectsDownstream(?i, ?stations) ∧
swrlb:greaterThan(count(?stations), 5) ∧
containsHazardous(?i, true)
→ hasAlertLevel(?i, 4)  (* 红色预警 *)
```

### 3.3 规则引擎架构

```
┌──────────────────────────────────────────────┐
│              规则推理引擎                      │
│                                               │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐   │
│  │ 水质评价  │  │ 异常检测  │  │ 污染溯源  │   │
│  │ 8条规则  │  │ 6条规则  │  │ 5条规则  │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘   │
│       │             │             │          │
│       ▼             ▼             ▼          │
│  ┌────────────────────────────────────────┐  │
│  │          冲突解决 + 优先级排序          │  │
│  └────────────────┬───────────────────────┘  │
│                   │                          │
│                   ▼                          │
│  ┌────────────────────────────────────────┐  │
│  │      推理结果输出 (JSON-LD 格式)        │  │
│  │  { incident, confidence, evidence,    │  │
│  │    suggested_action, alert_level }     │  │
│  └────────────────┬───────────────────────┘  │
└───────────────────┼──────────────────────────┘
                    │
                    ▼
           MQTT BBS Board (下一章)
```

---

## 4. MQTT BBS 架构集成

### 4.1 层次化 Board 命名空间

```
bbs/water/{city_id}/
  ├── river/{river_id}/
  │   ├── param/{param_name}     — 实时参数数据 (DO/COD/NH3N/...)
  │   ├── status                 — 河段健康状态 (本体推理结果)
  │   └── alert                  — 预警信息
  │
  ├── station/{station_id}/
  │   ├── raw                    — 传感器原始读数
  │   ├── validated              — 经过数据质量校验
  │   └── meta                   — 监测站元数据 (本体实例)
  │
  ├── incident/{incident_id}/
  │   ├── alerts                 — 初始报警
  │   ├── trace/{agent_id}       — 各Agent排查线索
  │   ├── suspects               — 嫌疑源聚合
  │   ├── evidence               — 证据汇总
  │   ├── action                 — 处置措施
  │   └── archive                — 事件归档
  │
  ├── governance/
  │   ├── task/{task_id}         — 跨部门协调任务
  │   └── decision/{decision_id} — 决策记录与溯源
  │
  └── ontology/
      ├── tbox                   — 本体模式定义
      └── 推理结果                 — 推理引擎输出
```

### 4.2 Agent 角色与协作

| Agent 角色 | 职责 | 订阅的 Board | 发布的 Board |
|:-----------|:-----|:-------------|:-------------|
| **采集Agent** | 从传感器/API拉取数据，发布到 raw | — | station/{id}/raw |
| **校验Agent** | 数据质量检查、缺失插值 | station/{id}/raw | station/{id}/validated |
| **本体映射Agent** | 原始数据 → 本体实例(JSON-LD) | station/{id}/validated | ontology/实例 |
| **推理Agent** | 规则引擎执行，生成状态/预警 | ontology/实例 | river/{id}/status, river/{id}/alert |
| **溯源Agent** | 污染事件溯源推理 | incident/{id}/trace/* | incident/{id}/suspects |
| **协调Agent** | 跨部门任务分发 | governance/task/{id} | governance/decision/{id} |
| **归档Agent** | 事件归档与知识沉淀 | incident/{id}/archive | ontology/经验知识 |

### 4.3 数据流水线

```
传感器/API
    │
    ▼
┌─────────────┐
│ 采集Agent    │  →  station/{id}/raw           (MQTT QOS=1)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 校验Agent    │  →  station/{id}/validated     (MQTT QOS=1)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 本体映射Agent │  →  ontology/实例             (MQTT QOS=2, 持久化)
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 推理Agent    │  →  river/{id}/status
│ 规则引擎     │  →  river/{id}/alert
│ (8+6+5+4条) │  →  incident/{id}/alerts
└──────┬──────┘
       │
       ▼
┌─────────────┐
│ 溯源/协调Agent│  →  incident/{id}/suspects
│ 多Agent并行   │  →  governance/task/{id}
└─────────────┘
```

### 4.4 BBS 关键特性利用

| BBS 特性 | 在水务场景中的应用 |
|:---------|:-------------------|
| **持久化消息** | 污染事件全链路可追溯，满足环保督察审计要求 |
| **Board 注册发现** | 动态监测站/传感器上线即注册，无需人工配置 |
| **异步广播** | 异常读数 → 多Agent并行排查 → 结果聚合 |
| **DAG 工作流** | 应急响应流程编排: 报警→溯源→决策→处置→归档 |
| **文件传输** | 水样照片/检测报告的传输与共享 |

---

## 5. 本体引擎 × MQTT BBS 融合接口

### 5.1 本体推理结果输出格式 (JSON-LD)

```json
{
  "@context": "bbs/water/{city_id}/ontology/context.jsonld",
  "@type": "PollutionIncident",
  "id": "bbs/water/gz/incident/20260604-001",
  "timestamp": "2026-06-04T08:30:00Z",
  "location": {"@type": "Station", "id": "st-4412"},
  "parameters": {
    "COD": {"value": 85.3, "unit": "mg/L", "standard": 40},
    "NH3N": {"value": 12.5, "unit": "mg/L", "standard": 2.0}
  },
  "推理结果": {
    "alertLevel": 4,
    "confidence": 0.87,
    "evidence": [
      "COD超标112%, NH3N超标525%, 非自然波动",
      "上游3km内有化工企业排口",
      "当前为枯水期, 稀释能力下降"
    ],
    "suggestedAction": "立即启动红色预警, 通知环保监察, 下游取水口加强监测"
  }
}
```

### 5.2 接口调用链

```
                   ┌──────────────────────┐
                   │    推理Agent           │
                   │  (Python规则引擎)      │
                   └──────────┬───────────┘
                              │ 订阅: ontology/实例 (QOS=2)
                              │
                              ▼
                   ┌──────────────────────┐
                   │  推理规则匹配验证      │
                   │  1. 水质评价           │
                   │  2. 异常检测           │
                   │  3. 污染溯源           │
                   │  4. 预警分级           │
                   └──────────┬───────────┘
                              │
                              ▼
                   ┌──────────────────────┐
                   │  发布推理结果          │
                   │  river/{id}/status    │
                   │  river/{id}/alert     │
                   │  incident/{id}/alerts │
                   └──────────┬───────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
   ┌────────────┐    ┌────────────┐    ┌────────────┐
   │ 溯源Agent   │    │ 协调Agent   │    │ Dashboard  │
   │ 并行排查    │    │ 任务分发    │    │ 可视化展示  │
   └────────────┘    └────────────┘    └────────────┘
```

### 5.3 与传统方案对比

| 维度 | 传统方案 (中心化API) | 本方案 (MQTT BBS + 本体) |
|:-----|:-------------------|:------------------------|
| **数据流** | Polling/定时任务 | Push/事件驱动, 实时性更高 |
| **扩展性** | 加新传感器需改API | 新传感器=新Agent, 注册即用 |
| **审计追溯** | 日志文件, 查询困难 | BBS持久化, 全链路可追溯 |
| **跨部门协作** | 需要统一接口规范 | Board作为共享空间, 各写各的 |
| **知识复用** | 规则硬编码在代码中 | 本体规则声明式, 可独立演化 |
| **故障隔离** | 单点故障影响全局 | Agent独立, 部分故障不影响整体 |

---

## 6. 实施路线图

### Phase 1: 本体建模 (2-3周)

| 步骤 | 产出 |
|:-----|:-----|
| TBOX 精化 | OWL类定义文件 (.ttl) |
| 规则编码 | 23条SWRL规则实现 |
| 标准对齐 | SOSA/SSN + WaterML2.0 映射表 |
| 验证数据集 | 3个典型场景测试案例 |

### Phase 2: 本体引擎 + MQTT BBS 桥接 (2周)

| 步骤 | 产出 |
|:-----|:-----|
| 推理Agent实现 | Python规则引擎 + BBS Board发布 |
| 本体映射Agent | CSV/JSON → JSON-LD 转换器 |
| Board 命名空间部署 | MQTT BBS Board 自动化创建 |

### Phase 3: 多Agent协作流水线 (2周)

| 步骤 | 产出 |
|:-----|:-----|
| 采集/校验Agent | 传感器数据接入 |
| 溯源Agent | 污染溯源多Agent并行 |
| 归档Agent | 事件沉淀为经验知识 |

### Phase 4: 实战验证 (持续)

| 场景 | 验证指标 |
|:-----|:---------|
| 突发污染溯源 | 从报警到定位嫌疑源 < 30分钟 |
| 跨部门协调 | 应急响应全流程在BBS上可追溯 |
| 数据质量流水线 | 自动检测并修复 > 90% 的异常数据 |

---

## 附录: 关键参考

| 标准/项目 | 领域 | 与本方案关系 |
|:----------|:-----|:-------------|
| **SOSA/SSN (W3C, 2017)** | 传感器本体 | TBOX基类复用 |
| **WaterML2.0 (OGC, 2014)** | 水文数据 | 时间序列模型对齐 |
| **HY_ONT (Vilches-Blazquez, 2014)** | 水文实体 | WaterBody分类参考 |
| **GB 3838-2002** | 中国水质标准 | 评价规则基础 |
| **GB/T 35654-2017** | 水质在线监测 | 监测站元数据规范 |
