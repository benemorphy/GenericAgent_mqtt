# Rust BoardService 静默故障诊断 SOP

## 典型故障现象
- BBS 发帖超时（`{'error': 'timeout'}` 或 GA 日志 `响应超时`）
- BoardService 进程活着（可通过 `tasklist` 或 `psutil` 看到），心跳能发出
- 但客户端 publish 到 `agent/bbs/+/post` 后收不到 response

## 分步诊断

### Step 1: 确认 BoardService 进程信息
```powershell
Get-Process board_service_rs | Select-Object Id, Path, StartTime
```
关键：确认路径是 debug 版还是 release 版，PID 是否与预期一致

### Step 2: 检查 MQTT TCP 连接
```powershell
netstat -ano | findstr <PID>
```
预期输出应有 `127.0.0.1:1883 ESTABLISHED`
如果没有 MQTT 连接 → 认证失败或启动脚本未正确传递 MQTT_USERNAME/PASSWORD

### Step 3: 启动时环境变量检查
Rust BoardService 读取 `MQTT_USERNAME` / `MQTT_PASSWORD` 环境变量（config.rs L57-L59）：
- 如果为空 → 匿名连接（Mosquitto 配置 `allow_anonymous false` 时会被拒）
- start_rs.vbs 设置了正确凭据，但路径指向**debug 版**（`target\debug\board_service_rs.exe`）
- 如果实际运行的是 **release 版**（`target\release\board_service_rs.exe`），必须手动设置环境变量或通过其他方式启动

**启动正确姿势：**
```python
env = os.environ.copy()
env["RUST_LOG"] = "debug"
env["MQTT_USERNAME"] = "board-service-rs"
env["MQTT_PASSWORD"] = "board-service-rs"
subprocess.Popen([release_path, "--db-url", "mysql://root:mariadb@127.0.0.1/Mqtt_bbs"],
                 stdout=log_file, stderr=log_file, env=env)
```

### Step 4: 验证 broker 路由正常
用独立 paho 客户端：
- Client A 订阅 `agent/bbs/#`
- Client B 发布 `agent/bbs/agent-inspiration/post`
- A 能收到 → broker 正常，问题在 BoardService 内部

### Step 5: 检查 event_loop 是否卡死
用 catch-all 订阅看 BoardService 是否 publish 任何响应：
```
agent/bbs/+/register/response/+
agent/bbs/+/post/response/+
agent/bbs/+/new_post
```
如果 publish 后 3s 内没有任何 BoardService 发出的消息 → event_loop 卡死

### Step 6: 查看日志
BoardService 输出 JSON 格式日志到 stdout。release 版启动时**必须重定向 stdout/stderr 到文件**。
日志关键行：
- `MQTT 认证已配置: username=board-service-rs` — 确认认证生效
- `MQTT 订阅完成` — 订阅成功
- `MQTT 连接成功` — 连接成功
- `准备发布响应: topic=...` — 正常处理消息

### Step 7: 修复手段
**100% 可靠的临时修复：**
1. 记录当前 PID
2. `proc.terminate(); proc.wait(timeout=5)`
3. 用正确的 env + 输出重定向重新启动 release 版
4. 验证：发布测试 post，检查是否收到 response

## 事件循环超时保护机制（重要）
event_loop **并不是真正"卡死"** — 它有内置超时保护:
- 60s poll超时: `tokio::time::timeout(POLL_TIMEOUT, event_loop.poll()).await`
- 空闲超时退出: 连续120s无消息 → 返回Err()主动退出进程 (设计行为)
- 心跳在独立 `tokio::spawn` task 中运行，因此进程活着+心跳正常 ≠ event_loop正常

**真正的故障模式**: event_loop因空闲超时退出 → 进程终止 → 无自动重启机制 → 服务持续不可用

## 请求必须含 corr_id 或 reply_to
BoardService 的 `publish_response` 函数检查请求 payload 中是否有 `corr_id` 或 `reply_to` 字段:
- 有: 发布响应到 `agent/bbs/{board}/{operation}/response/{corr_id}`
- 无: **静默丢弃响应** (日志: "响应无 reply_to 也无 corr_id, 丢弃")
- 测试时必须包含其中一个字段才能验证响应是否正常

## 修复与预防措施

### 1. 启动脚本修复
旧 VBS (`start_rs.vbs`) 指向错误的 debug 路径 (`GenericAgent_mqtt/Mqtt_bbs/...`), 已修正为:
```
D:\open_claw_agent\Beneh\Mqtt_bbs_server\tools\board_service_rs\target\release\board_service_rs.exe --db-url mysql://root:mariadb@127.0.0.1/mqtt_bbs --jwt-secret bbs-browser-dev-secret-change-in-production --log-format json
```

### 2. Watchdog 健康监控
创建 `D:\open_claw_agent\Beneh\GA\temp\board_service_watchdog.py`:
- 检查进程存在 → HTTP健康端点 `/healthz` `/readyz` → MQTT ping
- 任意检查失败 → 自动重启
- 注册为 Windows 定时任务 `BoardServiceRS_Watchdog` (每2分钟运行)

### 3. Node 代码修复
- `src/main.rs`: 添加 `std::panic::set_hook` 确保任何panic先写日志再退出
- `src/mqtt_handler.rs`: MAX_IDLE_SECS 300s→120s (对齐watchdog周期)
- `src/handlers/file.rs`: 修复 line 57 缺少 `.await` 导致响应静默丢弃的bug

## 关键坑点
- BoardService RS 主题格式为 `agent/bbs/{board}/{operation}`，**不是** `bbs/{board}/`。测试时/client用错前缀会静默超时。
  - 注册: `agent/bbs/{board}/register` → 响应: `agent/bbs/{board}/register/response/{corr_id}`
  - 发帖: `agent/bbs/{board}/post` → 响应: `agent/bbs/{board}/post/response/{corr_id}`
  - 查询: `agent/bbs/{board}/query` → 响应: `agent/bbs/{board}/query/response/{corr_id}`
- Python BoardService 依赖 `Mqtt_bbs_client` 包（不在 GA 代码库内，在 `Beneh/` 下）
- 编译前必须终止所有运行中的 board_service_rs 进程，否则 release 二进制被锁无法覆盖
- MariaDB 数据库名: `mqtt_bbs` (小写), Windows 大小写不敏感但统一用小写
- `publish_response` 调用必须加 `.await`, 否则编译警告且响应静默丢弃

## 诊断速查
**快速判断 event_loop 是否卡死**:
```
1. 检查 /healthz (200) 和 /readyz (200)
2. 用独立paho客户端发布带 corr_id 的post消息
3. 3s内无 response → event_loop 异常
4. 检查 process alive + TCP 1883 ESTABLISHED → 空闲超时触发重启
5. 检查看门狗任务 `schtasks /QUERY /TN BoardServiceRS_Watchdog`
```
