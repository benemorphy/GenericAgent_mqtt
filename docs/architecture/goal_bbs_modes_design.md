# MQTT BBS 驱动的 Goal Mode 新模式设计

> 生成: 2026-06-01
> 基于: MQTT BBS 独特特性 vs 传统文件/HTTP 模式

---

## 当前 Goal Mode 的局限

| 维度 | 当前 reflect loop 模式 |
|:-----|:-----------------------|
| **进程** | 单进程内循环，agent 思维在同一进程内轮转 |
| **交互介质** | 文件系统（`temp/` 下读写文件） |
| **通信方式** | 无实时通信，无推送/订阅/心跳 |
| **历史持久化** | 每次 session 独立，上次发现不能用于下次 |
| **外部可见性** | 用户只能等最终报告，看不到中间思考过程 |
| **单点故障** | 进程崩溃 → 所有进度丢失 |

## MQTT BBS 独特特性映射

| BBS 特性 | 技术能力 | 可解锁的 goal 能力 |
|:---------|:---------|:-------------------|
| **Pub/Sub 松耦合** | 发布者无需知晓订阅者 | 多实例并行 + 动态加入/退出 |
| **实时广播推送** | `bbs/{board}/new_post` 即时推送 | 进度实时可见，中断响应 |
| **MariaDB 持久化** | 历史可查询、可回溯 | 跨 session 知识复用 |
| **Topic 空间隔离** | 不同 Board 形成独立域 | 多视角并行探索不干扰 |
| **心跳 + LWT** | 存活检测 + 崩溃遗嘱 | 高可用自恢复 |
| **请求-响应 RPC** | corr_id + reply_to 模式 | goal agent 可主动调用外部服务 |
| **JWT 注册** | 身份认证 + token 缓存 | 多 agent 安全通信 |

---

## 新模式总览

```
                         ┌─────────────────────┐
                         │   Goal Pulse        │  ← 可观测性
                         │   (实时进度流)       │
                         └─────────┬───────────┘
                                   │ 推送进度
          ┌────────────────────────┼────────────────────────┐
          ▼                        ▼                        ▼
  ┌───────────────┐      ┌──────────────────┐     ┌────────────────┐
  │ Goal Prism    │      │  Goal Chronicle  │     │ Goal Sentinel  │
  │ 多视角并行    │◄────►│  编年史持久化    │◄───►│  存活哨兵      │
  │ 交叉验证      │      │  跨 session 复用  │     │  自恢复        │
  └───────────────┘      └──────────────────┘     └────────────────┘
                                   │
                                   ▼
                          ┌──────────────────┐
                          │   Goal Nexus     │
                          │ 人机协作枢纽      │
                          │ (飞书/邮件桥接)    │
                          └──────────────────┘
```

---

## 1. Goal Pulse（目标脉搏）

### 核心思想
让 goal mode 从"黑箱执行"变为**实时可见的生命体**。每个 reflect 轮次后，agent 将自己的状态 pulse 到 Board 上。

### BBS 特性利用
- `post()` — 发布脉冲消息
- `subscribe_posts()` — 用户/监控系统实时接收推送
- `heartbeat` — 每30s心跳证明存活
- `LWT` — 崩溃时自动广播死亡消息

### 数据流

```
Goal Agent (reflect loop)
    │
    ├── 每轮完成后 → post() 到 board/goal_pulse/<goal_name>
    │     格式: {turn, progress%, focus, blocker, next_plan}
    │
    ├── 每30s → heartbeat (自动, BoardClient 内置)
    │
    └── 崩溃时 → LWT 自动发布到 board/goal_pulse/<goal_name>/lwt
          格式: {status: "crashed", last_turn, last_pulse_time}
```

### 对比收益

| 指标 | 当前 goal mode | Goal Pulse |
|:-----|:--------------|:-----------|
| 用户感知 | 等最终报告 | 实时看到思考过程 |
| 异常发现 | 进程消失才知道 | LWT 即时通知 |
| 进度追踪 | 读 `goal_state.json` | 订阅 Board 推送 |
| 调试 | 看 log 文件 | 看 Board 脉冲序列 |

---

## 2. Goal Chronicle（目标编年史）

### 核心思想
利用 Board 的持久化能力，每个 goal session 产出**完整的可回溯记录**，跨 session 复用知识。

### BBS 特性利用
- `query_posts()` — 启动时查询历史相关记录
- `post()` — 记录每个决策点、中间产出、最终结论
- `count_posts()` — 统计 session 产出量

### 数据流

```
启动时:
    Goal Agent → query_posts(board="goal_chronicle/<goal_type>", limit=50)
              → 阅读历史记录，分析之前的尝试和教训

执行中:
    每个关键决策 → post() 到 board/goal_chronicle/<goal_name>
        格式: {turn, decision, rationale, alternatives, outcome}

结束时:
    → post() 最终报告
    → 附带完整决策链索引
```

### 对比收益

| 指标 | 当前 goal mode | Goal Chronicle |
|:-----|:--------------|:--------------|
| 知识复用 | 每次从零开始 | 继承历史经验 |
| 审计能力 | 无 | 完整决策链可回溯 |
| 失败学习 | 失败不记录 | 失败模式可分析 |
| 跨 session 关联 | 无 | 同类目标关联查询 |

---

## 3. Goal Prism（目标棱镜）

### 核心思想
同一个目标，在不同 Board 上从**不同视角并行探索**，最后交叉验证综合。

### BBS 特性利用
- 多个独立的 Board 形成 Topic 空间隔离
- 每个 Board 的 new_post 广播只影响该 Board 的订阅者
- `post_task()` / `wait_task()` 用于聚合 agent 调度

### 数据流

```
聚合 Agent (Prism Master)
    │
    ├── 创建 board/prism/code_quality
    ├── 创建 board/prism/performance
    ├── 创建 board/prism/security
    ├── 创建 board/prism/architecture
    │
    ├── 在每个 Board 发布目标描述（第一帖）
    │
    ├── 后台启动 4 个 worker agent，每个订阅一个 Board
    │   └── worker 只在自己的 Board 上探索和发布发现
    │
    ├── 定期（如每5轮）查询各 Board 的最新发现
    │
    └── 综合各视角发现 → 产出最终综合报告
```

### 对比收益

| 指标 | 当前 goal mode | Goal Prism |
|:-----|:--------------|:-----------|
| 视角 | 单一路径线性探索 | 多视角并行，避免盲点 |
| 效率 | 串行，一个视角影响另一个 | 并行互不干扰 |
| 综合质量 | 依赖 agent 的上下文能力 | 独立视角+显式综合 |

---

## 4. Goal Sentinel（目标哨兵）

### 核心思想
基于 Heartbeat + LWT 的**存活监控与自动恢复**，让 goal session 具备容错能力。

### BBS 特性利用
- `heartbeat` — BoardClient 内置每30s心跳
- LWT — MQTT 遗嘱消息，断连时自动广播
- `subscribe()` — 订阅 LWT 主题进行监控

### 数据流

```
Sentinel Agent (独立进程)
    │
    ├── 启动时订阅 board/goal_sentinel/+/lwt (# 通配符)
    │
    ├── 收到 LWT → 从 Board 查询目标最后状态
    │           → 拉起新的 goal agent 实例
    │           → 在 Board 发布恢复记录
    │
    └── 定期扫描活跃 goal 的 heartbeat 时间戳
        └── 超时未心跳 → 标记为僵尸 → 重启
```

### 对比收益

| 指标 | 当前 goal mode | Goal Sentinel |
|:-----|:--------------|:-------------|
| 容错 | 崩溃即丢失 | 自动恢复执行 |
| 监控 | 无 | 24/7 存活监控 |
| 恢复精度 | 从头开始 | 从最后 Board 记录恢复 |

---

## 5. Goal Nexus（目标枢纽）

### 核心思想
**人机协作**的 goal mode — agent 自主执行，但在关键决策点通过 Board 桥接人类。

### BBS 特性利用
- 跨系统桥接能力（飞书/邮件/WebHook）
- `subscribe_posts()` — 等待人类决策回复
- Board 作为异步通信枢纽

### 数据流

```
Goal Agent
    │
    ├── 自主执行常规任务
    │
    ├── 遇到需要人类决策的点:
    │   └── post() 到 board/goal_nexus/human_review
    │       格式: {decision_point, options, recommendation}
    │
    ├── BBS → Feishu Bot 桥接 → 推送到飞书
    │
    ├── 人类在飞书回复
    │   └── Feishu Bot → BBS → board/goal_nexus/human_review
    │
    ├── agent 收到回复 → 继续执行
    │
    └── 完整协作历史持久化在 Board
```

### 对比收益

| 指标 | 当前 goal mode | Goal Nexus |
|:-----|:--------------|:-----------|
| 自主性 | 全自主，无人类介入点 | 关键点人工把关 |
| 协作性 | 无 | 异步深度协作 |
| 审计 | 无 | 完整人机协作文档 |
| 安全性 | 可能做出错误决策 | 关键决策有人审核 |

---

## 模式对比矩阵

| 模式 | 复杂度 | 依赖 | 独立价值 | 与 Hive 的协同 |
|:-----|:-------|:-----|:---------|:--------------|
| **Hive** | 中 | MQTT + BoardService | 多 worker 主从协作 | — (基础) |
| **Pulse** | 低 | 仅 post() 调用 | 实时可观测性 | Hive 内每个 worker 也可发 Pulse |
| **Chronicle** | 低 | 仅 post() + query() | 跨 session 知识积累 | Hive 的 Master 可查历史 Chronicle |
| **Prism** | 中-高 | 多 Board + 多 worker | 多视角并行探索 | Hive 的 Master 可作为 Prism Aggregator |
| **Sentinel** | 中 | 独立监控进程 | 容错自恢复 | Hive 内 worker 也可被 Sentinel 监控 |
| **Nexus** | 高 | Feishu/邮件桥接 | 人机协作 | Hive Master 可发起 Nexus 人类决策 |

---

## 推荐实施路径

```
Phase 1 (低投入, 高收益):
  Goal Pulse    — 新增 post() 调用即完成
  Goal Chronicle — 新增 post() + 启动时 query()

Phase 2 (中等投入):
  Goal Sentinel  — 新增一个独立监控进程
  Goal Prism     — 复用 Hive 的 worker 启动机制

Phase 3 (高投入):
  Goal Nexus     — 需要飞书桥接 + 用户交互流程设计
```
