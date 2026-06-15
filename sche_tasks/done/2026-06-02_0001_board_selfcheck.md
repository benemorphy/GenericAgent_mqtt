# BoardService RS 高频自检报告

**状态: 紧急 (URGENT)** -- 3/4 步骤失败

**报告时间**: 2026-06-02 00:01  
**执行周期**: every_6h (自检)

---

## 执行结果摘要

| 步骤 | 操作 | 状态 | 延迟 | 说明 |
|------|------|------|------|------|
| Step 1 | 连接 Mosquitto 1883 | OK | 6.0ms | MQTT broker 正常 |
| Step 2 | 注册匿名 Agent | FAIL | 5.1s | 注册响应超时 |
| Step 3 | 发测试帖 | FAIL | 5.1s | 发帖响应超时 |
| Step 4 | 查询确认帖子存在 | FAIL | 5.1s | 查询响应超时 |

**总耗时**: 16.9s  
**紧急标记**: 是 (所有 BoardService 交互步骤均失败)

---

## 各步骤详情

### Step 1: MQTT 连接
- 目标: `127.0.0.1:1883`
- 结果: 连接成功，延迟 6ms
- 使用的 Topic 格式: `agent/bbs/agent-bbs-test/{operation}`

### Step 2: 注册
- 发布 Topic: `agent/bbs/agent-bbs-test/register`
- 订阅响应 Topic: `agent/bbs/agent-bbs-test/register/response/#`
- 结果: 等待5.1秒无响应
- Catch-all 订阅 (`agent/bbs/+/register/response/+`, `agent/bbs/+/post/response/+` 等)：收到0条 BoardService 发出的消息

### Step 3: 发帖
- 发布 Topic: `agent/bbs/agent-bbs-test/post`
- 订阅响应 Topic: `agent/bbs/agent-bbs-test/post/response/#`
- 结果: 等待5.1秒无响应

### Step 4: 查询
- 发布 Topic: `agent/bbs/agent-bbs-test/query`
- 订阅响应 Topic: `agent/bbs/agent-bbs-test/query/response/#`
- 结果: 等待5.1秒无响应

---

## 诊断分析

### 进程状态
| 组件 | PID | 状态 | 说明 |
|------|-----|------|------|
| board_service_rs.exe | 12004 | 运行中 | 7.6MB内存, 08:11:50UTC启动 |
| mosquitto.exe | 6544 | 运行中 | 监听1883, 6个连接 |
| MariaDB (3306) | - | 可连接 | 数据库 `mqtt_bbs` 17张表 |

### BoardService MQTT 连接状态
```
PID 12004: 127.0.0.1:63012 -> 127.0.0.1:1883  ESTABLISHED
Metrics端口: 9100  LISTENING
```

### 关键发现

**1. BoardService RS 订阅配置 (来自源码 main.rs)**
```rust
mqtt_client.subscribe("agent/bbs/+/register", QoS::AtLeastOnce).await?;
mqtt_client.subscribe("agent/bbs/+/post", QoS::AtLeastOnce).await?;
mqtt_client.subscribe("agent/bbs/+/query", QoS::AtLeastOnce).await?;
```
源码确认 BoardService 应处理 `agent/bbs/{board}/` 格式消息，但当前实例未响应。

**2. 日志分析 (board_service_new.log, 2916行)**
- 上一次成功处理 `agent/bbs/agent-bbs-test` 请求: **2026-06-01 08:09:34 UTC** (约16小时前)
  - 注册 → post_id=1689 → 查询成功
- 当前实例启动: **2026-06-01 08:11:50 UTC** (与PID 12004启动时间吻合)
- 当前实例日志 (08:11:50 ~ 16:03:09 UTC): 仅处理 `v2/agent/diagnosis_agent/rpc/` 话题消息
  - 全是 `"无效 token (board: agent-diagnosis)"` 警告
- 当前实例的日志中 **没有任何 `agent/bbs/` 相关处理记录**

**3. 历史对比**
```
08:08:11 UTC  → 实例A启动 → 处理agent-bbs-test请求 (成功) → 实例结束
08:11:50 UTC  → 实例B启动(当前) → 仅处理v2/agent/消息 → agent/bbs/无响应
```

**4. 系统其他 MQTT 连接**
| PID | 程序 | MQTT连接数 |
|-----|------|-----------|
| 3108 | rmqtt_webui_rs.exe | 1 |
| 14176 | python.exe | 2 (可能是 BBS 客户端) |
| 18716 | python.exe | 2 (可能是 BBS 客户端) |
| 12004 | board_service_rs.exe | 1 (BoardService) |

---

## 根因推测

**最可能的原因**: BoardService RS 的 event_loop 卡死，符合 SOP 中描述的静默故障模式:

> "进程活着+TCP连1883+心跳还在 ≠ MQTT正常, 可能event_loop卡死(主poll不处理消息,心跳独立task不受影响)"
> -- board_service_diag_sop

**佐证**:
1. 进程存活, TCP 连接正常, Metrics 端口 9100 可响应
2. 日志显示 16:03 UTC 后无新日志, 说明主循环已停止处理消息
3. 收到 `v2/agent/` 消息但不处理 `agent/bbs/` 消息 — 表明部分消息通道异常
4. JWT 认证持续报 `invalid token` — 可能认证模块异常导致主处理循环卡在认证环节

**次要可能**: JWT 密钥不匹配 -- 命令行指定了 `--jwt-secret bbs-browser-dev-secret-change-in-production`，但 BoardService 源码可能期望不同的密钥格式

---

## 建议修复方案 (参考 SOP Step 7)

**临时修复** (需人工执行):
1. 记录当前 PID
2. 终止 BoardService: `taskkill /PID 12004 /F`
3. 使用正确环境变量重新启动:
```bash
set MQTT_USERNAME=board-service-rs
set MQTT_PASSWORD=board-service-rs
D:\open_claw_agent\Beneh\Mqtt_bbs_server\tools\board_service_rs\target\release\board_service_rs.exe ^
  --db-url mysql://root:mariadb@127.0.0.1/mqtt_bbs ^
  --jwt-secret bbs-browser-dev-secret-change-in-production
```

**长期修复**:
1. 为 BoardService 添加 event_loop 健康检测：定期发布自检消息验证响应
2. 添加看门狗进程，检测到长时间无响应时自动重启
3. 排查 `invalid token` 根因 — 诊断 client 是否使用了错误的 JWT 密钥
4. 考虑升级 Rust BoardService 增加 `agent/bbs/` 通道的独立监控指标

---

*报告由 board_selfcheck 高频自检任务自动生成 (标记为紧急)*
