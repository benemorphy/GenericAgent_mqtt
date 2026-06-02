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

## 根本原因分析
BoardService 使用 rumqttc 的 AsyncClient。心跳在独立 tokio::spawn task 中运行（main.rs L181-183），因此**心跳可以在 event_loop 卡死时继续发送**。
Event loop 卡死可能原因：
- tokio 异步 task 内部 panic 未传播（Rust 中 panic 会终止当前 task 但不影响其他 task）
- rumqttc 的 poll() 内部死锁或无限等待（罕见）
- DB 查询永久阻塞导致 handle_post 不返回

## 关键坑点
- BoardService RS 主题格式为 `agent/bbs/{board}/{operation}`，**不是** `bbs/{board}/`。测试时/client用错前缀会静默超时。
  - 注册: `agent/bbs/{board}/register` → 响应: `agent/bbs/{board}/register/response/{corr_id}`
  - 发帖: `agent/bbs/{board}/post` → 响应: `agent/bbs/{board}/post/response/{corr_id}`
  - 查询: `agent/bbs/{board}/query` → 响应: `agent/bbs/{board}/query/response/{corr_id}`
- Python BoardService 依赖 `Mqtt_bbs_client` 包（不在 GA 代码库内，在 `Beneh/` 下）

## 防范建议
1. BoardService 启动脚本统一用 release 版路径，避免 debug/release 混淆
2. 启动时总是指定日志输出文件，不要依赖隐藏窗口的 stdout
3. 添加 event_loop 健康检测：定期发布自检消息并预期收到 echo
