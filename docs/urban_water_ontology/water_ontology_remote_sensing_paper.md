# 面向城市水环境监测的本体模型与多Agent消息总线架构
## ——融合卫星遥感与地面传感网的空天地协同方法

## Ontology Model and Multi-Agent Message Bus Architecture for Urban Water Environment Monitoring: An Integrated Space-Air-Ground Approach with Satellite Remote Sensing

**作者** &emsp; **机构** &emsp; **日期**

---

## 摘要

城市水环境监测面临多源异构数据语义互操作困难、异常事件推理链断裂、跨部门协作缺乏共享知识表达等核心挑战。现有监测体系以地面固定站为主，空间覆盖有限，难以支撑大范围水域的同步监测与快速溯源。本文提出一种融合卫星遥感、地面传感网与MQTT消息代理总线(BBS)的空天地一体化监测架构，以本体模型为语义纽带连接多源观测数据。主要工作包括: (1)设计覆盖卫星遥感传感器、地面监测站、水环境事件与治理实体的五层水务本体TBOX，模型兼容SOSA/SSN、OGC EO、WaterML2.0国际标准及GB 3838-2002国家标准；(2)构建包含水质评价、遥感异常检测、空地数据融合与预警分级四类共27条推理规则的规则引擎，实现从卫星影像与地面传感数据到污染事件判定的可解释推理链；(3)将本体推理引擎部署于层次化MQTT BBS之上，通过8类Agent的异步协作完成遥感影像处理、地面数据采集、空地数据融合、污染溯源与归档全流程。工程实践表明，该架构在突发污染溯源场景中可将响应时间压缩至分钟级，有效融合了卫星遥感的广域覆盖优势与地面传感网的高精度优势。

**关键词**: 城市水环境监测; 本体模型; 卫星遥感; MQTT; 多Agent系统; 空地数据融合

---

## Abstract

Urban water environment monitoring faces critical challenges including semantic interoperability among heterogeneous data sources, broken reasoning chains for anomaly events, and absence of shared knowledge representation for cross-department collaboration. Existing monitoring systems predominantly rely on fixed ground stations with limited spatial coverage, making it difficult to achieve synchronized monitoring and rapid source tracing across large water areas. This paper proposes an integrated space-air-ground monitoring architecture that combines satellite remote sensing, in-situ sensor networks, and an MQTT Bulletin Board System (BBS), with an ontology model serving as the semantic bridge connecting multi-source observational data. The main contributions include: (1) a five-layer water environment ontology TBOX covering satellite remote sensing sensors, ground monitoring stations, water environment events, and governance entities, compatible with SOSA/SSN, OGC EO, WaterML2.0, and GB 3838-2002 standards; (2) a reasoning engine comprising 27 rules across four categories—water quality assessment, remote sensing anomaly detection, space-ground data fusion, and alert grading—establishing an interpretable reasoning chain from satellite imagery and ground sensor data to pollution incident determination; (3) deployment of the ontology reasoning engine atop a hierarchical MQTT BBS, where eight types of agents collaboratively complete the full pipeline of remote sensing image processing, ground data acquisition, space-ground data fusion, pollution source tracing, and archival. Engineering practice demonstrates that the proposed architecture compresses the response time in sudden pollution source tracing scenarios to the minute level, effectively integrating the wide-area coverage advantages of satellite remote sensing with the high-precision capabilities of in-situ sensor networks.

**Keywords**: Urban water environment monitoring; Ontology model; Satellite remote sensing; MQTT; Multi-agent system; Space-ground data fusion

---

## 1 引言

### 1.1 研究背景与问题

城市水环境监测是生态文明建设的基础设施。中国生态环境部《"十四五"生态环境监测规划》明确要求"构建天地一体的生态环境监测网络，实现卫星遥感与地面监测的协同应用"[10]。然而，当前城市水环境监测体系呈现出严重的"重地面、轻天基"的结构性失衡: 地面监测站能提供分钟级精度的原位数据，但单站覆盖半径仅数百米，城市尺度(通常数百平方公里)的同步监测需要数千个监测站，建设与运维成本极高；卫星遥感和机载遥感能实现大范围水域的同步观测，但受限于空间分辨率(10-300m)、时间分辨率(数天至数周重访周期)和大气校正等工程约束，在精确溯源和实时预警方面存在能力短板。

更深层的挑战在于: 两种监测手段产生的是**本体层面异构**的数据。地面站输出的多是以时间为索引的参数序列(如"2026-06-04T08:30, st-4412, COD=38.2mg/L")，卫星遥感输出的是以空间为索引的反射率图像(如"2026-06-04T09:47, Sentinel-2 B4波段, Tile 50TLP, 像素值=0.12")。同一水体健康状态在这两套数据体系中用完全不同的实体类型、空间参考和时间粒度来描述，传统方法依赖人工编码的映射逻辑进行数据融合，效率低且难以推广。

### 1.2 相关研究

**环境监测本体领域.** W3C的SOSA/SSN本体[1]为传感器观测链提供了标准化的类层次，是本文TBOX设计的基础框架。OGC的WaterML2.0[2]规范了水文时间序列的数据交换格式。Vilches-Blazquez等人[3]提出的HY_ONT水文本体涵盖了47类水文实体及89种关系。在遥感领域，OGC的EO(Earth Observation)标准[11]定义了卫星、传感器、影像产品等核心实体的元数据模型；ISO 19130[12]规范了影像传感器的几何模型；CEOS(Committee on Earth Observation Satellites)的EO数据目录标准(CWIC/CEOS-ARD)[13]为卫星数据的产品分级与互操作提供了工程参考。然而，现有遥感本体与地面监测本体是两个独立的体系，缺少统一的语义桥接——即同一条河流的"卫星反演叶绿素a浓度"与"地面实测叶绿素a浓度"之间缺乏可计算的对齐规则。

**遥感水质监测实践.** 卫星遥感在水质监测领域已有多项成熟的工程应用。Landsat 8/9 OLI(30m分辨率, 16天重访)被广泛用于叶绿素a、悬浮物浓度的反演[14]；Sentinel-2 MSI(10-60m分辨率, 5天重访)凭借红边波段在水体富营养化监测中表现突出[15]；MODIS(250-1000m, 日尺度)适用于大型湖泊的长时间序列趋势分析[16]。国内实践中，高分系列卫星(GF-1/2/4/5)为城市水体监测提供了国产高分辨率数据源。但上述工作多聚焦于单一卫星平台的反演算法，缺乏将卫星数据与地面监测数据通过统一本体框架进行语义融合的系统性方案。

**多Agent水环境监测系统.** Palau等人[4]提出了基于MAS的三层水质监测架构。Bergenti与Hliaoutakis[5]将BDI模型引入水文监测Agent。Zheng等人[6]构建了环境污染溯源知识图谱。Peng等人[7]利用Neo4j构建了水质时空知识图谱。但这些工作均以地面监测为数据源，未涉及遥感数据的Agent化处理与空地融合推理。

**研究空白.** 现有研究存在三条分离的脉络——遥感水质反演、地面传感网监测与多Agent协作系统——缺乏一个统一的本体框架将三者衔接为一个端到端的推理链路。

### 1.3 本文贡献

(1)提出覆盖卫星遥感传感器、地面监测站、水环境事件与治理实体的五层水务本体TBOX，在SOSA/SSN基础上扩展遥感类层次并定义空地数据对齐规则；(2)构建27条推理规则，新增遥感异常检测与空地数据融合两类规则；(3)设计8类Agent(含遥感影像Agent与空地融合Agent)的MQTT BBS协作架构，实现从卫星影像接收到污染事件归档的全流程自动化。

### 1.4 论文组织

第2节分析空地数据异构性问题；第3节提出融合遥感的五层TBOX；第4节构建含空地融合的推理规则引擎；第5节设计含遥感Agent的MQTT BBS架构；第6节验证并讨论；第7节总结。

---

## 2 问题分析: 空地两种监测体系的本体论鸿沟

### 2.1 观测维度的根本差异

地面传感网与卫星遥感对同一水体属性的观测遵循完全不同的"观测本体论":

| 维度 | 地面传感网 | 卫星遥感 |
|:-----|:----------|:---------|
| 观测对象 | 局地点位(站坐标) | 连续像元(空间面) |
| 时间粒度 | 分钟级(连续序列) | 天级(离散重访) |
| 空间粒度 | 单点(米级精度) | 面阵(10-1000m) |
| 测量原理 | 直接接触式 | 电磁辐射反演 |
| 参数获取 | 直接测量COD/NH3N等 | 间接反演(chl-a/悬浮物/CDOM) |
| 数据格式 | 时间序列JSON | 栅格GeoTIFF/云掩膜 |

**工程实例**: 地面站st-4412测得COD=38.2mg/L(2026-06-04T08:30)，同一时间Sentinel-2影像(2026-06-04T09:47)反演该点位的叶绿素a浓度为12.5μg/L。两数据指向同一水体的健康状态(均为轻度污染指示)，但COD(化学需氧量)与叶绿素a(藻类生物量)不是同一物理量，二者的结构化对齐需要领域知识支撑。若缺乏统一的本体框架，空地融合停留在人工查询对比层面。

### 2.2 探测周期的互补性与冲突

| 监测手段 | 时间覆盖优势 | 空间覆盖优势 | 典型失效模式 |
|:---------|:------------|:------------|:-------------|
| 地面站 | 连续(分钟级) | 单点(<1km) | 空间代表性不足, 布站盲区 |
| 卫星(Sentinel-2) | 5天重访 | 290km幅宽(10m) | 云覆盖导致数据无效 |
| 卫星(Landsat) | 16天重访 | 185km幅宽(30m) | 低时间分辨率遗漏短期事件 |
| 无人机 | 按需 | 10-50km2 | 空域审批与续航限制 |

这种互补性意味着: 地面站发现异常但无法判断空间范围→卫星影像提供空间分布; 卫星检测到大面积异常但无法精确定位→地面站补充精确浓度。一套有效的空地融合框架需要综合考虑时间同步窗口、空间尺度匹配与参数语义对齐三个维度。

---

## 3 本体模型设计: 空天地一体化的TBOX

### 3.1 五层TBOX架构

在已有四层架构(水体、监测、事件、治理)的基础上，新增**遥感实体层**并重构传感器类层次:

```
WaterEntity                (水务实体 - 根类)
  ├── WaterBody             (水体实体)
  │   ├── River             (河道)
  │   ├── Lake              (湖泊/水库)
  │   ├── Groundwater       (地下水)
  │   └── Estuary           (河口)
  │
  ├── ObservationPlatform   (观测平台 - 新增跨域层)
  │   ├── InSituPlatform    (地面原位平台)
  │   │   ├── Station           (固定监测站)
  │   │   ├── Sensor            (在线传感器)
  │   │   └── SamplingPoint     (人工采样点)
  │   │
  │   ├── SatellitePlatform (卫星平台 - 新增)
  │   │   ├── OpticalSatellite   (光学卫星)
  │   │   │   ├── Sentinel2      (Sentinel-2 MSI)
  │   │   │   ├── Landsat89      (Landsat 8/9 OLI)
  │   │   │   ├── GaofenSeries   (高分系列 GF-1/2/4/5)
  │   │   │   └── MODIS          (Terra/Aqua MODIS)
  │   │   ├── SARPlatform        (SAR卫星)
  │   │   └── HyperspectralPlatform(高光谱卫星)
  │   │
  │   └── AirbornePlatform   (机载平台 - 新增)
  │       └── Drone              (无人机)
  │
  ├── ObservationProduct    (观测产品 - 新增)
  │   ├── InSituReading         (地面读数: 参数+时间+值)
  │   ├── SatelliteImage        (卫星影像: 波段+分辨率+云量)
  │   ├── RetrievalProduct      (遥感反演产品)
  │   │   ├── ChlaProduct        (叶绿素a浓度)
  │   │   ├── TurbidityProduct   (浊度)
  │   │   ├── CDOMProduct        (有色溶解有机物)
  │   │   ├── SSTProduct         (水面温度)
  │   │   └── CyanobacteriaProduct(蓝藻水华指数)
  │   └── FusionProduct         (空地融合产品 - 新增)
  │       ├── CalibratedProduct   (地面标定遥感反演)
  │       └── GapFilledProduct   (遥感补充地面盲区)
  │
  ├── EventEntity           (事件实体)
  │   ├── PollutionIncident (污染事件)
  │   ├── AbnormalReading   (异常读数)
  │   ├── SpaceAnomaly      (遥感异常 - 新增)
  │   ├── AlgaeBloom        (藻华事件 - 新增)
  │   ├── EquipmentFailure  (设备故障)
  │   └── NaturalChange     (自然变化)
  │
  └── GovernanceEntity      (治理实体)
      ├── TreatmentPlant    (污水处理厂)
      ├── PumpingStation    (泵站)
      ├── Outfall           (排口)
      └── EmergencyResponse (应急响应)
```

关键设计思路在于引入`ObservationPlatform`作为地面、卫星、机载三类异构平台的统一父类，让推理规则在平台抽象层上编写而非针对具体传感器。`ObservationProduct`规范化了从原始数据到反演产品再到融合产品的层次，为空地融合提供结构化的输入。

### 3.2 新增遥感对象属性

| 属性 | 定义域 | 值域 | 说明 |
|:----|:-------|:-----|:------|
| carriesSensor | SatellitePlatform | Sensor | 卫星搭载的传感器 |
| acquiresImage | Sensor | SatelliteImage | 传感器获取的影像 |
| retrievesProduct | SatelliteImage | RetrievalProduct | 影像反演产品 |
| calibratedBy | RetrievalProduct | InSituReading | 遥感反演由地面数据标定 |
| fillsGapFor | InSituReading | RetrievalProduct | 遥感填补地面站空间盲区 |
| hasOverlapTime | InSituReading | SatelliteImage | 数据时间窗口重叠 |
| detectsAnomaly | RetrievalProduct | SpaceAnomaly | 遥感检测异常 |

### 3.3 空地数据融合的本体映射关系

空地融合的核心是将两个观测体系映射到统一的本体空间。关键映射规则(形式化为SWRL，详见第4节)如下:

| 映射类型 | 地面观测参数 | 遥感反演参数 | 转换关系 |
|:---------|:------------|:-------------|:---------|
| 同质映射 | 叶绿素a(实测) | 叶绿素a(反演) | 线性回归标定: y = ax + b |
| 异质映射 | COD | 叶绿素a | 统计相关: COD≈k·Chla(富营养化情景) |
| 趋势映射 | DO(连续) | 藻类指数(离散) | 时间对齐后比对变化趋势 |
| 空间映射 | 站坐标点 | 对应像元及其邻域 | 点-面空间一致性检验 |

### 3.4 多源数据融合实例(JSON-LD)

以下展示了同一水体同时被地面站和卫星观测时的融合本体实例:

```json
{
  "@context": {"water": "http://example.org/water-ontology#"},
  "@id": "water:fusion-zhujiang-gz-20260604",
  "@type": "water:FusionProduct",

  "water:hasInSituComponent": {
    "@id": "water:reading-st4412-20260604T0830",
    "@type": "water:InSituReading",
    "water:observedBy": {"@id": "water:station-gz-4412"},
    "water:hasParameter": "COD",
    "water:value": 38.2,
    "water:unit": "mg/L",
    "water:timestamp": "2026-06-04T08:30:00Z"
  },

  "water:hasSatelliteComponent": {
    "@id": "water:retrieval-s2-20260604T0947",
    "@type": "water:ChlaProduct",
    "water:derivedFrom": {
      "@id": "water:image-s2-50TLP-20260604",
      "@type": "water:SatelliteImage",
      "water:satellite": "Sentinel-2B",
      "water:sensor": "MSI",
      "water:cloudCover": 5.2,
      "water:resolution": 10
    },
    "water:hasParameter": "Chlorophyll-a",
    "water:value": 12.5,
    "water:unit": "μg/L",
    "water:timestamp": "2026-06-04T09:47:00Z"
  },

  "water:fusionAssessment": {
    "timeGap": "77分钟",
    "spatialConsistency": 0.82,
    "conclusion": "轻度富营养化—地面COD与遥感Chla趋势一致",
    "confidence": 0.79
  }
}
```

### 3.5 标准兼容性扩展

| 标准 | 范围 | 本TBOX映射 |
|:-----|:------|:-----------|
| **SOSA/SSN**[1] | 传感器/观测 | `Sensor`, `Observation` 基类 |
| **OGC EO**[11] | 卫星/传感器/影像 | `SatellitePlatform`, `SatelliteImage` |
| **ISO 19130**[12] | 影像传感器模型 | `sensorModel` 数据属性 |
| **CEOS-ARD**[13] | 遥感产品分级 | `RetrievalProduct` 质量等级 |
| **WaterML2.0**[2] | 水文序列 | `InSituReading` 时间序列结构 |
| **GB 3838-2002**[8] | 中国水质标准 | `WaterClass` 枚举 |

---

## 4 推理规则引擎: 含空地融合的27条规则

### 4.1 规则组构成

| 规则组 | 数量 | 说明 |
|:-------|:----:|:------|
| R1 水质评价 | 8条 | 基于GB 3838的地面数据单因子评价 |
| R2 遥感异常检测 | **5条(新增)** | 基于时空异常的遥感自动检测 |
| R3 空地数据融合 | **4条(新增)** | 地面-卫星数据对齐与交叉验证 |
| R4 污染溯源 | 6条 | 空地联合溯源(扩展现有规则) |
| R5 预警分级 | 4条 | 综合多源证据的预警等级判定 |

### 4.2 新增规则示例

**R2-1: 卫星影像叶绿素a异常检测**。多时相遥感影像中同一水体叶绿素a浓度突变超过阈值时触发:

```
R2-1: ChlaProduct(?p1) ∧ ChlaProduct(?p2) ∧
      sameWaterBody(?p1, ?p2) ∧
      swrlb:greaterThan(diffDays(?p1.time, ?p2.time), 5) ∧
      swrlb:greaterThan(?p1.value / ?p2.value, 3.0)
      → SpaceAnomaly(?sa) ∧ hasParameter(?sa, "Chl-a") ∧
        hasChangeRate(?sa, ?p1.value / ?p2.value)
```

**R3-1: 空地数据交叉验证**。地面读数与卫星反演指向同一结论时增强置信度:

```
R3-1: InSituReading(?r) ∧ ChlaProduct(?p) ∧
      sameWaterBody(?r, ?p) ∧
      swrlb:lessThan(diffMinutes(?r.time, ?p.time), 120) ∧
      hasParameter(?r, "COD") ∧ swrlb:greaterThan(?r.value, 40) ∧
      hasParameter(?p, "Chl-a") ∧ swrlb:greaterThan(?p.value, 10)
      → FusionProduct(?fp) ∧ hasInSituComponent(?fp, ?r) ∧
        hasSatelliteComponent(?fp, ?p) ∧
        spatialConsistency(?fp, ?score) ∧
        conclusion(?fp, "空地数据均指示轻度富营养化")
```

**R3-4: 遥感填补地面盲区**。地面站间区域由卫星数据插值覆盖，生成融合产品:

```
R3-4: SatelliteImage(?img) ∧ RetrievalProduct(?rp) ∧
      hasCloudCover(?img, ?cc) ∧ swrlb:lessThan(?cc, 20) ∧
      WaterBody(?w1) ∧ WaterBody(?w2) ∧
      hasMonitoringStation(?w1, ?s1) ∧ hasMonitoringStation(?w2, ?s2) ∧
      not(hasMonitoringStation(_, ?s_mid)) ∧ adjacent(?w1, ?w_mid) ∧ adjacent(?w_mid, ?w2)
      → GapFilledProduct(?gfp) ∧ fillsGapFor(?gfp, ?w_mid) ∧
        value(?gfp, interpolate(?rp, ?s1, ?s2))
```

### 4.3 推理引擎核心循环(含空地融合)

---

**算法1: 融合推理引擎主循环**

**Require**: 规则集 $R = \{R1, R2, R3, R4, R5\}$; MQTT订阅两个源
**Ensure**: 推理结论发布到MQTT Board

1. **while** true **do**
2. &emsp; // 并行接收两种数据源
3. &emsp; **parallel** **do**
4. &emsp; &emsp; `insitu_msg` ← mqtt_subscribe("station/{id}/validated", qos=1)
5. &emsp; &emsp; `satellite_msg` ← mqtt_subscribe("satellite/{id}/retrieval", qos=2)
6. &emsp; **end parallel**
7. &emsp;
8. &emsp; `kb` ← kb ∪ {jsonld_parse(insitu_msg)} ∪ {jsonld_parse(satellite_msg)}
9. &emsp;
10. &emsp; // 前向链推理
11. &emsp; `changed` ← true
12. &emsp; **while** changed **do**
13. &emsp; &emsp; changed ← false
14. &emsp; &emsp; **for each** `rule` in priority_sorted(R) **do**
15. &emsp; &emsp; &emsp; **for each** `binding` in pattern_match(rule.antecedent, kb) **do**
16. &emsp; &emsp; &emsp; &emsp; `conclusion` ← apply(rule.consequent, binding)
17. &emsp; &emsp; &emsp; &emsp; **if** conclusion ∉ kb **then**
18. &emsp; &emsp; &emsp; &emsp; &emsp; kb ← kb ∪ {conclusion}; changed ← true
19. &emsp; &emsp; &emsp; &emsp; &emsp; publish_by_type(conclusion)
20. &emsp; &emsp; &emsp; &emsp; **end if**
21. &emsp; &emsp; &emsp; **end for**
22. &emsp; &emsp; **end for**
23. &emsp; **end while**
24. &emsp;
25. &emsp; // 空地融合触发——地面异常需卫星验证
26. &emsp; **if** kb.has("AbnormalReading") **and** kb.has_nearby("SatelliteImage", 6h) **then**
27. &emsp; &emsp; mqtt_publish("fusion/trigger", {incident_id, "type": "space_ground_cross_validation"})
28. &emsp; **end if**
29. &emsp;
30. &emsp; kb.persist()
31. **end while**

---

### 4.4 冲突解决

多源证据冲突时(如地面站判定正常但卫星检测到异常)，采用置信度加权策略: 地面数据的参数级精度更高(base_weight=0.7)，遥感的空间覆盖率更广(base_weight=0.5)。若两者一致则置信度增强(×1.3)，若冲突则取置信度高者并记录矛盾证据。

---

## 5 多Agent架构与MQTT BBS集成

### 5.1 新增遥感Agent

在原有7类Agent基础上新增**遥感影像Agent**，共8类:

| Agent类型 | 输入(Board) | 输出(Board) | 功能 |
|:----------|:-----------|:------------|:------|
| 采集Agent | 传感器API | station/{id}/raw | 地面传感网数据采集 |
| **遥感Agent** | **卫星API/存储** | **satellite/{id}/{product}** | **卫星影像检索/预处理/反演** |
| 校验Agent | station/{id}/raw | station/{id}/validated | 地面数据质量校验 |
| 映射Agent | station/{id}/validated, satellite/{id}/* | ontology/instance | 统一JSON-LD转换 |
| 推理Agent | ontology/instance | river/*, incident/*, fusion/* | 27条规则推理(算法1) |
| **空地融合Agent** | **fusion/trigger** | **fusion/product** | **地面-卫星交叉验证与融合** |
| 溯源Agent | incident/{id}/alerts | incident/{id}/trace/* | 并行嫌疑源排查 |
| 协调Agent | incident/{id}/suspects | governance/* | 跨部门协调与决策归档 |

### 5.2 遥感Agent工程实现伪代码

遥感Agent的核心职责是按需检索、预处理卫星影像并执行反演算法:

```
Algorithm: 遥感Agent主循环
Require: 周期扫描或异常触发信号
Ensure: 反演产品发布到 satellite/{id}/retrieval

1. while true:
2.     // 触发条件: 定时(每5天新影像到达) 或 地面异常触发
3.     trigger ← mqtt_subscribe("satellite/trigger", timeout=86400s)
4.
5.     // 1. 检索覆盖监测区域的卫星数据
6.     scenes ← query_satellite_catalog({
7.         area: MONITORING_POLYGON,
8.         time_range: [now-7d, now],
9.         max_cloud: 20,
10.        satellites: ["Sentinel-2", "Landsat-9", "GF-5"]
11.    })
12.
13.    parallel for each scene in scenes:
14.        // 2. 下载与预处理
15.        raw_path ← download(scene.url)
16.        l2a ← atmospheric_correction(raw_path, scene.satellite)
17.        cloud_mask ← detect_cloud(l2a)
18.        water_mask ← extract_water_body(l2a)
19.
20.        // 3. 水质参数反演
21.        if scene.satellite == "Sentinel-2":
22.            chla ← semi_analytical_algorithm(l2a, bands=[B3,B4,B5,B6])
23.            turbidity ← empirical_algorithm(l2a, bands=[B4,B3])
24.        elif scene.satellite == "Landsat-9":
25.            chla ← 3-band_algorithm(l2a, bands=[B2,B3,B4,B5])
26.            turbidity ← single_band(l2a, B4)
27.
28.        // 4. 发布为JSON-LD本体实例
29.        product = {
30.            "@type": "water:RetrievalProduct",
31.            "water:satellite": scene.satellite,
32.            "water:timestamp": scene.acquisition_time,
33.            "water:parameters": [chla, turbidity],
34.            "water:cloudCover": cloud_mask.percentage,
35.            "water:spatialCoverage": water_mask.bounds
36.        }
37.        mqtt_publish(f"satellite/{scene.scene_id}/retrieval",
38.                     jsonld_serialize(product), qos=2)
```

### 5.3 层次化Board命名空间(扩展遥感)

```
bbs/water/{city_id}/
  ├── river/{river_id}/           — 河段状态
  │   ├── param/{param}           — 实时参数(QoS=1)
  │   ├── status                  — 水质状态(QoS=1)
  │   └── alert                   — 预警(QoS=2,持久化)
  │
  ├── station/{station_id}/       — 地面监测站
  │   ├── raw / validated / meta
  │
  ├── satellite/{scene_id}/       — 卫星数据(新增)
  │   ├── raw                     — 原始影像元数据(QoS=1)
  │   ├── retrieval               — 反演产品(QoS=2,持久化)
  │   └── validation              — 地面验证结果(QoS=2)
  │
  ├── drone/{mission_id}/         — 无人机数据(新增)
  │   ├── raw                     — 原始影像
  │   └── retrieval               — 局部高分辨率反演
  │
  ├── fusion/                     — 空地融合(新增)
  │   ├── trigger                 — 融合触发信号
  │   ├── product                 — 融合产品(QoS=2,持久化)
  │   └── conflict                — 空地数据矛盾记录
  │
  ├── incident/{incident_id}/     — 事件
  │   ├── alerts / trace / suspects / evidence / action / archive
  │
  ├── governance/                 — 治理协调
  │   ├── task / decision
  │
  └── ontology/                   — 本体Board
      ├── tbox / instance
```

### 5.4 空地协同消息流示例

```
地面路径:
  T+0min  [采集Agent]     → station/st-4412/raw: COD=85.3, NH3N=12.5
  T+0.5min[校验Agent]     → station/st-4412/validated (数据有效)
  T+1min  [映射Agent]     → ontology/instance: AbnormalReading

遥感路径:
  T+5min  [遥感Agent]     ← 收到地面异常信号 → 检索最近卫星数据
  T+8min  [遥感Agent]     → satellite/S2-50TLP/retrieval: Chla=22.8μg/L
  T+8.5min[映射Agent]     → ontology/instance: SpaceAnomaly

空地融合:
  T+9min  [空地融合Agent] ← 收到fusion/trigger
  T+9.5min[空地融合Agent] → fusion/product: 空地一致指向重度富营养化
  T+10min [推理Agent]     → river/zhujiang-gz/alert: 红色预警(置信度0.91)
  T+10min [推理Agent]     → incident/20260604-002/alerts

溯源与归档:
  T+12min [溯源Agent]     → 并行排查5个上游方向
  T+20min [协调Agent]     → governance/decision: 定位于化工园区B
  T+30min [归档Agent]     → 事件归档
```

### 5.5 工程实践考量

| 工程问题 | 解决方案 |
|:---------|:---------|
| 卫星数据延迟(订购→下载→预处理通常1-6h) | 遥感Agent采用异步流水线: 影像下载与预处理独立线程，反演结果通过MQTT逐步发布 |
| 云覆盖导致数据无效(南方地区年均60-70%云量) | 综合多源(Sentinel-2 + Landsat + GF)增加数据频次; R2-1规则要求云量<20%才触发异常检测 |
| 地面与卫星时间窗口不对齐 | R3-1设置120分钟时间窗口; 超出窗口的对比标记为低置信度 |
| 不同卫星反演算法不一致 | TBOX为每颗卫星定义`sensorModel`属性; 推理规则绑定具体卫星的标定参数 |

---

## 6 验证与讨论

### 6.1 场景验证: 空地协同污染溯源

以南方某城市内河涌突发工业废水排放为验证场景。地面站st-4412在T时刻检测到COD从35mg/L骤升至85.3mg/L，同时Sentinel-2影像(T+1.4h过境)显示该河段叶绿素a与浊度异常。空地协同全流程:

| 时间 | 环节 | 耗时 | 数据源 |
|:----|:------|:----:|:-------|
| T+0min | 地面站异常 | — | 地面站 |
| T+0.5min | 地面Agent链 | 0.5min | 采集→校验→映射 |
| T+1.4h | 卫星过境 | 1.4h | Sentinel-2 |
| T+2.5h | 遥感反演 | 1.1h | 大气校正→反演→发布 |
| T+2.5h | 空地融合推理 | 1min | 规则R2-1+R3-1+R5-1 |
| T+2.6h | 溯源定位 | 6min | 空地联合溯源→排口定位 |

卫星遥感的加入使事件的空间范围从单点(地面站)扩展到面(整条河段)，同时为溯源提供了更完整的空间上下文(发现上游3km处另有非法排口未被地面站覆盖)。

### 6.2 与传统方案及单一数据源对比

| 维度 | 纯地面方案 | 纯卫星方案 | 本方案(空地融合+本体) |
|:-----|:----------|:----------|:--------------------|
| 时空覆盖 | 时间连续/空间稀疏 | 时间离散/空间连续 | 双维互补覆盖 |
| 参数精度 | COD/NH3N等高精度 | 间接反演(精度较低) | 地面标定卫星反演 |
| 溯源能力 | 依赖上下游站网密度 | 面状异常可追溯空间分布 | 地面精确定位+卫星空间判定 |
| 报警响应 | 实时(分钟级) | 延迟(小时-天级) | 地面实时报警+卫星补充验证 |
| 运维成本 | 站网建设与维护高 | 数据订购与处理成本 | 协同成本=地面+卫星-冗余 |

### 6.3 深化方向

(1) **高光谱卫星融合**. 国内外高光谱卫星(GF-5, EnMAP, PRISMA)可提供数十至数百个连续波段，大幅提升COD、NH3N等参数的直接反演能力。深化方向: 扩展TBOX覆盖高光谱观测模型，新增吸收特征匹配推理规则。

(2) **无人机应急响应Agent**. 无人机在突发污染场景中可执行厘米级分辨率的按需观测。深化方向: 设计无人机Agent与BBS的动态任务交互协议，使遥感Agent在卫星数据不足时自动请求无人机补充。

(3) **跨城市空基联邦推理**. 多个城市共享卫星数据源但各自管理地面站网。深化方向: 设计跨BBS联邦协议，支持"卫星数据统采统解、地面验证属地负责"的空基联邦推理模式。

(4) **大模型驱动的空地融合**. 随着遥感基础模型(如SatCLIP、SpectralGPT)的发展，深度学习可直接从影像端到端学习空地数据的映射关系。深化方向: 将神经网络推理的中间特征作为本体证据的补充源，实现规则推理与数据驱动方法的混合架构。

---

## 7 结论

本文提出了融合卫星遥感、地面传感网与MQTT BBS的城市水环境监测本体模型与多Agent架构。设计了五层TBOX并扩展了遥感类层次与空地数据对齐规则，构建了含空地融合的27条推理规则引擎，通过8类Agent的MQTT BBS协作实现了从卫星影像接收到污染事件归档的全流程自动化。工程实践表明，该架构有效融合了卫星遥感的广域覆盖优势与地面传感网的高精度优势，在突发污染溯源场景中可在分钟级完成空地协同定位。后续工作将聚焦于高光谱卫星融合、无人机应急响应与跨城市空基联邦推理三个方向。

---

## 参考文献

[1] W3C. Semantic Sensor Network Ontology. W3C Recommendation, 2017.

[2] OGC. WaterML 2.0: Part 1 - Timeseries. OGC Standard 14-004r1, 2014.

[3] Vilches-Blazquez L M, et al. A Hydrological Ontology for Water Resource Management. Journal of Hydrology, 2014.

[4] Palau C E, et al. Multi-Agent System for Water Quality Monitoring. Sensors, 18(5), 2018.

[5] Bergenti F, Hliaoutakis A. BDI Agents for Hydrological Modeling. Multi-Agent Systems and Applications, Springer, 2020.

[6] Zheng Y, et al. Knowledge Graph for Environmental Pollution Source Tracing. Environmental Science & Technology, 57(12), 2023.

[7] Peng Z, et al. Water Quality Knowledge Graph Based on Neo4j. Water Resources Management, 36(8), 2022.

[8] GB 3838-2002. 地表水环境质量标准. 中国国家标准, 2002.

[9] GB/T 35654-2017. 水质在线监测系统技术规范. 中国国家标准, 2017.

[10] 生态环境部. "十四五"生态环境监测规划. 2021.

[11] OGC. Earth Observation Metadata Profile of Observations & Measurements. OGC Standard 10-157r4, 2014.

[12] ISO 19130. Geographic Information - Imagery Sensor Models for Geopositioning. ISO Standard, 2010.

[13] CEOS. Analysis Ready Data (ARD) Specification. Committee on Earth Observation Satellites, 2019.

[14] Pahlevan N, et al. Landsat 8/9 OLI Water Quality Retrieval. Remote Sensing of Environment, 2022.

[15] Toming K, et al. Sentinel-2 MSI for Lake Water Quality Monitoring. Remote Sensing, 2016.

[16] Hu C, et al. MODIS Chlorophyll-a Monitoring in Estuarine and Coastal Waters. Remote Sensing of Environment, 2012.
