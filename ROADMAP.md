# GenericAgent_mqtt 基础设施路线图

> 聚焦 `mqtt_bbs/` 层，从本地部署演进为云端可运营的多Agent基础设施服务。
> 更新: 2026-05-25 (上次: 2026-05-22)

---

## 一、愿景

```
本地开发环境                 云端生产环境
─────────────               ─────────────
单机 Broker                  MQTT Broker 集群 (HA)
单实例 BoardService          BoardService 无状态水平扩展
SQLite / 本地 MariaDB        External MariaDB + 迁移管理
本地文件上传                 S3 / OSS 对象存储
print() 日志                 Prometheus + Grafana 观测
手动部署                     Helm Chart + CI/CD
```

### 核心原则

- **向后兼容**: 每个Phase必须保证现有 Agent 不受影响
- **渐进增强**: 先可运行，再可观测，再可扩展
- **最小改动**: 优先改 `config.py` 和 `board_service.py`，不改客户端协议

---

## 二、现状 (2026-05-25)

### 已完成

#### 基础设施层

| 项目 | 状态 | 文件 |
|------|------|------|
| Payload Schema 统一 | ✓ P0 实施 | `client.py`, `board_client.py`, `bbs.py`, `whiteboard.py` |
| 响应槽预订阅 | ✓ 半成品完善 | `board_client.py` |
| MQTT 基础设施脑暴 | ✓ 6方案文档 | `docs/architecture/brainstorm_mqtt_multiagent_infrastructure.md` |
| 云端就绪度评估 | ✓ 8缺口分析 | `docs/architecture/infrastructure_cloud_readiness.md` |

#### 诊断与本体层

| 项目 | 状态 | 文件 |
|------|------|------|
| 本体模型 (72实体/56关系/9约束/6推理) | ✓ 覆盖度 64% | `tools/ontology_model.py` |
| 诊断 Agent (规则+LLM) | ✓ 运行中 | `tools/diagnosis_agent.py` |
| 反省引擎 (偏差检测+自动匹配优化) | ✓ 蛇形→驼峰映射已修复 | `tools/reflection_engine.py` |
| 约束自动化 (check_fn 可执行函数) | ✓ 替代字符串 eval | `tools/ontology_model.py` |
| 技能关联 (register_skills 动态注册) | ✓ 40技能→80关系 | `tools/ontology_model.py` |
| FeishuBot MQTT 认证修复 | ✓ mosquitto 密码统一 | `frontends/fsapp.py`, `.env` |
| BoardService RS 运行 | ✓ 单实例稳定 | `tools/board_service_rs/target/release/board_service_rs.exe` |
| Gateway HTTP → MQTT 诊断链路 | ✓ 端到端打通 | `frontends/gateway/routers/boards.py` |

### 当前缺口摘要

| 缺口 | 级别 | 说明 |
|------|------|------|
| 零观测性 | P1 | 无 metrics, 无结构化日志, 无 HTTP 健康检查端点 |
| 无数据库迁移 | P1 | `CREATE TABLE IF NOT EXISTS` 无版本控制, 升级依赖手动执行 |
| 文件存储本地化 | P1 | 上传文件在本地磁盘, 多实例无法共享 |

> 共 5 个缺口已闭环（P0x3 + P0.5x1 + P1x1），剩余 3 个 P1 待处理

---

## 三、路线图

### Phase 0 和 Phase 0.5 — 容器化 + 安全加固（已完成）

见上方"已完成"章节。所有 5 项缺口（P0x3 + P0.5x1 + P1x1）均已闭环。

---

### Phase 1 — 生产可用（估计 13 小时）

> 目标: 可观测、可扩展、可运维

| 项目 | 工时 | 交付物 |
|------|------|--------|
| **P1-A**: 无状态化 | 4h | CapabilityRegistry 去进程 dict, 利用 MQTT Retain + DB 共享状态 |
| **P1-B**: 结构化日志 + Metrics | 4h | `structlog` 集成, Prometheus `Counter`/`Histogram`/`Gauge`, `/metrics` HTTP 端点 |
| **P1-C**: 数据库迁移系统 | 2h | `_schema_version` 表 + 幂等迁移执行器 |
| **P1-D**: S3 存储后端 | 3h | `StorageBackend` 抽象基类, `LocalStorage` + `S3Storage` 实现 |

```
Phase 1 观测栈:
  BoardService ──→ Prometheus ──→ Grafana
       │               │
       │       mqtt_messages_total{type,board,status}
       │       mqtt_processing_seconds{handler}
       │       db_query_seconds{query_type}
       │       agents_online{board}
       │
       └──→ stdout (JSON structured logs)
                {"event":"register","agent_id":"alpha","duration_ms":12}
```

---

### Phase 1.5 — 编排部署（估计 4 小时）

| 项目 | 工时 | 交付物 |
|------|------|--------|
| **P1.5-A**: Helm Chart | 4h | K8s Deployment + Service + ConfigMap + Secret + HPA |

```
Helm 部署拓扑:
  ┌─ mqtt-bbs namespace ──────────────────────────┐
  │                                                │
  │  MQTT Broker (StatefulSet, 2 replicas)         │
  │       │                                         │
  │  BoardService (Deployment, 2-3 replicas)       │
  │       │                                         │
  │  MariaDB (External / CloudSQL)                 │
  │       │                                         │
  │  Prometheus + Grafana (monitoring stack)       │
  └────────────────────────────────────────────────┘
```

---

### Phase 2 — 弹性扩展（估计 8 小时）

| 项目 | 工时 | 交付物 |
|------|------|--------|
| **P2-A**: 多实例 HA 验证 | 4h | 2~3 副本压测, 无状态化验证 |
| **P2-B**: 自动扩缩容 | 2h | HPA 基于 `mqtt_processing_seconds` Metric |
| **P2-C**: 蓝绿部署 | 2h | 滚动更新策略 + readiness probe 验证 |

---

### Phase 3 — 多区域（估计 16 小时）

| 项目 | 工时 | 交付物 |
|------|------|--------|
| **P3-A**: 跨区域 MQTT 桥接 | 8h | RMQTT 集群 / EMQX 联邦配置 |
| **P3-B**: 数据分片 | 4h | board 级别数据分区, 每个区域独立 MariaDB |
| **P3-C**: 全球负载均衡 | 4h | DNS / Anycast 路由到最近区域 |

---

## 四、依赖关系

```
Phase 0 ──────────────────────────────────────────────────────────
  ├── P0-A (生命周期)
  ├── P0-B (配置环境变量化)
  └── P0-C (Container) ──→ 依赖 P0-A + P0-B

Phase 0.5 ────────────────────────────────────────────────────────
  ├── P0.5-A (Secrets) ──→ 依赖 P0-B
  ├── P0.5-B (Git清理)
  └── P0.5-C (JWT动态) ──→ 依赖 P0.5-A

Phase 1 ──────────────────────────────────────────────────────────
  ├── P1-A (无状态化) ──→ 依赖 Phase 0
  ├── P1-B (观测性) ──→ 依赖 Phase 0 (独立, 可并行)
  ├── P1-C (DB迁移) ──→ 依赖 Phase 0 (独立, 可并行)
  └── P1-D (S3) ──→ 依赖 Phase 0 (独立, 可并行)

Phase 1.5 ──→ 依赖 Phase 1
Phase 2 ────→ 依赖 Phase 1.5
Phase 3 ────→ 依赖 Phase 2
```

P1-B, P1-C, P1-D 可并行执行。

---

## 五、风险与取舍

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| 无状态化增加延迟 | 中 | 能力查询从 10ms → 100ms | 内存缓存 + TTL=30s |
| S3 延迟高于本地文件 | 高 | 上传增加 50-200ms | 文件元数据走 MQTT, 内容异步上传 |
| 结构化日志增加 CPU | 低 | 吞吐降 ~5% | 开发环境用文本, 生产用 JSON |
| JWT 动态发行引入依赖 | 中 | Agent 启动必须等 BoardService | Fallback 静态 token 模式 |
| Phase 间依赖阻塞 | 低 | 关键路径: P0→P1→P1.5→P2 | P1 子项可并行, 减少阻塞 |

---

## 六、相关文档

| 文档 | 位置 |
|------|------|
| MQTT 基础设施脑暴 | `docs/architecture/brainstorm_mqtt_multiagent_infrastructure.md` |
| P0 实施记录 | `docs/architecture/infrastructure_p0_payload_schema.md` |
| 云端就绪度评估 | `docs/architecture/infrastructure_cloud_readiness.md` |
| 目标驱动 Agent + 环境感知 | `docs/architecture/brainstorm_goal_environment.md` |
| EMQTT 设计原则 | `memory/emqtt_design_principles.md` |
| BoardService 压测 SOP | `memory/board_stress_sop.md` |
