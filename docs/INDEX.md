# docs/ — 文档目录导航

> 最后整理: 2026-06-12 | 按主题分类，脑暴归入对应目录 | 各子目录均有 README.md

---

## 根目录

| 文件 | 说明 |
|:-----|:------|
| `GA_design_overview.html` | GA 智能体系统设计总览（HTML 全景图） |
| `INDEX.md` | **本文件** — 文档目录导航 |

---

## goal_mode/ (3文件)
Goal Mode 移植分析、可行性与实现记录

| 文件 | 说明 |
|:-----|:------|
| `goal_mode_analysis.md` | GenericAgent Goal Mode 5层架构分析 |
| `goal_mode_feasibility.md` | 移植到 Beneh 的可行性审计 |
| `goal_mode_implementation_session.md` | 移植实现会话记录 |

---

## architecture/ — 核心架构

### root (2文件)
| 文件 | 说明 |
|:-----|:------|
| `README.md` | 系统架构概览（47秒之隙项目定位 + 5服务拓扑） |
| `系统服务拓扑与信息流向图.md` | 全服务拓扑与数据流 |

### gateway_design/ (4文件)
统一网关 (FastAPI) 设计与修复记录

| 文件 | 说明 |
|:-----|:------|
| `gateway_structure_design.md` | FastAPI 统一网关结构设计 |
| `gateway_fix_session_2026-05-28.md` | Gateway 邮箱验证修复会话 |
| `用户认证与Retain策略设计.md` | 认证重构 + MQTT Retain策略 |
| `session_resume_note.md` | Gateway Email Auth + SMTP 修复完成记录 |

### infrastructure/ (8文件)
基础设施分层、上云评估与扩展方案

| 文件 | 说明 |
|:-----|:------|
| `infrastructure_cloud_readiness.md` | MQTT BBS 云端就绪度评估 |
| `infrastructure_deep_dive.md` | 上云方案补充维度分析 |
| `infrastructure_identity_query.md` | 分层方案补充：BBS查询/Agent身份/MariaDB |
| `infrastructure_p0_payload_schema.md` | P0 统一消息 Payload Schema |
| `infrastructure_plugin_analysis.md` | Plugin System 上云还是留本地 |
| `infrastructure_scaling_tls.md` | 万级Agent基础设施 + TLS证书方案 |
| `infrastructure_vps_recommendation.md` | VPS 配置评估与产品推荐 |
| `infrastructure_decoupling_brainstorm.md` | [脑暴] 基础设施层分离方案 |

### self_harness/ (6文件)
自驭 (Self-Harness) — 自主智能体的自我约束与自改进

| 文件 | 说明 |
|:-----|:------|
| `brainstorm_self_harness.md` | [脑暴] 自驭的架构哲学 |
| `deep_research_self_harness.md` | 自驭机制深研：约束范式 |
| `deep_research_goal_self_harness.md` | 目标自驭深研：方向感与自驱力 |
| `self_harness_audit_analysis.md` | 自驭审计循环必要性分析 |
| `code_and_rumination.md` | [脑暴] 代码与反刍 — 多智能体架构反思 |
| `deep_research_code_and_rumination.md` | 代码反刍深研：自改进代码的元认知架构 |

### curiosity/ (6文件)
好奇心驱动 Agent — 理论基础、BBS讨论与感知应用

| 文件 | 说明 |
|:-----|:------|
| `brainstorm_agent_curiosity.md` | [脑暴] 智能体与好奇心 |
| `brainstorm_bbs_curiosity.md` | [脑暴] BBS x 好奇心 — 讨论激发好奇 |
| `brainstorm_perception_curiosity.md` | [脑暴] 环境感知中的好奇心保持 |
| `curiosity_roadmap.md` | 好奇心驱动 Agent 实施路线图 |
| `deep_research_agent_curiosity.md` | 智能体好奇心深研 |
| `deep_research_cls_complementary_learning_systems.md` | 互补学习系统(CLS)深研 |

### purification/ (3文件)
项目净化与可行性分析

| 文件 | 说明 |
|:-----|:------|
| `brainstorm_project_purification.md` | [脑暴] 项目的净化与洗涤 |
| `purification_assessment.md` | 净化状态快照评估 |
| `feasibility_analysis.md` | 三项能力实现可行性分析 |

### mqtt_hive/ (4文件)
MQTT 实现的 Goal Hive 多 Worker 机制

| 文件 | 说明 |
|:-----|:------|
| `brainstorm_mqtt_multiagent_infrastructure.md` | [脑暴] MQTT 基础设施架构演进 |
| `brainstorm_goal_environment.md` | [脑暴] Goal-Aimed Agent + 环境感知 |
| `mqtt_goal_hive_plan.md` | MQTT BBS 实现 Goal Hive 方案 |
| `goal_hive_mechanism_analysis.md` | GenericAgent Goal Hive 机制原理分析 |

### bbs_board/ (1文件)
BBS Board Browser

| 文件 | 说明 |
|:-----|:------|
| `bbs_board_browser_plan.md` | FastAPI + Jinja2 + MariaDB 架构与实现计划 |

### ontology_diagnosis/ (3文件)
本体论模型与系统诊断

| 文件 | 说明 |
|:-----|:------|
| `brainstorm_multiagent_ontology_diagnosis.md` | [脑暴] 多Agent本体论与系统诊断 |
| `brainstorm_erlang_mqtt_ontology.md` | [脑暴] Erlang节点 x MQTT x 活图 x 本体论 |
| `ontology_diagnosis_detail.md` | 本体论模型与系统诊断详细说明 |

### performance/ (2文件)
性能基线测试

| 文件 | 说明 |
|:-----|:------|
| `performance_baseline_2026-05-25.md` | 首次全量性能基线记录 |
| `stress_test_retro.md` | P0-A 压测执行完整记录 |

---

## ontology/ (9文件)
本体论建模 — 贷款系统领域 + 通用本体论研究

| 文件 | 说明 |
|:-----|:------|
| `neograph_review本体论实现方案.md` | Neo4j + MariaDB 本体论实现构想 |
| `neograph_review本体论建模可行性分析.md` | 基于 neograph_review 文档的可行性分析 |
| `个人经营贷系统本体论分析.md` | 个人经营贷系统内部智能助手本体论分析 |
| `小微贷款系统本体建模技术方案.md` | 小微贷款本体建模技术实施方案 |
| `小微贷款系统本体建模目标体系与运营产出.md` | 本体建模目标体系与运营产出 |
| `本体论模型输入输出说明.md` | 本体模型输入实体与输出成果说明 |
| `brainstorm_gbrain_kg_ontology.md` | [脑暴] gbrain 知识图谱本体论融合 |
| `kg_semantic_research_synthesis.md` | 知识图谱语义研究综述 |
| `本体模型与自动驾驶理论_DeepResearch_2026-06-11.md` | 本体模型与自动驾驶理论交叉研究 |

---

## urban_water_ontology/ (5文件)
城市水务本体论 — 论文与Mqtt BBS集成

| 文件 | 说明 |
|:-----|:------|
| `water_ontology_comparison_paper.md` | 水务本体对比论文 |
| `water_ontology_mqtt_bbs.md` | 水务本体与 Mqtt BBS 集成方案 |
| `water_ontology_mqtt_bbs_paper.md` | 水务本体 Mqtt BBS 论文 |
| `water_ontology_practical_paper.md` | 水务本体实践论文 |
| `water_ontology_remote_sensing_paper.md` | 水务本体遥感应用论文 |

---

## opensquilla/ (4文件)
OpenSquilla 路由器分析、集成与经验总结

| 文件 | 说明 |
|:-----|:------|
| `opensquilla_analysis.md` | OpenSquilla 功能分析 |
| `opensquilla_router_integration_for_ga.md` | OpenSquilla 与 GA 集成方案 |
| `squilla_router_integration_for_beneh.md` | Squilla 与 Beneh 集成方案 |
| `squilla_router_lessons_learned.md` | Squilla 集成经验教训总结 |

---

## trending/ (2文件)
每日技术趋势简报

| 文件 | 说明 |
|:-----|:------|
| `trending_briefing_2026-06-09.md` | 趋势简报摘要 |
| `trending_detailed_2026-06-09.md` | 趋势简报详细版 |

---

## ideas/ (2主题)
项目构想与创意

| 目录/文件 | 说明 |
|:-----|:------|
| `binocular-reading-ocr/` | 双目AR眼镜OCR阅读方案（含竞品分析/FPGA方案/环境检查清单） |
| `EEG_neurofeedback_shooting_training_brainstorm.md` | EEG神经反馈射击训练构想 |

---

## papers/ (1文件)
学术论文/专题研究

| 文件 | 说明 |
|:-----|:------|
| `中国特色企业社会责任ESG框架探讨.md` | 中国社会主义特色的企业ESG框架探讨 |

---

## plans/ (4文件)
测试与实施计划

| 文件 | 说明 |
|:-----|:------|
| `verify_email_real_smtp_plan.md` | 真实邮箱验证码 SMTP 发送计划 |
| `vpn_remote_login_test_plan.md` | VPN 远程新用户登录测试计划 |
| `EEG_SCATT_neurofeedback_implementation_plan.md` | EEG SCATT神经反馈实施方案 |
| `GA_Improvement_Roadmap_P0_P4.md` | GA 改进路线图 P0-P4 |
