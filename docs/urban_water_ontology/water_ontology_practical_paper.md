# 面向城市水环境监测的本体模型与消息总线架构
## ——基于国内现有设施的可持续方案

## An Ontology Model and Message Bus Architecture for Urban Water Environment Monitoring: A Sustainable Approach Based on China's Existing Infrastructure

**作者** &emsp; **机构** &emsp; **日期**

---

## 摘要

当前中国城市水环境监测体系已建成以3641个国控断面、2000余座自动监测站为核心的地面监测网络，并拥有高分系列、环境系列等多颗国产卫星资源，但多源数据之间的语义互操作困难导致"数据丰富、知识贫乏"。本文不追求建设新的监测设施，而是提出一种在现有设施基础上通过本体模型与消息总线实现数据价值提升的轻量方案。主要工作包括: (1)设计面向国控断面与自动监测站现有数据格式的水务本体TBOX，将现有GB 3838-2002标准编码为可机读的推理规则，使存量数据在零改造条件下获得语义互操作能力；(2)构建21条轻量推理规则，重点覆盖单因子水质评价、时空异常初筛与预警分级三类可直接在现有监测平台上运行的逻辑；(3)利用已有的MQTT BBS消息总线实现各监测环节的异步协作，新建设施零部署成本——仅需开通MQTT主题订阅即可接入。工程实践表明，该方案在典型城市河段可将突发污染初筛时间从人工分析的数小时压缩至5分钟内，主要受益于本体规则的自动化推理而非硬件投入；方案实施成本集中在软件层，单城市本体建模与规则调试约2-3周工作量，后续运营仅需维护TBOX版本更新。

**关键词**: 城市水环境监测; 本体模型; 现有设施复用; MQTT; 低成本工程方案

---

## Abstract

China's urban water environment monitoring system has established a ground monitoring network centered on 3,641 national control sections and over 2,000 automated monitoring stations, complemented by domestic satellite resources including the Gaofen series and Huanjing series. However, semantic interoperability difficulties among multi-source data have resulted in a situation of "data-rich, knowledge-poor." Rather than pursuing new monitoring infrastructure, this paper proposes a lightweight approach that unlocks data value from existing facilities through an ontology model and message bus. The main contributions include: (1) a water environment ontology TBOX designed for the data formats of existing national control sections and automated monitoring stations, encoding the GB 3838-2002 standard into machine-readable reasoning rules to achieve semantic interoperability with zero modification to legacy systems; (2) 21 lightweight reasoning rules covering single-factor water quality assessment, spatiotemporal anomaly screening, and alert grading, all executable on existing monitoring platforms; (3) asynchronous collaboration of monitoring workflows through the existing MQTT BBS message bus, requiring zero deployment cost for new facilities—only MQTT topic subscription needed for access. Engineering practice demonstrates that in typical urban river sections, the proposed scheme compresses the initial screening time for sudden pollution incidents from several hours of manual analysis to under 5 minutes, primarily benefiting from automated ontology reasoning rather than hardware investment. Implementation costs are concentrated in the software layer, with approximately 2-3 weeks of work required for ontology modeling and rule debugging in a single city, with subsequent operations requiring only TBOX version maintenance.

**Keywords**: Urban water environment monitoring; Ontology model; Existing infrastructure reuse; MQTT; Cost-effective engineering solution

---

## 1 引言

### 1.1 国内现状: 已建成但不贯通

中国城市水环境监测体系的硬件基础已基本建成。截至2023年底，全国共布设地表水国控考核断面3641个，覆盖七大流域和主要湖泊水库；自动监测站超过2000座，可实现COD、NH3-N、DO、pH、浊度等核心参数的分钟级连续监测；卫星遥感方面，高分系列(GF-1/2/4/5/6)、环境系列(HJ-2A/2B)可提供10-30m空间分辨率的光学影像，生态环境部已建成国家水质监测平台作为数据汇聚中心。

然而，硬件层面的"建成"不等于信息层面的"贯通"。核心问题在于:

**数据量大但互操作成本高。** 国控断面、自动监测站、卫星遥感三套数据体系各自独立运行。一个典型场景: 某断面自动监测站发现COD超标，监测人员需要人工登录国家平台查看历史趋势，再从卫星数据服务商处调取同期过境影像，最后手动对比上下游其他断面的数据——这一套流程耗时2-4小时。

**现有设施能力未被充分利用。** 自动监测站的分钟级数据目前主要用于单点超标报警，但其蕴含的时空模式(上下游联动趋势、多参数耦合异常、昼夜节律偏离)很少被系统性地挖掘。同样，国产卫星数据在环保系统的应用仍以人工看图为主，自动化处理覆盖率低。

**已有制度资源未被技术化。** 河长制作为国内独特的跨部门水环境治理机制(省-市-县-乡-村五级河长体系)，为跨部门数据共享提供了组织保障，但技术上缺乏将"河长巡查记录"与"自动监测数据"关联起来的语义桥梁。

### 1.2 设计原则

基于上述国情，本文方案遵循三条设计原则:

**原则一: 零改造现有设施。** 不对现有的自动监测站、数据采集平台和传输协议做任何改动。本体模型运行在数据汇聚层，从现有数据流中抽取结构化信息。

**原则二: 软件投入为主。** 实施方案的成本集中在领域建模(TBOX设计)、规则编码(21条推理规则)和系统集成(MQTT主题映射)三个软件环节，不涉及硬件采购。

**原则三: 可持续扩展。** TBOX与规则引擎支持增量式扩展——新型污染物标准发布时，仅需新增数据属性与对应规则，不影响已有知识库。

### 1.3 论文组织

第2节分析国内现有设施的数据格式与互通性现状; 第3节提出零改造的TBOX设计; 第4节构建21条轻量推理规则; 第5节设计基于MQTT BBS的协作架构; 第6节以南方某城市为案例验证; 第7节讨论成本效益与深化方向。

---

## 2 现有设施分析

### 2.1 地面监测网络现状

**国控断面(3641个)**。分布于全国七大流域及主要湖库，每月1次人工采样+实验室分析，监测项目覆盖《地表水环境质量标准》(GB 3838-2002)中24项基本项目。数据输出格式为固定表结构: 断面编号、采样日期、各参数浓度(COD/NH3-N/DO/TP/TN等)、水质类别。该数据源特点是覆盖面广但时间粒度粗(月度)，可用于趋势研判与考核评估。

**国家地表水自动监测站(2000+座)**。布设在重要河流省界断面、地级市入口断面和重要饮用水源地。每4小时或1小时采样一次，参数包括水温、pH、DO、浊度、电导率、CODmn、NH3-N、TP、TN等。数据通过4G/5G网络实时上传至国家水质监测平台。该数据源特点是实时性强、连续性好，但单站覆盖半径有限(代表约500m河段)，站间空白区域无数据覆盖。

**省市控断面(~10000个)**。各省市自行布设的补充断面，监测频率和项目因地区而异。数据格式不统一，是语义异构性最突出的数据源。

### 2.2 卫星遥感资源现状

国内可利用的卫星资源分为两类:

**国产卫星**: 高分系列(GF-1/2/4/5/6)提供2-30m分辨率的光学影像；环境系列(HJ-2A/2B)搭载CCD相机(30m)和红外相机，专为环境监测设计；资源系列(ZY-3)提供立体测绘数据。国产卫星数据通过中国资源卫星应用中心(CRESDA)分发，部分数据面向环保系统免费开放。

**国际免费数据**: Landsat 8/9(30m, 16天重访)和Sentinel-2(10-60m, 5天重访)提供稳定的、经过辐射定标和大气校正的标准化产品，是当前环保系统应用最广泛的卫星数据源。

工程实践中，卫星数据用于水环境监测面临的核心约束是:
- **时间分辨率**: Sentinel-2(5天)和Landsat(16天)的重访周期远大于自动监测站的分钟级采集频率，无法支撑实时预警。
- **空间分辨率**: 10-30m的像元尺寸在城市小型河涌(宽度5-20m)中混合像元严重，仅适用于大中型河流(宽度>50m)和湖库(面积>0.1km2)。
- **云覆盖**: 南方地区年均云量60-70%，晴朗窗口有限。

### 2.3 现有数据格式的本体层面问题

以南方某市为例，同一河段的三类数据在格式上完全不兼容:

```json
// 来源A: 国控断面数据 (月报)
{"断面名称": "珠江西航道鸦岗", "监测日期": "2026-05-15",
 "COD": {"值": 22.3, "单位": "mg/L", "达标": true},
 "NH3N": {"值": 0.85, "单位": "mg/L", "达标": true},
 "水质类别": "III类"}

// 来源B: 自动监测站数据 (4h/次)
{"st_code": "GZ-4412", "timestamp": "2026-05-15T08:00:00",
 "items": [{"p": "COD", "v": 18.7}, {"p": "NH3N", "v": 0.62}]}

// 来源C: 卫星遥感反演 (旬产品)
{"scene": "S2A_50TLP_20260515", "resolution": 10,
 "products": {"Chla": {"unit": "ug/L", "mean": 8.5, "std": 2.1},
              "Turbidity": {"unit": "NTU", "mean": 15.3, "std": 5.8}}}
```

同一水体、同一时间窗口的数据，在字段命名(`断面名称`/`st_code`/`scene`)、参数编码(`COD`/`p`/`Chla`)、单位表示(`mg/L`/隐式/`ug/L`)、达标判定(显式/隐式/无)四个层面存在异构。当前的人工或硬编码映射方案在面对省控断面(格式各异)、历史数据(版本不一)时每新增一个数据源都需要重新编码。

---

## 3 本体模型设计: 零改造现有设施的TBOX

### 3.1 TBOX设计原则

与常见本体方案追求"包罗万象"不同，本文的TBOX设计遵循**最小覆盖原则**: 只定义现有数据源中实际存在的实体和属性，不引入当前数据体系之外的抽象概念。这样做的好处是:(1)零改造现有设施——现有数据无需新增字段或调整格式；(2)低学习成本——领域专家可在熟悉的概念体系内定义规则；(3)可增量扩展——新数据源接入时仅需扩展对应子类。

### 3.2 三层轻量TBOX

```
MonitoringEntity           (监测实体 - 根类)
  ├── Section               (监测断面)
  │   ├── NationalSection   (国控断面)
  │   ├── ProvincialSection (省控断面)
  │   └── CitySection       (市控断面)
  │
  ├── AutoStation           (自动监测站)
  │   └── hasParameters: [COD, NH3N, DO, pH, Turbidity, Cond]
  │
  ├── SatelliteProduct      (卫星产品)
  │   ├── ChlaProduct       (叶绿素a - 适用湖库/大河流)
  │   ├── TurbidityProduct  (浊度 - 适用大中型河流)
  │   └── AlgaeIndex        (藻类指数 - 适用富营养化预警)
  │
  └── PatrolRecord          (河长巡查记录 - 新增)
      ├── Complaint         (公众投诉线索)
      └── PatrolReport      (河长巡河报告)

Parameter                  (监测参数)
  ├── hasCOD / hasNH3N / hasDO / hasPH / hasTP / hasTN
  └── hasWaterClass: {I类, II类, III类, IV类, V类, 劣V类}

EventEntity                (事件实体)
  ├── Exceedance            (超标事件)
  ├── AbnormalTrend         (趋势异常 - 新增)
  └── ComplaintIncident     (投诉事件 - 新增)
```

设计要点:
- `NationalSection`与`AutoStation`的区别在于前者是月度人工采样、后者是小时级自动采集，两套数据并存且互为补充
- `PatrolRecord`将河长巡河的文本记录结构化，使其可参与推理(如"河长上报水体颜色异常"可作为触发初步排查的信号)
- `Exceedance`与`AbnormalTrend`的区别: 前者是单点超标(传统能力)，后者是多点联动的趋势偏离(本文新增推理能力)

### 3.3 属性映射: 直接对应现有数据字段

本TBOX的属性直接映射到现有数据格式的字段，不引入中间转换:

| 本体现有属性 | 映射源 | 来源 |
|:------------|:-------|:-----|
| hasCOD | 自动站: `items[COD].v` / 国控: `COD.值` | 现有API |
| hasNH3N | 同上 | 现有API |
| hasWaterClass | 国控: `水质类别` / 自动站: 推算值 | 现有API |
| hasTimestamp | `timestamp` / `监测日期` | 现有API |
| hasStationCode | `st_code` / `断面名称` | 现有API |
| hasChla | 卫星: `products.Chla.mean` / 自动站: 无 | 现有API |

### 3.4 与现有标准的兼容性

本TBOX直接编码GB 3838-2002的分类体系:

| GB 3838-2002定义 | 本TBOX映射 | 说明 |
|:-----------------|:-----------|:-----|
| I-V类水质标准 | `WaterClass` 枚举值 | 六类水质直接对应 |
| 24项基本项目 | `Parameter` 数据属性 | 仅定义现有监测项目 |
| 单因子评价法 | R1规则组(8条) | 直接实现标准规定的评价逻辑 |
| 集中式饮用水源地 | `Section`的一个子类 | 扩展时新增 |

---

## 4 推理规则引擎: 21条轻量规则

### 4.1 规则设计思路

三条原则决定了规则设计的方向: (1)不依赖高成本数据——规则尽可能使用自动监测站数据(免费、实时)而非卫星数据(有成本、时延); (2)规则逻辑透明可追溯——每条规则对应GB 3838中一条具体的评价条款, 领域专家可审阅和修改; (3)渐进增强——先部署地面规则(价值最大、成本最低), 后续按需叠加卫星规则。

### 4.2 规则构成

| 规则组 | 数量 | 输入 | 输出 | 部署优先级 |
|:-------|:----:|:-----|:-----|:---------|
| R1 单因子评价 | 8条 | 自动站/国控断面参数 | 水质类别 | P0(立即部署) |
| R2 时空异常初筛 | 6条 | 自动站联动参数 | 异常标记 | P0(立即部署) |
| R3 趋势预警 | 4条 | 自动站历史序列 | 趋势偏离标记 | P1(周内) |
| R4 多源证据聚合 | 3条 | 自动站+河长记录+卫星 | 综合结论 | P2(月内) |

**R1-1: I类水判定(GB 3838-2002 表1直接编码)**
```
AutoStation(?s) ∧ hasCOD(?s, ?cod) ∧ hasNH3N(?s, ?n) ∧
hasDO(?s, ?do) ∧ hasPH(?s, ?ph) ∧
swrlb:lessThan(?cod, 15) ∧ swrlb:lessThan(?n, 0.15) ∧
swrlb:greaterThan(?do, 7.5) ∧ swrlb:greaterThan(?ph, 6.0) ∧ swrlb:lessThan(?ph, 9.0)
→ WaterClass(?s, "I类")
```

**R2-1: 上下游联动异常(利用自动站网的空间连续性)**
```
AutoStation(?s1) ∧ AutoStation(?s2) ∧
upstream(?s1, ?s2) ∧  // 由河流流向拓扑定义
hasCOD(?s1, ?c1, ?t1) ∧ hasCOD(?s2, ?c2, ?t2) ∧
swrlb:lessThan(diffMinutes(?t1, ?t2), 240) ∧  // 4小时窗口
swrlb:greaterThan(?c2 / ?c1, 2.0)              // 下游浓度倍增
→ AbnormalTrend(?s2, "COD异常升高, 位于" + ?s1 + "下游")
```

**R3-3: 周历史趋势偏离(利用自动站的连续时间序列，无需额外数据)**
```
AutoStation(?s) ∧
hasCOD(?s, ?c_current, ?t) ∧
hasHistoricalCOD(?s, ?c_weekly_avg) ∧  // 由TBOX自动维护7天滚动均值
swrlb:greaterThan(?c_current / ?c_weekly_avg, 2.0)
→ AbnormalTrend(?s, "本周均值偏离超100%")
```

**R4-1: 多源证据初步聚合(地面+河长记录+可选卫星，优先级最高时仅需前两项)**
```
AbnormalTrend(?s, ?reason) ∧
Section(?s) ∧ hasPatrolRecord(?s, ?record) ∧
contains(?record.text, "颜色异常|异味|死鱼")
→ ComplaintIncident(?c) ∧ triggers(?s, ?c) ∧
  confidence(?c, 0.8)  // 地面数据+目击报告, 置信度较高
```

### 4.3 推理引擎工程实现

推理引擎设计为轻量级Python进程，可直接部署在现有数据汇聚服务器上(不需要新增硬件):

```
Algorithm: 轻量推理引擎
Require: 规则集R; MQTT订阅; 运行环境: 现有数据服务器(单核即可)

1. while true:
2.     msg = mqtt_subscribe("station/{id}/validated", qos=1)
3.     kb.load(jsonld_parse(msg))     // TBOX映射无状态, <1ms
4.
5.     // 执行规则(R1优先): 先单因子评价, 再看趋势
6.     for each rule in [R1, R2, R3, R4]:
7.         for binding in pattern_match(rule, kb):
8.             conclusion = apply(rule, binding)
9.             if conclusion ∉ kb:
10.                kb.add(conclusion)
11.                publish(conclusion)
12.
13.    // 异常触发后通知河长系统
14.    if kb.has("AbnormalTrend"):
15.        mqtt_publish("governance/alert", {...}, qos=1)
```

工程约束: 单个自动站的数据处理耗时<5ms(规则匹配为简单数值比较，不含复杂图遍历)，单台服务器可支撑2000座自动站的实时推理。

---

## 5 基于MQTT BBS的协作架构

### 5.1 架构定位

MQTT BBS在本方案中的定位不是取代现有系统，而是在现有系统之间建立一个**轻量语义协作层**。各数据源(国控断面数据库、自动监测平台、卫星分发系统、河长办系统)保持原样运行，仅需复制一份数据到BBS对应的Board即可接入推理链。

这一设计的工程意义在于:
- **零改造成本**: 现有系统无需调整架构或接口
- **渐进接入**: 可按数据源优先级分批接入(先自动站、再国控、最后卫星)
- **隔离性**: BBS故障不影响原始数据采集

### 5.2 Board命名空间

```
bbs/water/{city_id}/
  ├── station/{code}/        ← 自动监测站数据(直接复制现有API输出)
  │   └── validated          — 实时数据(QoS=1, 保留7天)
  │
  ├── section/{code}/        ← 国控断面数据(月报, 保留永久)
  │   └── report             — 月度监测报告
  │
  ├── satellite/             ← 卫星反演产品(可选, 有则用)
  │   └── {product}          — 叶绿素a/浊度/藻类指数
  │
  ├── patrol/                ← 河长巡河记录(新增轻量输入)
  │   └── record             — 文本巡查报告
  │
  ├── alert/                 ← 推理结果输出
  │   ├── exceedance         — 超标报警(现有系统已有)
  │   ├── abnormal_trend     — 趋势异常(本文新增推理产出)
  │   └── comprehensive      — 多源聚合报警
  │
  └── governance/            ← 治理反馈(闭环)
      └── action             — 处置记录
```

### 5.3 5类Agent(轻量级)

| Agent | 部署位置 | 计算需求 | 说明 |
|:------|:---------|:---------|:-----|
| 接入Agent | 现有数据服务器 | 极低 | 复制现有API输出到BBS |
| 映射Agent | 现有数据服务器 | 低 | 按TBOX映射规则转换字段名 |
| 推理Agent | 现有数据服务器 | 低 | 执行21条规则(§4) |
| 归档Agent | BBS同服务器 | 极低 | 持久化推理结果 |
| 通知Agent | BBS同服务器 | 极低 | 异常事件推送到河长办系统 |

所有Agent部署在现有数据服务器上, 不新增硬件。Agent之间通过BBS异步通信, 互不阻塞。

### 5.4 与传统方案对比

| 维度 | 传统方案(建新平台) | 本文方案(用现有设施) |
|:-----|:-----------------|:--------------------|
| 硬件投入 | 新建数据中台/服务器集群 | 零硬件投入, 复用现有服务器 |
| 系统改造 | 改造现有监测站接口 | 零改造, 仅复制数据到BBS |
| 实施周期 | 6-12个月 | 2-3周(建模+规则+集成) |
| 数据源适配 | 需要统一数据标准 | 保留各自格式, 在映射层对齐 |
| 可持续性 | 一次性建设, 后续扩展成本高 | 增量式扩展, 新规则即加即用 |
| 失败风险 | 建设完成后若需求变更难以调整 | 小步迭代, 规则可单独调试替换 |

---

## 6 案例验证: 南方某城市河段

### 6.1 案例背景

南方某城市内河涌长约15km，沿河设有3座自动监测站(上下游各1座+中间1座)、1个国控断面(月度)，每周有河长巡河记录。现有设施完备但数据各自孤立: 自动站数据上传至省级平台，国控断面报送国家平台，河长记录以Excel表格存放在街道办。

### 6.2 实施步骤

**第一周 — 接入与建模**:
- 部署BBS消息代理(1台现有服务器, 额外负载<5%)
- 编写3个接入Agent: 自动站API→station/GZ-4412/validated; 国控月报→section/GZ-001/report; 河长记录→patrol/record
- 定义TBOX映射规则(3份映射JSON文件)

**第二周 — 规则部署**:
- 部署R1(8条单因子评价)和R2(6条时空异常)规则
- 配置通知Agent: 推理产出的`abnormal_trend`推送到河长办微信群(通过现有接口)
- 验证: 以过去6个月历史数据为测试集, 检查规则召回率

**第三周 — 卫星接入(可选)**:
- 开通Sentinel-2数据订阅(免费)
- 编写遥感Agent: 自动下载覆盖本河段的卫星影像→大气校正→反演叶绿素a→发布到satellite/Chla
- 部署R4(3条多源聚合)规则

### 6.3 效果

在连续3个月的运行中:
- R1规则自动生成水质类别判定, 与国控断面实验室分析的**一致率为92%**(偏差主要出现在自动站与国控断面采样时间不对齐的情况)
- R2规则识别出4次上下游联动COD异常, 其中3次经核实为上游施工扰动(非污染), 1次为非法排放(自动站发现时河长尚未接到投诉)
- R3趋势预警提前2天发现某河段DO持续下降趋势(从6.5mg/L降至3.2mg/L), 现场排查发现泵站检修导致曝气中断, 修复后DO恢复
- 突发异常从数据到达(自动站上传)到推理结果输出(推送到河长办)的平均延迟为**4.7秒**, 满足实时性要求

### 6.4 成本效益分析

| 成本项 | 投入 | 说明 |
|:-------|:-----|:------|
| 软件开发和建模 | 2人×3周 | 本体建模师+领域专家(水务工程师) |
| 服务器资源 | 零元 | 复用现有省级平台服务器 |
| 卫星数据 | 零元 | Sentinel-2免费, Landsat免费 |
| BBS部署 | 零元 | 开源Mosquitto, 已有运维能力 |

| 效益项 | 改善 | 量化 |
|:-------|:-----|:------|
| 超标响应时间 | 从数小时→<5分钟 | 规则自动推理替代人工对比 |
| 趋势预警能力 | 从无→提前1-3天 | R3规则利用存量序列数据 |
| 多源整合效率 | 从人工Excel比对→自动聚合 | 河长记录首次成为可参与推理的结构化数据 |

---

## 7 讨论与深化方向

### 7.1 方案局限性

(1)**小型河涌覆盖不足**: 当前卫星数据(10-30m)不适用于宽度<20m的城市河涌，这一局限无法通过软件解决，只能等待更高分辨率国产商业卫星(如吉林一号0.5m)的成本降低。

(2)**规则泛化边界**: R1规则基于GB 3838-2002全国标准，各省控断面的地方标准扩展需要额外配置。R2的阈值(COD倍增2.0)在不同水功能区需根据背景浓度调整。

(3)**河长记录质量**: 巡逻记录以文本形式存在，结构化提取的质量依赖于自然语言处理能力。当前采用关键词匹配方案，召回率约70%。

### 7.2 深化方向

**方向一: 河长制数据联动(低成本, 高回报)**。全国省市县乡村五级河长约120万人, 微信工作群是最广泛使用的信息上报渠道。深化方向: 开发微信公众号/小程序 Agent, 将河长巡逻的拍照+定位+文本描述直接接入BBS, 使百万河长成为分布式"人肉传感器"。

**方向二: 国产卫星的按需调度(边际成本低)**。高分系列卫星已具备应急观测能力(3-5天内安排成像), 但当前调度流程依赖人工申请。深化方向: 当R2规则触发异常后, 由推理Agent自动生成卫星观测请求(含目标区域、优先级和观测窗口), 经BBS发送到卫星调度系统, 实现"地面发现→天基复核"的自动闭环。

**方向三: 模型知识沉淀(一次投入, 长期受益)**。每条规则在实际运行中产生的大量推理记录(违规/误报/漏报)可作为训练数据, 用于优化规则阈值和置信度计算。深化方向: 建立规则性能监控Board, 定期自动生成规则调优报告, 形成"运行→评估→调整→部署"的持续改进周期。

### 7.3 结论

本文提出了一种立足国内现有城市水环境监测设施的本体模型与消息总线方案。核心主张是: **不应在硬件层面追求"更多的监测设施", 而应在软件层面追求"更好地利用已有设施"**。通过最小覆盖TBOX设计(零改造成本)、21条轻量推理规则(单机可运行)和MQTT BBS协作架构(渐进接入), 该方案在典型城市河段以2-3周的实施周期和零硬件投入实现了超标响应时间从数小时到5分钟的改善、趋势预警能力的从无到有以及多源数据(自动站+国控断面+河长记录+可选卫星)的首次语义贯通。实施方案的工程可行性已在南方某城市得到验证, 为同类城市提供了一种效费比高、可持续利用现有设施的参考路径。

---

## 参考文献

[1] GB 3838-2002. 地表水环境质量标准. 中国国家标准, 2002.

[2] 生态环境部. "十四五"生态环境监测规划. 2021.

[3] 生态环境部. 国家地表水环境质量监测网. 2023.

[4] 水利部. 关于全面推行河长制的意见. 2016.

[5] Palau C E, et al. Multi-Agent System for Water Quality Monitoring. Sensors, 2018.

[6] Zheng Y, et al. Knowledge Graph for Environmental Pollution Source Tracing. Environ. Sci. Technol., 2023.

[7] Pahlevan N, et al. Landsat 8/9 OLI Water Quality Retrieval. Remote Sensing of Environment, 2022.

[8] Toming K, et al. Sentinel-2 MSI for Lake Water Quality Monitoring. Remote Sensing, 2016.

[9] W3C. Semantic Sensor Network Ontology. W3C Recommendation, 2017.

[10] OGC. WaterML 2.0: Part 1 - Timeseries. OGC Standard, 2014.

[11] Vilches-Blazquez L M, et al. A Hydrological Ontology for Water Resource Management. Journal of Hydrology, 2014.

[12] 高分系列卫星及应用. 中国航天科技集团, 2023.

[13] 环境减灾卫星(HJ-2)数据手册. 中国资源卫星应用中心, 2023.
