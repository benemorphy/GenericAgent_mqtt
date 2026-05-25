# 飞书 Bot 连接与运维 SOP

> 目标: 通过飞书 Bot 实现远程对话控制电脑
> 实际状态: 已部署运行中 (App: cli_a92489c81e381bc4)

## 1. 快速参考

| 项目 | 内容 |
|------|------|
| Bot 入口 | `frontends/fsapp.py` |
| 配置文件 | `mykey.py` — 优先从环境变量读取: `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_ENCRYPT_KEY` |
| 环境变量 | `FEISHU_APP_ID`, `FEISHU_APP_SECRET`, `FEISHU_ENCRYPT_KEY`, `FEISHU_IS_LARK` |
| 启动方式 | `python frontends/fsapp.py` (需要 lark-oapi 库) |
| 启动脚本 | `temp/launch_feishu.cmd`, `temp/run_feishu.cmd` |
| 日志文件 | `temp/feishu_bot.log` |
| 安装依赖 | `pip install lark-oapi` |
| 开发平台 | https://open.feishu.cn/app/cli_a92489c81e381bc4 |

## 2. 连接架构

```
飞书客户端 ←[WebSocket]→ lark-oapi SDK ←→ fsapp.py ←→ GeneraticAgent
                               ↓
                         mykey.py (凭证)
```

- bot 使用 **WebSocket 长连接**模式 (`lark.ws.Client`)，无需公网 IP
- 消息接收: 注册 `p2_im_message_receive_v1` 事件处理器
- 自动重连: 失败后指数退避 (5s → 120s max)
- 文件收发: 支持图片/文件/音频的上传下载

## 3. 配置指南

### 3.1 mykey.py 必要字段

```python
fs_app_id = "cli_xxxxxxxxxxxxxxxx"       # App ID
fs_app_secret = "xxxxxxxxxxxxxxxx"       # App Secret
fs_allowed_users = ["ou_xxx"]            # 允许的用户 Open ID，['*']=所有人
```

### 3.2 飞书开放平台配置

1. 访问 https://open.feishu.cn/app/cli_a92489c81e381bc4
2. 「权限管理」→ 开通:
   - `im:message` （消息读写）
   - `im:message:send_as_bot` （以 bot 身份发消息）
   - `contact:user.id:readonly` （读取用户信息）
3. 「事件与回调」→ 已自动订阅 `im.message.receive_v1`
4. 「版本管理与发布」→ 每次修改后需**发布新版**才生效

## 4. 启动与验证

### 4.1 启动

```bash
cd D:\open_claw_agent\GenericAgent_mqtt
python frontends\fsapp.py
```

或双击 `temp/launch_feishu.cmd`

### 4.2 验证运行

启动后终端显示:
```
飞书 Agent 已启动（长连接模式）
App ID: cli_a92489c81e381bc4
等待消息...
```

### 4.3 验证消息收发

1. 打开飞书客户端
2. 搜索 bot 名称（在 App 详情页查看）
3. 发送任意消息 → bot 应在飞书回复
4. 也支持命令: `/help`, `/status`, `/stop`, `/new`, `/llm`, `/continue`

## 5. Bot 支持的消息类型

| 类型 | 处理方式 |
|------|----------|
| 文本 | 直接进入 agent 对话 |
| 图片 | 下载到 `temp/feishu_media/` 后传入 |
| 音频 | 下载到 `temp/feishu_media/` |
| 文件 | 下载到 `temp/feishu_media/` |
| Sticker/其他 | 显示占位符 |
| 分享卡片/合并转发 | 提取文本内容 |

## 6. 常见问题

### 6.1 连接失败

```log
飞书长连接断开或启动失败: ...
```

- 检查 `mykey.py` 中 `fs_app_id` 和 `fs_app_secret` 是否正确
- 检查飞书开放平台该应用是否**已发布**
- 网络问题 → 自动重连，无需人工干预

### 6.2 BBS桥接初始化失败 (Not authorized)

```log
[feishu_bbs_bridge] 连接失败 (rc=Not authorized)
```

- BBS 桥接需要连接本地 MQTT Broker (默认 127.0.0.1:1883)
- 当前 Broker 为 **mosquitto** (`D:\tools\mosquitto\`)，使用密码文件认证
- `D:\tools\mosquitto\mosquitto_passwd` 中已预置 `feishu_bbs_bridge` 用户
- `fsapp.py` 启动时自动设置 `MQTT_USERNAME=feishu_bbs_bridge` / `MQTT_PASSWORD=feishu_bridge_2024`
- 如需重置密码: `D:\tools\mosquitto\mosquitto_passwd.exe -b D:\tools\mosquitto\mosquitto_passwd feishu_bbs_bridge <新密码>`
- 确保 MQTT Broker (mosquitto.exe) 已启动且端口 1883 可访问

### 6.2 消息无响应

- 检查 `agent.is_running` — 处理中不会响应新消息
- 检查终端日志是否有报错
- 尝试发送 `/status` 查看状态

### 6.3 `processor not found` 错误

日志中出现 `processor not found, type: im.chat.access_event.bot_p2p_chat_entered_v1`:
- 这是正常行为，代码未注册该事件处理器
- 不影响消息接收功能

### 6.4 文件发送/接收失败

- 检查文件大小（飞书限制: 图片≤20MB，文件≤200MB）
- 检查 `temp/feishu_media/` 目录是否存在且有写入权限

## 7. 开发与调试

- **测试 WebSocket**: `python temp/test_lark_ws.py`
- **调试级别**: `log_level=lark.LogLevel.INFO` 已在代码中设置
- **手动发送消息**: 通过 SDK 的 `create_message` API

## 8. 安全注意事项

- `fs_app_secret` 是敏感凭证，严禁打印/泄露
- `fs_allowed_users` 设为 `['*']` 时，**所有知道 bot 名的飞书用户都可使用**
- 建议限制为特定用户 Open ID
