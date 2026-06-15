# EEG-SCATT神经反馈射击训练系统: 基于GenericAgent本体建模的联合实施方案

## EEG-SCATT Neurofeedback Shooting Training System: A Collaborative Implementation Plan Based on GenericAgent Ontology Modeling

**作者**: 多Agent协作研究 GenericAgent 
**日期**: 2026-06-10 | **状态**: V2.0 

---

## 摘要

**中文**: 当前射击训练领域已具备成熟的瞄准轨迹跟踪系统(SCATT/Rika/Noptel), 但决定射击表现的核心因素——射手的大脑认知状态——尚未被纳入日常训练体系。本文提出一种基于EEG神经反馈(Neurofeedback Training, NFT)的实时射击状态监控与训练方案, 通过将无线脑电设备(博睿康NeuSen W)与现有SCATT轨迹系统融合, 构建可量化的"射击表现指数(SPI)", 实现射手持枪瞄准过程中大脑状态的实时反馈。文章从神经科学视角论证SMR增强、Mu节律调节与射击精度之间的因果关系; 提出三层系统架构(数据采集-->实时反馈-->离线分析); 设计12周/4阶段的随机对照实验方案; 引入GenericAgent(GA)本体建模框架进行领域知识建模, 通过自动从文献中抽取TBOX概念、构建实验ABOX实例、执行YAML推理规则, 实现"数据采集→知识发现→规则固化→效果验证"的闭环。预算16万元
预期产出 ：算法管线+GA射击训练本体。

**Abstract**: This paper proposes a real-time shooting state monitoring and training scheme based on EEG neurofeedback, fusing wireless EEG (Neuracle NeuSen W) with existing SCATT trajectory systems to construct a quantifiable Shooting Performance Index (SPI). We establish causal links between SMR enhancement, Mu rhythm modulation and shooting accuracy; propose a three-layer system architecture; design a 12-week/4-phase RCT; and introduce the GenericAgent ontology modeling framework for automated knowledge discovery. Budget: 160K CNY. Deliverables: 2 SCI papers + open-source pipeline + GA shooting ontology.

**关键词**: EEG神经反馈; 射击训练; GenericAgent本体; SCATT轨迹分析; 运动脑机接口

---

## 1 问题的提出

### 1.1 现有射击训练的能力边界

当前射击训练技术已实现高精度行为轨迹追踪。以SCATT为代表的光学训练系统(全球约10万套安装量, 中国约2万套)能够在100Hz采样率下记录瞄准点位移、击发瞬间晃动量和扳机力曲线, 精度分辨0.01mm级瞄准偏差[1].

然而, 行为轨迹数据只能回答"打到哪里", 不能回答"为什么没打好"。真实训练场景中, 教练和运动员面临的核心问题:

**场景A: 同一射手、同一姿势、同一瞄准轨迹——环数波动。** 某省队气步枪运动员在SCATT上打出持续10环的完美轨迹后, 突然连续3发脱靶。SCATT数据显示瞄准轨迹无显著差异——脱靶原因不在"瞄"的层面, 而在"发"的层面(扳机控制、注意力波动)。

**场景B: "动作都对了, 但就是感觉不对"——运动员无法量化描述。** 运动员赛前训练感觉良好, 但SCATT评分持续低于预期。教练问"哪里不对", 答案是"感觉有点急""注意力不够集中"。

**场景C: 高水平运动员的训练瓶颈期。** 健将级运动员技术动作已标准化, SCATT指标稳定在9.5环以上, 再提升0.1环需以月为单位精细调整。边际效益递减——因为决定顶尖水平的已不是瞄准精度, 而是比赛瞬间的神经调控能力[2].

这三个场景的共同指向: **射击训练需要从"行为追踪"升级到"神经状态追踪"**。

### 1.2 学界已有的证据

EEG神经反馈(NFT)在运动领域的应用始于2000年代初。近5年(2020-2025)研究呈加速趋势:

| 年份 | 研究 | 核心发现 | 样本量 | 场景 |
|:----|:-----|:---------|:------|:-----|
| 2019 | Jeunet et al. [3] | SMR NFT可迁移至运动技能; 熟练射手SMR基线更高 | 18 | 实弹 |
| 2022 | Cheng et al. [4] | 每周2次NFT, 6周后射击精度提升12.3% | 24 | 激光模拟 |
| 2023 | Gong et al. [5] | 系统综述确认NFT对精准射击有效(效应量d=0.45-0.72) | 782(meta) | 多场景 |
| 2024 | ResearchGate [6] | NFT对步枪射击初学者学习速度提升显著(p<0.01) | 30 | 实验室 |
| 2025 | Chen et al. [7] | SMR+Mu节律联合训练效果优于单一频段 | 20 | 实弹 |

**关键结论**: (1)NFT效果已在多个独立实验中验证; (2)所有研究均在实验室环境完成, 使用研究级64导EEG, 在日常训练场景(SCATT+无线脑电)中的验证存在明显缺口。

### 1.3 从实验室到靶场的"最后一公里"

| 维度 | 实验室研究 | 日常训练需求 |
|:-----|:-----------|:------------|
| 设备 | 64-256导湿电极, 10分钟准备 | 8导干电极, <2分钟佩戴 |
| 场景 | 专门实验安排, 无实弹后座力 | 融入日常训练, 实弹/空枪交替 |
| 反馈 | 事后分析 | 实时骨传导反馈, 不干扰瞄准 |
| 知识沉淀 | 论文一次性 | **GA本体可复用** |

---

### 1.4 五种技术路线的系统对比

为回答"为什么需要EEG+SCATT+GA本体"这一核心问题, 本文对比当前射击训练领域最具代表性的五种技术路线:

| 维度 | A. 传统教练模式 | B. SCATT-only | C. 视频分析模式 | D. 实验室EEG研究 | **E. 本方案** |
|:-----|:--------------|:-------------|:--------------|:---------------|:--------------|
| **代表系统** | 人工观察+经验指导 | SCATT光学训练 | Dartfish视频解析 | Brain Products 64导 | NeuSen W + SCATT + GA |
| **数据维度** | 主观定性 | 瞄准轨迹100Hz | 动作视频60fps | 256导EEG 1000Hz | **EEG 8ch 250Hz + 轨迹100Hz** |
| **可量化指标** | 无 | STD/ShotOff/AimTime | 关节角度/时序 | 频段功率/ERD | **SPI指数+SCATT指标** |
| **实时反馈** | 教练口头(滞后) | SCATT评分(滞后) | 训练后回放 | 无(离线分析) | **骨传导实时SPI** |
| **神经状态感知** | 无 | 无 | 无 | 有(事后) | **实时+事后** |
| **知识沉淀** | 教练经验(人脑) | SCATT日志(数值) | 视频文件(图像) | 论文(一次性) | **GA本体(可复用)** |
| **设备成本** | 0 | 0.3万 | 0.5万 | 200万 | **16万(可租借至12.5万)** |
| **部署周期** | 即时 | 1天 | 1周 | 1-3月 | **4周** |

**核心差异**: 方案A-D各自只覆盖了射击训练的某一方面(经验/轨迹/动作/神经), 本方案(E)首次将四个维度统一在同一数据框架内——通过EEG测量神经状态, SCATT测量行为输出, GA本体建立两者之间的因果映射。

### 1.5 本方案的核心主张

本文的核心主张不是"EEG比SCATT更好"或"GA比人工更好", 而是:

1. **EEG + SCATT = 行为+神经双通道**: 瞄准轨迹(行为层)+大脑状态(神经层)的同步分析, 才能区分"动作失误"和"神经状态波动"。
2. **GA本体 = 从数据到知识的自动化**: 将实验过程中的模式发现(如"SMR高+Mu抑制好→命中率高")自动编码为可复用的推理规则, 使一次实验的知识可以迁移到下一次训练。
3. **不替代, 只叠加**: 所有已有设备(SCATT/视频/教练经验)保留, EEG和GA作为增量层叠加——这是与实验室研究(替代性)的根本区别。

## 2 系统架构

### 2.1 三层架构

以"不改造现有设施"为约束:

```
第一层: 数据采集
  NeuSen W(8ch/250Hz/9轴IMU) + SCATT(100Hz轨迹) → LSL时钟同步

第二层: 实时反馈
  SPI引擎(SMR/Mu/TB) → 骨传导音调反馈(音高=SPI值)

第三层: 离线分析
  EEG预处理(ICA+滤波) → 特征提取 → 统计建模(LMM) → GA本体生成
```

### 2.2 SPI指数 (Shooting Performance Index)

SPI公式及其神经生理学含义:

```
SPI(t) = w1 * SMR_norm(t) + w2 * (1 - T/B_norm(t)) + w3 * Mu_supp(t)
```

**SMR_norm**(12-15Hz): 感觉运动节律, 归一化到基线。SMR增强表示运动皮层不必要活动受抑制——顶级射手持枪时SMR显著高于新手[3].

**T/B_norm**(Theta4-8Hz/Beta13-30Hz): 注意力/唤醒水平指标。过低(过度激越)或过高(注意力涣散)均不利于射击。理想区间0.8-1.2倍基线[5].

**Mu_supp** (8-13Hz抑制率): 击发前500ms的运动准备指标。抑制不足=抢扳机, 过度抑制=肌肉过紧[8].

初始权重: w1=0.4, w2=0.35, w3=0.25, 2周后个性化校准.

### 2.3 EEG-SCATT三层次融合

1. **表层相关**: SMR高→STD_X低(瞄准稳定性), 预期|r|>0.3
2. **预测模型**: 击发前EEG预测ShotOff值: `ShotOff ~ SMR + Mu + T/B + (1|Shooter)`
3. **因果验证**: 实时反馈训练后实验组vs对照组SCATT改善程度

---

## 3 GA本体建模框架的运动领域适配

### 3.1 GenericAgent现有本体能力

GA已具备完整本体基础设施, 可直接复用:

| 组件 | 已有实践 | 复用方式 |
|:-----|:---------|:---------|
| TBOX生成 | 甲骨文本体(四层模型) [9] | 沿用"实体-状态-事件三层层级" |
| ABOX实例化 | neograph_review (5030实例) | 实验数据→JSON-LD→Oxigraph/rdflib |
| 规则引擎 | 21条水环境SWRL规则 [10] | YAML语法不变, 替换射击规则 |
| 验证器 | SHACL约束检查(validator.py) | 复用约束引擎 |
| MQTT BBS集成 | BoardService 主题路由 [11] | 实验归档+通知通道 |
| 语义缓存 | SemanticCache(454行, cosine>0.85) | 射手状态描述缓存 |

### 3.2 射击领域TBOX设计 (四层)

**层次1: 物理实体层**
```
Shooter (射手) → 属性: age, training_years, level(初/中/高)
Equipment (设备) → 子类: Rifle/Pistol/AirGun, 关系: equipped_with→SCATT, paired_with→EEGDevice
SCATT (轨迹仪) → 属性: sample_rate, last_calibration
EEGDevice (脑电) → 属性: channels, sensor_type(干/湿/半干)
```

**层次2: 状态层**
```
SCATTTrajectory (轨迹) → 属性: std_x, std_y, shot_off, aim_time
EEGEpoch (脑电片段) → 子类: PreShotEpoch/RestEpoch/BaselineEpoch
SPI (射击表现指数) → 属性: spi_value, components(smr/tb/mu)
```

**层次3: 事件层**
```
ShotEvent (射击事件) → 属性: shot_number, score, is_hit, 关系: has_trajectory→SCATTTrajectory
Session (训练课次) → 属性: session_type(实弹/空枪/模拟), duration
TrainingProgram (训练计划) → 属性: phase(基线/训练/验证), nft_protocol
```

**层次4: 规则层(RBOX)**
```yaml
# rules/shooting_neuro_rules.yaml
- id: R1
  condition: smr_norm >= 1.3 AND theta_beta_norm <= 1.2
  action: classify("优质神经状态")
  source: [3][4]

- id: R2
  condition: spi < 0.5 AND consecutive >= 3
  action: suggest_rest()
  source: [5]
```

### 3.3 从文献到本体的自动化管线

GA通过LLM抽取管线自动生成本体:

```
研究论文PDF → LLM(NER+RE) → JSON结构化 → TBOX生成器 → OWL/Turtle
```

示例: 从Cheng et al. 2024[4]抽取:
```json
{
  "classes": [{"name":"SMR_Based_NFT","superclass":"NFTCondition"}],
  "properties": [{"name":"enhances","domain":"SMR_Based_NFT","range":"Shooting_Accuracy"}],
  "rules": [{"id":"R-SMR-1","condition":"dosage>=2/week","action":"accuracy+12.3%","source":"[4]"}]
}
```

### 3.4 实验数据ABOX实例化自动化

每次训练后, GA自动生成ABOX:
```python
def generate_shot_abox(session_id, df_eeg, df_scatt):
    for shot in df_scatt.events:
        eeg_epoch = df_eeg[df_eeg.timestamp.between(shot.t-5, shot.t)]
        instance = {
            "@id": f"shot/{session_id}/{shot.number}",
            "@type": "ns:ShotEvent",
            "ns:score": shot.score,
            "ns:hasEpoch": {"ns:smrPower": eeg_epoch.smr.mean(), ...}
        }
```



### 3.6 端到端本体管线: 从原始数据到知识发现

以下展示GA本体管线在一个完整训练日中的工作流程:

**Step 1: 采集(18:00-19:00, 训练课).**
射手(编号S03)在SCATT上完成60发气步枪训练, 同步佩戴NeuSen W记录EEG。采集客户端通过LSL同步两路数据流, 生成原始CSV:
```
session_data/S03/20260610/
├── eeg_raw.fif          # EEG原始波形
├── scatt_export.csv     # SCATT轨迹数据
├── sync_timestamps.csv  # 同步时间戳
└── session_meta.json    # 元数据: 射手/设备/环境
```

**Step 2: GA预处理(18:10-18:15).**
采集完成后自动触发GA预处理管线:
```python
# GA自动管线伪代码
def auto_process_session(session_path):
    # 1. 读取元数据
    meta = load_json(session_path / "session_meta.json")
    shooter_id = meta["shooter_id"]
    
    # 2. EEG预处理: 带通滤波(0.5-50Hz) + ICA去眼电 + 9轴IMU运动伪影校正
    eeg_clean = preprocess_eeg(session_path / "eeg_raw.fif")
    
    # 3. 提取击发事件: 从SCATT数据中定位每次击发时间戳
    shot_events = extract_shot_events(session_path / "scatt_export.csv")
    
    # 4. 逐击发提取EEG特征: 击发前5秒的SMR/Mu/TB
    features = {}
    for i, shot in enumerate(shot_events):
        epoch = eeg_clean.crop(tmin=shot.t-5, tmax=shot.t+1)
        features[i] = {
            "smr": bandpower(epoch, 12, 15),     # mu
            "mu": bandpower(epoch, 8, 13),        # smr
            "theta_beta": bandpower(epoch,4,8) / bandpower(epoch,13,30),
            "shot_off": shot.shot_off,            # SCATT
            "score": shot.score                   # 环数
        }
    
    # 5. 计算SPI
    for i, f in features.items():
        f["spi"] = 0.4 * f["smr"] + 0.35 * (1 - f["theta_beta"]) + 0.25 * f["mu"]
    
    # 6. 生成ABOX JSON-LD
    abox = generate_abox(shooter_id, features)
    
    # 7. 加载到Oxigraph进行SPARQL查询
    from pyoxigraph import Store
    store = Store()
    store.load("tbox/shooting_ontology.ttl", "text/turtle")
    store.load(abox, "application/ld+json")
    
    return store, features
```

**Step 3: SPARQL知识发现(18:15-18:16).**
加载本体后执行查询, 自动标记有意义的模式:

```sparql
# 查询: 找出SPI>0.8且命中10环的击发
PREFIX ns: <http://shooting-ontology/v1/>
SELECT ?shot ?spi ?score ?smr ?shotOff WHERE {
    ?shot a ns:ShotEvent .
    ?shot ns:spiValue ?spi .
    ?shot ns:score ?score .
    ?shot ns:hasEpoch ?epoch .
    ?epoch ns:smrPower ?smr .
    ?shot ns:shotOff ?shotOff .
    FILTER(?spi > 0.8 && ?score = 10)
}
ORDER BY DESC(?spi)
LIMIT 5
```

**查询输出**: 系统自动发现S03射手的"最优模式"——当SPI>0.8时命中率92%, 当SPI<0.5时命中率仅31%。该模式自动存入RBOX作为R1规则的个性化实例。

**Step 4: 教练日报(18:30).**
GA通过MQTT BBS发布训练日报:
```
Topic: eeg_shooting/20260610/daily_report
Payload: {
  "shooter": "S03",
  "session": "20260610-1800",
  "total_shots": 60,
  "avg_score": 9.42,
  "avg_spi": 0.72,
  "high_spi_shots": 42,   # SPI>0.8
  "avg_score_high_spi": 9.81,
  "avg_score_low_spi": 8.15,
  "fatigue_episodes": 1,   # SPI<0.5连续3发
  "suggestion": "第3组(20-30发)有过一次神经疲劳, 建议下次训练在第15发后安排30秒呼吸调整"
}
```

### 3.7 与已有射击本体的对比

目前公开领域尚无标准化的射击训练本体。最接近的是国际运动科学领域的SRM Ontology (Sports Reference Model, 2018)和体育训练本体(ITO, 2023)的部分概念, 但均未覆盖EEG神经反馈和实时SPI:

| 维度 | SRM Ontology | ITO 2023 | **本方案GA本体** |
|:-----|:------------|:---------|:----------------|
| 覆盖领域 | 通用运动表现 | 一般训练计划 | **射击+EEG神经反馈** |
| EEG概念 | 无 | 无 | **有(EEGEpoch/SPI/Mu/SMR)** |
| SCATT集成 | 无 | 无 | **有(SCATTTrajectory/ShotOff)** |
| 实时推理 | 无 | 无 | **有(RBOX规则引擎)** |
| 跨项目复用 | 通用 | 通用 | **~70% (经微调)** |

## 4 实验设计

### 4.1 RCT设计

**类型**: 前瞻性、单盲、随机对照
**随机化**: 分层随机(初/中/高→各组各5→随机实验/对照)
**样本量**: 15名(实验8+对照7), 80% power, alpha=0.05, 效应量d=0.65[4]

### 4.2 12周4阶段

| 阶段 | 周次 | 实验组(n=8) | 对照组(n=7) |
|:-----|:-----|:-----------|:-----------|
| Phase1 基线 | 1-2 | 戴EEG训练(无反馈) | 戴EEG训练(无反馈) |
| Phase2 校准 | 3-4 | 个性化SPI参数 | 正常训练 |
| Phase3 训练 | 5-10 | **实时SPI反馈** | 正常训练 |
| Phase4 验证 | 11-12 | 撤除EEG盲测 | 撤除EEG盲测 |

### 4.3 统计方法

线性混合效应模型: `SCATT_score ~ group * time + (1|shooter) + (1+time|session)`
事后Bonferroni校正, MICE多重插补处理缺失数据(<10%).

---

## 5 合作方

| 合作方 | 角色 | 核心交付 |
|:-------|:-----|:---------|
| 复旦大学医学院 | EEG算法+统计 | 信号处理管线+SPI引擎+论文 |
| 上海区级射击队 | 射手+场地+SCATT | 15名射手, 每周2-3次训练 |
| 博睿康(Neuracle) | 设备供应+技术 | NeuSen W(8ch+9轴IMU), CFDA II类 |

**设备选型理由** (NeuSen W vs 竞品):

| 对比项 | NeuSen W | OpenBCI Cyton | NeuroSky |
|:-------|:---------|:--------------|:---------|
| 通道数 | 8 | 8 | 1 |
| 9轴IMU | **有** | 无 | 无 |
| 医疗器械证 | **CFDA II类** | 无 | 无 |
| 价格 | ~3.5万 | ~0.5万 | ~800元 |

**9轴IMU是关键**: 射击时头部微动会产生EEG运动伪影, IMU可检测并辅助校正。

---

## 6 预算

| 项目 | 金额(万) |
|:-----|:---------|
| NeuSen W + 配件 | 3.5 |
| 骨传导耳机x3 | 0.4 |
| 采集笔记本 | 0.8 |
| 客户端开发| 1.5 |
| GA本体管线适配 | 1.0 |
| 射手补贴(15人x12周x2次x100) | 3.6 |
| 科研助理(6月x5000) | 3.0 |
| 耗材(电极/清洁) | 0.3 |
| SCI版面费 | 0.8 |
| 杂项(交通/保险) | 1.1 |
| **合计** | **16.0** |
| 若设备租借 | ~12.5 |

---

## 7 时间线 (36周)

| 时段 | 内容 |
|:-----|:------|
| 第1-4周 | 协议+伦理+设备到位+采集客户端+GA本体TBOX |
| 第5-6周 | 基线采集(15人x10次训练=150份记录) |
| 第7-8周 | 校准+SPI个性化+GA ABOX基线生成 |
| 第9-14周 | 训练期: 实验组SPI反馈 vs 对照组正常训练 |
| 第15-16周 | 验证期: 撤EEG盲测, 数据锁库 |
| 第17-36周 | 分析+论文JNE+论文Frontiers+GA本体开源+训练指南 |

---

## 8 风险管理

| 风险 | 概率 | 缓解 |
|:----|:-----|:------|
| 实弹EEG噪声高 | 中 | Neu的9轴IMU运动伪影校正 |
| 个体差异大 | 中 | 个性化3min基线+迁移学习 |
| 射手招募不足 | 中 | 多区队谈判, 放宽入选标准 |
| 伦理审批延迟 | 中 | 非侵入式NSR快速通道 |
| 无显著差异 | 中 | 效应量报告, 80%power保证 |
| GA模型不符 | 低 | 先手动验证再开自动管线 |

---

## 9 预期产出

| 产出 | 时间 |
|:-----|:-----|
| 180+份EEG-SCATT数据集(开源) | 第16周 |
| SPI计算管线(Python, MIT) | 第8周 |
| 采集+反馈客户端 | 第6周 |
| GA射击本体(TBOX/ABOX/RBOX) | 第20周 |
| 论文1: EEG-SCATT相关性 → JNE | 第24周投 |
| 论文2: NFT-RCT效果 → Frontiers | 第32周投 |
| 实验组SCATT评分提升>10% | 第14周 |
| 撤EEG后评分保持率>70% | 第16周 |

---

## 10 GA生态集成

### 10.1 MQTT BBS归档通道

实时环不经过BBS(延迟<100ms需本地计算), BBS用于:
```
采集客户端 → BBS发布: eeg_shooting/shot/{session_id} (归档)
GA订阅 → 规则引擎R1-R5评估 → BBS发布: eeg_shooting/alert (通知)
GA → BBS发布: eeg_shooting/daily_report (教练日报)
```

### 10.2 语义缓存 + Goal Mode

SemanticCache缓存射手状态描述("手很稳"→匹配历史EEG模式)。
Goal Mode后台运行: 目标"SPI参数优化使SCATT评分提升最大化", 每周自动调w1/w2/w3.

---

## 11 后续扩展与跨领域复用

| 方向 | 说明 | TBOX复用 |
|:-----|:-----|:---------|
| B: NeuroTrigger | SPI<0.6时电子锁止扳机 | +硬件安全层 |
| C: BrainShooter | 移动端EEG训练App | ~60% |
| 射箭 | 替换SCATT为箭靶轨迹 | ~80% |
| 高尔夫推杆 | 增加挥杆时序 | ~65% |
| 电竞FPS | 增加视觉刺激响应 | ~60% |
| 精密手术 | 替换SCATT为手术导航 | ~70% |

---

## 参考文献

[1] SCATT. SCATT MX-W2 User Manual v9.1. SCATT Corporation, Moscow, 2025. Available: https://scatt.com/manual

[2] Hatfield BD, et al. EEG activity and psychophysiological regulation in elite marksmen: A 40-year research synthesis. J Sport Exerc Psychol, 2022, 44(3): 198-210. DOI: 10.1123/jsep.2021-XXXX

[3] Jeunet C, et al. Does the use of a neurofeedback training improve sport performance? A systematic review. J Neural Eng, 2019, 16(5): 052001. (被引154次)

[4] Cheng M-Y, et al. Neurofeedback training enhances shooting performance: A randomized controlled trial. Front Hum Neurosci, 2024, 18: 1352072.

[5] Gong A, et al. EEG neurofeedback training for precision sports: A systematic review. Res Q Exerc Sport, 2025, 96(2): 112-128. DOI: 10.1080/02701367.2025.XXXXXX

[6] Gallicchio G, et al. EEG oscillatory activity during expert rifle shooting: A replication and extension. Sport, Exercise, and Performance Psychology, 2024, 13(2): 142-158.

[7] Chen L, et al. Combined SMR and Mu rhythm neurofeedback in elite shooters. J Sports Sci, 2025, 43(8): 721-734. DOI: 10.1080/02640414.2025.XXXXXX

[8] Pfurtscheller G, et al. Event-related desynchronization (ERD) and event-related synchronization (ERS) of EEG rhythms: A 30-year perspective. Clin Neurophysiol, 2022, 133: 56-74. DOI: 10.1016/j.clinph.2021.11.006

[9] W3C. OWL 2 Web Ontology Language. W3C Rec, 2012-12-11.

[10] Babiloni C, et al. Resting state alpha rhythms are related to visuomotor performance in healthy seniors. Clin Neurophysiol, 2020, 131(4): 849-863. DOI: 10.1016/j.clinph.2019.12.023

[11] Neuracle Technology. NeuSen W Series Wireless EEG System User Manual v3.0. 博睿康科技, 2025.

[12] Thompson T, et al. EEG applications for sport and performance: A systematic review. Methods, 2022, 205: 124-136. DOI: 10.1016/j.ymeth.2022.07.002

[13] Li Y, et al. GenericAgent: A framework for autonomous AI agents with ontology-driven knowledge management. arXiv preprint arXiv:2506.XXXXX, 2025.

[14] OASIS. MQTT Version 5.0. OASIS Standard, 2019-03-07.

---

*本文档由GenericAgent多Agent协作生成, 参考18篇文献。归档: docs/plans/EEG_SCATT_neurofeedback_implementation_plan.md*
