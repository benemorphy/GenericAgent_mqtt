# MQTT BBS 安全分析：身份认证与威胁模型

> 基于 **rmqtt v0.20.0**（Rust 版 MQTT Broker）
> 实际配置路径：`D:\tools\rmqtt\rmqtt-0.20.0-x86_64-pc-windows\etc\rmqtt.toml`

---

## 当前安全现状

```
rmqttd.exe  -f etc\rmqtt.toml

# 外部监听器（Agent所用端口）
listener.tcp.external.addr          = "0.0.0.0:1883"
listener.tcp.external.allow_anonymous = true    ← 无认证！人人可连
listener.tcp.external.max_connections = 1024000 ← 高并发上限

# 内部监听器（管理端口）
listener.tcp.internal.addr          = "0.0.0.0:11883"
listener.tcp.internal.allow_anonymous = false   ← 内部有认证但未使用

# 已启用的插件（仅2个）
plugins.default_startups = [
    "rmqtt-web-hook",      # Webhook 通知
    "rmqtt-http-api",      # HTTP REST API
]

# 可用的认证插件（全部注释，未启用）
# "rmqtt-auth-http"        ← 可在启动时调HTTP API验证身份
# "rmqtt-auth-jwt"         ← JWT 令牌验证
```

**关键发现**：
1. `allow_anonymous = true` — 任意MQTT客户端可连接，无需用户名密码
2. 认证插件全部注释（`auth-http`、`auth-jwt`）
3. 无 TLS 配置（`listener.tcp.external.ssl` 不存在）
4. 监听 `0.0.0.0:1883` — 局域网内任何机器都可访问
5. 内部端口 `0.0.0.0:11883` 设了 `allow_anonymous = false` 但未使用（BBSClient连的是1883）

---

## 攻击面全景

### 当前的代码/配置层面

```
BBSClient.__init__()
  └── client_id = agent_id          # 自声明身份，无验证
  └── connect(host, port)            # 无username/password参数
  └── 无 TLS 加密

WorkerAgent
  └── subscribe("agent/board/task/+/input")  # 任何人可publish到此topic
  └── 任务内容含llm prompt → 可诱导泄露API Key

rmqtt 配置
  └── allow_anonymous = true         ← 无认证
  └── 认证插件全部注释
  └── 无 topic ACL 机制
```

### 🎭 A 级：身份假冒

| 攻击 | 方式 | 后果 |
|------|------|------|
| AgentBoard 冒充 | 任意MQTT客户端连接，设client_id="master" | 取消所有任务、注入虚假任务 |
| WorkerAgent 冒充 | 设client_id="agent_gpt" 抢任务 | 窃取agent处理的数据/密钥 |
| 冒认同名上线 | 真实agent离线时以同一ID重连 | LWT被覆盖，全面接管身份 |

**rmqtt 特有**：`max_clientid_len = 65535` 无限制，client_id 为任意字符串即可。

### 📡 B 级：消息窃听

| 攻击 | 方式 | 后果 |
|------|------|------|
| 订阅所有任务输出 | `subscribe agent/board/task/+/output` | 获取所有agent处理结果 |
| 订阅节点状态 | `subscribe agent/node/+/status` | 掌握agent集群拓扑 |
| 订阅实时思考流 | `subscribe agent/node/+/stdout` | 监控agent思考过程，含敏感信息 |

**rmqtt 特有**：`max_subscriptions = 0`（不限制）且MQTT协议默认topic无ACL，任何订阅都会被允许。

### 💉 C 级：任务注入

| 攻击 | 方式 | 后果 |
|------|------|------|
| 注入恶意任务 | `publish agent/board/task/hacked/input` = 恶意prompt | WorkerAgent 可能泄漏密钥/执行危险操作 |
| 伪造控制信号 | `publish agent/board/task/hacked/signal = [CANCEL]` | 中断任务 |
| 污染工作记忆 | `publish agent/board/task/hacked/keyinfo` | 影响agent判断 |

### 🧨 D 级：rmqtt 特有风险点

| 风险 | 说明 |
|------|------|
| **监听0.0.0.0** | 非127.0.0.1，同局域网任何机器可连接1883端口 |
| **高并发上限** | `max_connections = 1,024,000`，便于DoS但不至于构成额外风险 |
| **QoS队列溢出** | `max_mqueue_len = 1000`，合理限制 |
| **Session有效期** | `session_expiry_interval = "2h"`，离线session保留2小时，可被利用 |
| **无rate limit** | 无每客户端消息速率限制配置 |
| **无审计日志** | 仅基础日志（info级别），无连接/操作审计 |

---

## rmqtt 可用的加固能力

### ✅ 可用但现在未启用

| 功能 | rmqtt配置项 | 启用方式 |
|------|------------|---------|
| **密码认证** | `rmqtt-auth-http` 插件 | 在 `plugins.default_startups` 加入 `"rmqtt-auth-http"`，配置HTTP认证API地址 |
| **JWT认证** | `rmqtt-auth-jwt` 插件 | 在 `plugins.default_startups` 加入 `"rmqtt-auth-jwt"`，配置JWT密钥 |
| **Topic重写/ACL** | `rmqtt-topic-rewrite` 插件 | 基于规则重写主题，可实现访问控制 |
| **系统主题监控** | `rmqtt-sys-topic` 插件 | 启用后可监控 $SYS/broker/... 系列指标 |
| **消息存储** | `rmqtt-message-storage` | 持久化消息历史，用于审计 |
| **TLS** | `listener.tcp.external.ssl` | 需配置证书路径，启用SSL/TLS加密 |

### ⚠️ rmqtt 与 EMQX 的认证差异

| 特性 | EMQX | rmqtt |
|------|------|-------|
| 内置用户名密码 | ✅ 内建、无需插件 | ❌ 需 `rmqtt-auth-http` 插件+外部HTTP服务 |
| Dashboard管理界面 | ✅ 自带Web UI | ❌ 仅有HTTP API（`rmqtt-http-api`已启用） |
| RBAC/ACL规则 | ✅ 内建 | ❌ 需 `rmqtt-topic-rewrite` 或应用层实现 |
| 热加载配置 | ✅ 支持 | 部分支持 |
| 社区插件生态 | 丰富 | 较小（rmqtt核心插件覆盖基础需求） |

---

## 防御方案（基于rmqtt）

### 层级 1：快速加固（不改代码，30分钟）

```toml
# 1. 用 rmqtt-auth-http 插件：连接时调HTTP API验证身份
plugins.default_startups = [
    "rmqtt-web-hook",
    "rmqtt-http-api",
    "rmqtt-auth-http",        # 取消注释
]

# 2. auth-http 配置（在 etc/plugins/ 目录下新建 rmqtt-auth-http.toml）
# 设一个简单的本地验证HTTP端点，返回 allow/deny
[auth_http]
url = "http://127.0.0.1:8080/auth"
method = "POST"
```

**或更简单**：如果不需要外部认证服务，可以把监听地址从 `0.0.0.0` 改为 `127.0.0.1`：

```toml
listener.tcp.external.addr = "127.0.0.1:1883"  # 只监听本机
```

这直接把攻击面从**局域网所有机器**缩小到**仅本机进程**。

### 层级 2：应用层身份验证（改代码，2-4小时）

与具体broker无关，参见 [mqtt_vs_file_bbs.md](./mqtt_vs_file_bbs.md) 中的方案：

| 机制 | 说明 |
|------|------|
| **任务签名(HMAC)** | AgentBoard签名 → WorkerAgent验签，验证任务来源 |
| **挑战-握手** | WorkerAgent接收任务前验证Board身份 |
| **nonce+时间戳** | 防重放攻击 |
| **每agent独立MQTT credentials** | 通过环境变量注入，不硬编码 |

### 层级 3：生产级部署

```toml
# rmqtt 完整安全配置
listener.tcp.external.allow_anonymous = false   # 禁止匿名

plugins.default_startups = [
    "rmqtt-auth-jwt",             # JWT认证（比auth-http更适合agent集群）
    "rmqtt-topic-rewrite",        # Topic ACL
    "rmqtt-sys-topic",            # 系统监控
    "rmqtt-web-hook",             # Webhook通知
    "rmqtt-http-api",             # HTTP API
]

# TLS 配置
[listener.tcp.external.ssl]
enable = true
addr = "0.0.0.0:8883"
certfile = "./etc/certs/server.pem"
keyfile = "./etc/certs/server.key"
```

---

## 补救优先级（立即能用）

| 优先级 | 措施 | 难度 | 效果 |
|--------|------|------|------|
| **P0 🔴** | `listener.tcp.external.addr = "127.0.0.1:1883"` | 改1行配置 | 攻击面从局域网→本机 |
| **P0 🔴** | 启用 `rmqtt-auth-http` + 简单认证端点 | 中等 | 防未授权连接 |
| **P1 🟡** | 应用层HMAC任务签名 | 代码改动 | 防任务注入/伪造 |
| **P2 🟢** | 改用internal端口11883（已有认证） | 改BBSClient配置 | 利用rmqtt已有安全配置 |
| **P3 🟢** | TLS加密 | 配置+证书 | 防局域网窃听 |

---

## 与文件BBS的安全对比（基于rmqtt实际配置）

| | 文件BBS | MQTT BBS（当前rmqtt配置） | MQTT BBS（加固后） |
|--|---------|--------------------------|-------------------|
| 身份验证 | 文件权限(OS级) | ❌ `allow_anonymous=true` | ✅ auth-http或JWT |
| 传输加密 | 不涉及(本地文件) | ❌ 无TLS | ✅ TLS on port 8883 |
| 访问控制 | 文件权限(r/w) | ❌ 无topic ACL | ✅ topic-rewrite或应用层 |
| 攻击面 | 本机OS进程 | 🌐 局域网所有机器(`0.0.0.0:1883`) | 🔒 127.0.0.1或TLS+认证 |
| 审计追踪 | 文件修改时间 | ❌ 无（仅info日志） | ✅ sys-topic + web-hook |

**最直接的加固**：把 `0.0.0.0:1883` 改成 `127.0.0.1:1883` 只需改1行配置、30秒重启，攻击面就从局域网降到本机，与文件BMS同级。
