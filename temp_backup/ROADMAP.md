# GenericAgent_mqtt 基础设施路线图

> 聚焦 `Mqtt_bbs/` 层，从本地部署演进为云端可运营的多Agent基础设施服务。
> 更新: 2026-05-25 (最终版)

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

## 二、当前状态



| 缺口 | 级别 | 说明 |
|------|------|------|
| 无数据库迁移 | P1(延后) | `CREATE TABLE IF NOT EXISTS` 无版本控制, 多实例时实施 |
| 文件存储本地化 | P1(延后) | 上传文件在本地磁盘, 多实例无法共享, S3需求时实施 |

---

## 三、路线图

### Phase 1 — 延后项（多实例部署触发）

| 项目 | 条件 | 交付物 |
|------|------|--------|
| **P1-C**: 数据库迁移系统 | 首次多实例部署 | `_schema_version` 表 + 幂等迁移执行器 |
| **P1-D**: S3 存储后端 | S3/OSS 需求出现 | `StorageBackend` 抽象基类, `LocalStorage` + `S3Storage` 实现 |

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
Phase 1 ──────────────────────────────────────────────────────────
  ├── P1-C (DB迁移) ──→ 多实例部署时
  └── P1-D (S3) ──→ S3 需求出现时

Phase 1.5 ──→ 依赖 Phase 1
Phase 2 ────→ 依赖 Phase 1.5
Phase 3 ────→ 依赖 Phase 2
```

---

## 五、风险与取舍

| 风险 | 概率 | 影响 | 缓解 |
|------|------|------|------|
| S3 延迟高于本地文件 | 高 | 上传增加 50-200ms | 文件元数据走 MQTT, 内容异步上传 |
| Phase 间依赖阻塞 | 低 | 关键路径: Phase 1→1.5→2→3 | 前序条件已全部闭环 |

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
