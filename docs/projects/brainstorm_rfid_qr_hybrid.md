# Brainstorm 续: QR Code 巡检方案 + 巡视员到点报工

续上: docs/brainstorm_rfid_ontology_building.md
日期: 2026-05-21

---

## 1. QR Code vs RFID 核心对比

| 维度 | RFID (原方案) | QR Code (替代方案) | 胜负 |
|------|-------------|-------------------|------|
| **单点成本** | 3-15元/标签(HF) + 2000-5000元/手持Reader | 0.01-0.1元/标签(印刷) + 0元(用手机) | QR胜 |
| **读取方式** | 非接触式, 批量读取(每秒100+) | 需对准扫描, 单次1个 | RFID胜 |
| **穿透性** | 可穿透混凝土/涂料 | 必须可视, 表面清洁 | RFID大胜 |
| **金属环境** | 需抗金属标签(成本更高) | 无影响(纯视觉) | QR胜 |
| **数据容量** | EPC 96-496bit, User 8KB | 最多3KB(Version 40) | QR稍胜 |
| **耐久性** | 工业级, 10年+ | 印刷易磨损/污损/遮挡 | RFID大胜 |
| **批量巡检** | 走过即读, 全自动 | 必须逐一对准扫描 | RFID大胜 |
| **传感能力** | 可集成温湿度/振动传感器 | 无(纯标识) | RFID胜 |
| **防篡改** | 内埋/封装难破坏 | 表面粘贴, 可被覆盖替换 | RFID胜 |
| **部署门槛** | 需专用硬件+培训 | 手机扫码, 零培训 | QR胜 |
| **更换成本** | 需专业工具重新写入 | 打印即用, 快速更换 | QR胜 |

**结论: 没有绝对优劣, 场景决定选择。**

| 适用场景 | 推荐方案 |
|---------|---------|
| 关键承重构件(需长期/内埋) | RFID (抗金属封装) |
| 一般可见构件(梁/墙/幕墙) | QR Code |
| 高频巡检点(每日) | QR + NFC 双标签 |
| 隐蔽/难到达区域(管道井/吊顶内) | RFID |
| 临时/短期项目 | QR Code |
| 租户区域/非自持物业 | QR Code (成本低 > 更换灵活) |

---

## 2. 推荐: 双模混合方案

```
┌─────────────────────────────────────────────────────────┐
│              双模混合巡检方案                              │
│                                                         │
│  Tier 1: 核心结构件 → RFID (内埋/抗金属封装)              │
│    - 梁/柱/基础/关键节点                                  │
│    - 物业用RFID手持Reader快速通道式巡检                    │
│    - 自动批量读取, 无人为操作变量                          │
│                                                         │
│  Tier 2: 一般构件 + 巡检点 → QR Code (304不锈钢铭牌)     │
│    - 墙体/幕墙/门窗/管道/设备                             │
│    - 巡检员手机扫码 → 到点报工 + 状态填报                  │
│    - 可拍照上传现场照片                                   │
│                                                         │
│  Tier 3: 双标签交叉验证 (关键节点)                        │
│    - 同一构件同时贴RFID+QR                                │
│    - RFID自动读 + QR手动扫码确认 = 双重验证               │
│    - 用于"必须亲眼确认"的高风险点                          │
└─────────────────────────────────────────────────────────┘
```

---

## 3. QR Code 技术选型

| 项目 | 建议 | 理由 |
|------|------|------|
| **码制** | QR Code (不是Data Matrix/PDF417) | 手机原生支持, 纠错等级高 |
| **纠错等级** | H (30%纠错) | 污损/划伤后仍可读取 |
| **材质** | 304不锈钢激光蚀刻铭牌 | 户外5年+不褪色, 抗UV抗腐蚀 |
| **安装** | 结构胶+铆钉 | 防脱落, 防移位 |
| **尺寸** | 30x30mm - 50x50mm | 远距离(3m)用大码, 近距离用小码 |
| **编码内容** | **仅编码ID(32位UUID)** | 所有关联信息存在服务器, 扫码后查询 |
| **防伪** | 二维码+微缩文字/紫外荧光覆层 | 防止复印冒扫 |
| **数量** | 无感印刷, 钢制 | 长寿命, 也 |

### 为什么不把信息直接写入QR Code?

```
[错误做法] QR码内容: {"building":"A","floor":"3","component":"B12","installDate":"2020-01-01"}
  问题:
  - QR容量有限(3KB), 编码大量静态信息浪费空间
  - 信息更新必须重新打印贴纸
  - 扫描二维码 === 暴露底层数据

[正确做法] QR码内容: https://buildingscanner.cn/c/7f3a1b2c
  或: 纯ID: 7f3a1b2c-d8e4-4f12-9a3c-0b1e2f3a4b5c
  优点:
  - 扫码后实时从数据库获取最新状态
  - 更新信息无需换码
  - 可做URL跳转(扫码直接打开构件详情页)
  - 支持动态二维码(可更换目标URL)
```

---

## 4. 巡视员到点报工系统设计

### 4.1 核心机制

```
┌────────────────────────────────────────────┐
│           到点巡视报工流程                     │
├────────────────────────────────────────────┤
│                                            │
│  调度层:                                     │
│    ┌──────────────────────────────────┐     │
│    │ 每日自动生成巡检工单                │     │
│    │  - 根据构件风险等级排优先级          │     │
│    │  - 规划最优巡检路线(路径优化)        │     │
│    │  - 分配给对应资质的巡检员            │     │
│    │  - 预计工时: 30个点/小时            │     │
│    └──────────────────────────────────┘     │
│                    │                        │
│                    ▼                        │
│  执行层:                                     │
│    ┌──────────────────────────────────┐     │
│    │ 巡检员手机扫码 → 到点报工           │     │
│    │  1. 扫码(QR) → 记录时间戳+GPS     │     │
│    │  2. 选择构件状态(正常/异常/无法判断)  │     │
│    │  3. 异常时: 拍照 + 语音备注         │     │
│    │  4. 提交 → MQTT → 数据库+告警引擎  │     │
│    └──────────────────────────────────┘     │
│                    │                        │
│                    ▼                        │
│  核验层:                                     │
│    ┌──────────────────────────────────┐     │
│    │ 后台交叉验证                       │     │
│    │  - GPS距离: 扫码位置vs构件位置 < 5m│     │
│    │  - 时间间隔: 相邻扫码 > 30秒(防刷) │     │
│    │  - 照片AI识别: 确认是目标构件       │     │
│    │  - 漏检标记: 未扫点自动升级告警     │     │
│    └──────────────────────────────────┘     │
│                    │                        │
│                    ▼                        │
│  统计层:                                     │
│    ┌──────────────────────────────────┐     │
│    │ 巡检员绩效面板                     │     │
│    │  - 今日已检 / 应检 / 漏检         │     │
│    │  - 平均逗留时间(扫码到提交)        │     │
│    │  - 异常发现率 / 误报率            │     │
│    │  - 路线偏离度                     │     │
│    └──────────────────────────────────┘     │
└────────────────────────────────────────────┘
```

### 4.2 MQTT 主题: 巡检报工

```
inspection/{buildingId}/
  ├── dispatch/{inspectorId}         # 巡检员工单下发 (保留消息)
  ├── checkin/{pointId}              # 到点扫码事件
  │   payload: {
  │     "inspector": "ZHANG_SAN",
  │     "pointId": "B12-C17",
  │     "scanTime": "2026-05-21T09:30:00+08:00",
  │     "gps": {"lat": 22.5431, "lng": 114.0579},
  │     "photo": ["url1", "url2"],
  │     "status": "NORMAL",          # NORMAL / ABNORMAL / UNABLE
  │     "note": "焊缝外观良好，无可见裂纹",
  │     "weather": "CLEAR"
  │   }
  ├── abnormal/{pointId}             # 异常上报
  ├── route/{inspectorId}/plan       # 当日路线规划
  └── route/{inspectorId}/deviation  # 路线偏离告警
```

### 4.3 防作弊机制

| 作弊手段 | 检测方式 | 处置 |
|---------|---------|------|
| 远程截图扫码(不到场) | GPS位置校验 < 5m + 蓝牙beacon校验 | 标记为"疑似未到岗" |
| 一次性扫码多个点 | 扫描间隔 < 30秒 自动标记 | 要求该点重新拍照 |
| 代扫/代签 | 人脸识别 + 设备指纹 | 记录代扫日志, 绩效扣分 |
| 同一照片多次上传 | 照片哈希碰撞检测 | 拒绝重复照片 |
| 虚构异常上报 | AI图片分析 + 异常率统计偏离检测 | 标记为"可疑异常, 需复核" |

---

## 5. 本体扩展: 巡检点与报工

### 5.1 新增 OWL 类

```
InspectionPoint (巡检点)
  ├── StructuralPoint (结构巡检点)
  ├── EquipmentPoint (设备巡检点)
  ├── SafetyPoint (安全巡检点)
  └── EnvironmentPoint (环境巡检点)

QRLabel (二维码标签)
  ├── StainlessSteelLabel (304不锈钢铭牌)
  └── AdhesiveLabel (粘贴式标签)

CheckInEvent (到点报工事件)
  ├── NormalCheckIn (正常到点)
  ├── AbnormalCheckIn (异常上报)
  └── MissedCheckIn (漏检自动生成)

Inspector (巡检员)
  ├── CertifiedInspector (持证巡检员)
  └── TraineeInspector (实习巡检员)

InspectionRoute (巡检路线)
  ├── PlannedRoute (计划路线)
  └── ActualRoute (实际路线)
```

### 5.2 新增对象属性

```
InspectionPoint ──hasLabel──> QRLabel
InspectionPoint ──belongsTo──> BuildingComponent
Inspector ──performs──> CheckInEvent
CheckInEvent ──atPoint──> InspectionPoint
CheckInEvent ──hasPhoto──> PhotoEvidence
InspectionRoute ──includes──> InspectionPoint
Inspector ──assignedRoute──> InspectionRoute
```

### 5.3 新增数据属性

```
InspectionPoint:
  - hasExpectedDuration (int, seconds)   // 建议逗留时间
  - hasInspectionFrequency (string: DAILY/WEEKLY/MONTHLY)
  - hasLastCheckInTime (dateTime)
  - hasConsecutiveMisses (int)

CheckInEvent:
  - hasGPSLatitude (float)
  - hasGPSLongitude (float)
  - hasScanDuration (int, seconds)     // 扫码到提交耗时
  - hasPhotoHash (string)
  - hasDeviceFingerprint (string)

Inspector:
  - hasEmployeeId (string)
  - hasCertificationLevel (int)
  - hasTodayCompleted (int)
  - hasTodayAssigned (int)
  - hasAvgScanTime (float, seconds)
  - hasAbnormalFindRate (float, 0-1)
```

### 5.4 新增 SWRL 规则

```swrl
// 规则5: 漏检升级
InspectionPoint(?p) ^ hasConsecutiveMisses(?p, ?m) ^
  swrlb:greaterThan(?m, 3)
  -> hasAlertLevel(?p, "ESCALATED") ^
     notifySupervisor(?p, "连续3次漏检")

// 规则6: 逗留时间异常
CheckInEvent(?e) ^ atPoint(?e, ?p) ^
  hasExpectedDuration(?p, ?exp) ^
  hasScanDuration(?e, ?actual) ^
  swrlb:lessThan(?actual, ?exp * 0.3)
  -> flagSuspiciousCheckIn(?e)

// 规则7: 到点率考核
Inspector(?i) ^ hasTodayAssigned(?i, ?total) ^
  hasTodayCompleted(?i, ?done) ^
  swrlb:greaterThan(?total - ?done, 3)
  -> generateMissingAlert(?i)

// 规则8: 异常发现率过低
Inspector(?i) ^ hasAbnormalFindRate(?i, ?rate) ^
  swrlb:lessThan(?rate, 0.01)  // 发现率<1%
  -> flagInspectorForReview(?i, "异常发现率异常偏低")
```

---

## 6. 评估: QR替代RFID的净收益

### 正面 (Pro QR)

| 方面 | 收益 |
|------|------|
| 成本 | 单栋楼 RFID方案约20-50万(标签+Reader), QR方案约1-3万(不锈钢铭牌) |
| 部署速度 | RFID需专业安装+调试, QR仅需贴+打印, 1天vs2周 |
| 巡检员接受度 | 手机操作 vs 专用手持设备, 培训成本降低90% |
| 到点报工 | QR天然适合扫码签到, RFID需要额外软件层实现 |
| 照片证据 | 扫码同时拍照, 一体化操作 |
| 灵活性 | 增删改点无需重写RFID, 打印新码即可 |

### 负面 (Con QR)

| 方面 | 妥协 |
|------|------|
| 读取效率 | RFID 1秒读100个 vs QR 逐一扫描, 大面积巡检RFID效率高 |
| 隐蔽构件 | 管道井/吊顶内QR不可见, RFID可穿透 |
| 耐久性 | 304不锈钢铭牌可用10年, 但不如内埋RFID(50年) |
| 自动化 | RFID可实现"路过即读", QR必须主动扫 |
| 传感能力 | QR无法集成传感器, RFID芯片可集成温湿度/振动 |

### 优化决策矩阵

```
                                RFID        QR       混合(Hybrid)
                               ─────      ────      ──────────
关键承重构件(内埋)                ✓✓✓        ✗        RFID only
表面可见构件(梁/墙)               ✓✓        ✓✓        QR为主, R
================================================================

MERGED:

关键承重构件(内埋)                ✓✓✓        ✗        RFID only
表面可见构件(梁/墙)               ✓          ✓✓        QR为主, RFID抽检
巡检点(无构件关联)                 ✗         ✓✓✓       QR only
高频巡检区域(每日)                ✓✓        ✓         QR+RFID双标签
隐蔽区域(管道井/吊顶)             ✓✓✓        ✗        RFID only
租户区域                          ✗         ✓✓✓       QR only
```

---

## 7. 最终推荐方案

> **Tier 1:** 关键结构构件 → RFID (内埋/抗金属封装, 自动通道巡检)
> **Tier 2:** 一般构件+巡检点 → 304不锈钢QR铭牌 (手机扫码报工)
> **Tier 3:** 高风险节点 → 双标签(RFID+QR) 交叉验证
> **Tier 4:** 巡检员监督 → GPS+照片+时间三重防作弊, 绩效自动统计
> **Tier 5:** 到点报工 → MQTT实时上报, 漏检自动升级, 工单闭环

这种混合方案结合了RFID的自动化读取能力和QR的低成本+到点报工能力, 总成本约为纯RFID方案的40%, 但覆盖率和可靠性兼顾。
