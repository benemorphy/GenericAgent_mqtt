# MQTT 服务配置存档 (L3 存档)

最后更新: 2026-05-26

## MQTT Broker
- **Mosquitto** (实际运行, 非 RMQTT)
  - 路径: `D:\tools\mosquitto\mosquitto.exe`
  - 端口: 1883
  - 配置: `D:\tools\mosquitto\mosquitto.conf`
    - `listener 1883`
    - `allow_anonymous false`
    - `password_file D:\tools\mosquitto\mosquitto_passwd`
  - 密码文件: `mosquitto_passwd`
  - 用户列表: feishu_bbs_bridge, board, dashboard, agent_gpt, test_agent, board-service-rs, test_user (密码见 keychain)
  - 重启生效: 修改密码后需重启 mosquitto 进程

## 服务启动链 (start_all.ps1)

| # | 服务 | 端口 | 类型 | 编译目标 | 说明 |
|---|------|------|------|----------|------|
| 1 | MariaDB | 3306 | 系统服务 | - | 数据库, 127.0.0.1:3306/mqtt_bbs |
| 2 | Mosquitto | 1883 | 原生进程 | - | MQTT Broker |
| 3 | simphtml_rs | 8901 | Rust | release | HTML简化提取 |
| 4 | rmqtt_webui_rs | 8900 | Rust | **debug** | Broker监控面板, 需MQTT凭据 |
| 5 | md_server_rs | 8899 | Rust | debug | Markdown服务器 |
| 6 | BoardService RS | - | Rust | debug | MQTT BBS持久化 |
| 7 | Gateway | 8000 | Python | - | HTTP网关 |
| 8 | Default WorkerAgent | - | Python | - | WorkerAgent (Mqtt_bbs.bbs) |

## MQTT 主题拓扑

| 主题 | 用途 | 发布者/订阅者 |
|------|------|--------------|
| node/# | Agent 节点状态/任务消息 | Agent / WebUI |
| $SYS/broker/# | Mosquitto Broker 统计指标 | Mosquitto / WebUI |
| agent/bbs/ | BBS 协议主题空间 | BBS客户端 |
| board/ | 板块通信主题 | BoardService |

## 连接认证
- **方式**: MQTT username/password 认证
- **配置**: `allow_anonymous false`, 使用 `password_file`
- **rmqtt_webui_rs 特殊处理**:
  - 代码读取环境变量: `MQTT_USERNAME` + `MQTT_PASSWORD` (main.rs L215-218)
  - 用户: dashboard (JWT 密码)
  - 密码来源: `tools/rmqtt_webui_rs/start_worker.py` L5
  - start_all.ps1 使用 `ProcessStartInfo.EnvironmentVariables` 传递
- **订阅主题**: `node/#`, `$SYS/broker/#`

## 常见问题
1. **WebUI 面板空白**: 启动时未设置 MQTT_USERNAME/PASSWORD 环境变量, Mosquitto 拒绝匿名连接
2. **BoardClient 注册超时**: 检查 BoardService 是否启动; 用 monitor 订阅 agent/bbs/# 追踪实际 topic 路径
3. **topic 格式不匹配**: 发送端/接收端/中间件三者对 topic 格式假设独立, 用独立 paho 客户端做收发对比验证

## 配置参考文件
- `start_all.ps1` — 服务启动脚本
- `mosquitto.conf` — Mosquitto 配置
- `tools/*/src/main.rs` — Rust 服务代码
- `config.py` — Python 端 MQTT 配置
