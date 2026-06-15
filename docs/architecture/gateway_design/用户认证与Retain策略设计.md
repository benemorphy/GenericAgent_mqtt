# 用户认证体系重构 + MQTT Retain策略设计

> 生成时间: 2026-05-28
> 基于: BoardService Rust 源码 (register.rs, db.rs, models.rs, config.rs) + 当前架构

---

## 第一部分：用户认证体系重构

### 1.1 当前认证架构 (问题)

```
Mosquitto                BoardService                MariaDB
─────────               ────────────                ───────
密码文件认证             随机token+JWT               bbs_users表
(mosquitto_passwd)      (无密码验证)                 (无密码字段)
```

**核心问题：**
1. Mosquitto 的 `mosquitto_passwd` 文件管理，无法自助注册
2. `bbs_users` 表只有 `token, name, board`，没有密码、邮箱、状态等字段
3. BoardService 注册时不管 MQTT 用户名是谁，只要连上 Broker 就能注册
4. 远端用户增加需要 SSH 到服务器改密码文件，不可扩展

### 1.2 目标架构

```
用户/客户端              FastAPI Gateway:8000           Mosquitto (匿名)
─────────────           ──────────────────           ─────────────────
浏览器访问页面           统一认证入口                   允许匿名TCP连接
远端MQTT客户端          ┌─────────────────┐           (或TLS证书)
                       │  auth.routes:    │
                       │  /login          │                │
                       │  /register       │                │
                       │  /api/verify/send│          MQTT 1883
                       │  /api/login      │                │
                       └────────┬────────┘                │
                                │                          │
                                ▼                          ▼
                          MariaDB                   BoardService
                        ──────────                ─────────────
                        users 表                  MQTT 注册网关
                        (密码hash/email/          只验证JWT签名
                         验证码/状态)             upsert bbs_users
                        bbs_users 表
                        (保留,加user_id外键)
```

**关键变更：**
1. **认证上移**：用户注册/登录/邮箱验证码 → Gateway:8000 (Python FastAPI)
2. **BoardService 精简**：只保留 MQTT 注册网关，验证 JWT 签名，不再处理 HTTP
3. **统一 users 表**：替代现有的 web_users 表，Gateway 和 BoardService 共用

### 1.3 数据库新增: users 表

```sql
-- ── V2 用户表 (Email认证) ──
CREATE TABLE IF NOT EXISTS users (
    user_id       BIGINT AUTO_INCREMENT PRIMARY KEY,    -- 内部ID
    email         VARCHAR(255) NOT NULL UNIQUE,          -- Email (登录凭证)
    password_hash VARCHAR(255) NOT NULL,                -- bcrypt 哈希
    nickname      VARCHAR(64) DEFAULT '',               -- 昵称
    role          VARCHAR(32) DEFAULT 'user',           -- 角色: user/admin/service
    status        TINYINT DEFAULT 1,                    -- 1=启用 0=禁用
    verify_code   VARCHAR(6) DEFAULT '',                -- 验证码
    verify_token  VARCHAR(64) DEFAULT '',               -- 验证token (防重放)
    verify_expire BIGINT DEFAULT 0,                     -- 验证码过期时间戳(秒)
    last_login    DATETIME,                             -- 最后登录时间
    created_at    DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at    DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    INDEX idx_email (email),
    INDEX idx_status (status)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
```

**`bbs_users` 表保持不变**（保留 token/name/board 用于已注册客户端的 JWT 验证），也添加外键关联 users：

```sql
-- 现有 bbs_users 表添加 user_id 外键
ALTER TABLE bbs_users ADD COLUMN user_id BIGINT DEFAULT NULL;
ALTER TABLE bbs_users ADD INDEX idx_user_id (user_id);
```

### 1.4 Gateway 新增认证模块

#### 1.4.1 Python 模块结构

认证功能部署在已有的 Gateway (FastAPI:8000) 中，而非 BoardService：

```
frontends/gateway/
├── main.py                ← 已有，挂载 auth router
├── config.py              ← 修改：添加 JWT/SMTP/DB 配置
├── routers/
│   ├── auth.py            ← 新增：注册/登录/邮箱验证码路由
│   └── ...
└── database.py            ← 修改：添加 users 表 CRUD
```

BoardService 变化最小化：

```
board_service_rs/src/
├── handlers/
│   ├── register.rs        ← 修改：接收 Gateway 签发的 JWT，验证后 upsert bbs_users
│   └── ...
├── db.rs                  ← 修改：从 users 表读取 JWT_SECRET（共享密钥）
├── config.rs              ← 修改：添加 jwt_secret 配置（从 Gateway 共享）
└── ...
```

#### 1.4.2 认证架构

```
┌─────────────────────────────────────────────────────────────┐
│                   用户旅程 (典型流程)                          │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  浏览器/客户端           FastAPI Gateway:8000                │
│      │                        │                              │
│      ├──(1) POST /api/verify/send ────────────► 生成验证码    │
│      │   {email}                   │           SMTP发邮件     │
│      │                             │           users表写     │
│      │◄──(2) {success, verify_token}                        │
│      │                             │                        │
│      ├──(3) POST /api/register ──────────────► bcrypt哈希    │
│      │   {email, code, token, pwd}│          users表写入     │
│      │                             │           bbs_users创建 │
│      │◄──(4) {jwt, token, user_id}                          │
│      │                             │                        │
│      ├──(5) MQTT Connect ──────────► Mosquitto 匿名允许      │
│      │   username=email                                      │
│      │                             │                        │
│      ├──(6) agent/bbs/X/register ──► BoardService            │
│      │   {jwt, agent_id}           │   验证JWT签名           │
│      │                             │   upsert bbs_users     │
│      │◄──(7) {ok, token, ...}                               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

#### 1.4.3 API 路由 (FastAPI Gateway:8000)

```python
# frontends/gateway/routers/auth.py (新增)

@router.post("/api/register")
async def register(email: str, verify_code: str, password: str):
    """注册新用户"""
    # 1. 验证 verify_code + verify_token (防重放)
    user = db.find_user_by_email(email)
    if not user or user.verify_code != verify_code or time.time() > user.verify_expire:
        raise HTTPException(400, "验证码无效或已过期")
    # 2. bcrypt 哈希密码
    hashed = bcrypt.hashpw(password.encode(), bcrypt.gensalt())
    # 3. 写入 users 表
    db.insert_user(email=email, password_hash=hashed)
    # 4. 创建 bbs_users 记录 (token=UUID)
    token = db.create_bbs_user(user_id=user.id, name=email, board="default")
    # 5. 签发 JWT
    jwt = create_jwt({"user_id": user.id, "email": email, "role": "user"})
    # 6. 清除验证码 (一次性)
    db.clear_verify_code(email)
    return {"jwt": jwt, "token": token, "user_id": user.id}

@router.post("/api/verify/send")
async def send_verify(email: str):
    """发送邮箱验证码"""
    code = f"{random.randint(100000, 999999)}"
    verify_token = secrets.token_urlsafe(32)
    expire = int(time.time()) + 300
    db.save_verify_code(email, code, verify_token, expire)
    if DEV_MODE:
        logger.info(f"[DEV] 验证码 for {email}: {code}")
    else:
        send_email_smtp(email, f"您的验证码是: {code}")
    return {"success": True, "expire_in": 300, "verify_token": verify_token}

@router.post("/api/verify/check")
async def check_verify(email: str, verify_code: str, verify_token: str):
    """校验验证码"""
    user = db.find_user_by_email(email)
    if not user or user.verify_code != verify_code or user.verify_token != verify_token:
        raise HTTPException(400, "验证码或token无效")
    if time.time() > user.verify_expire:
        raise HTTPException(400, "验证码已过期")
    return {"success": True}

#### 1.4.3 MQTT 注册流程 (修改)

```
客户端 -> MQTT Connect (username=email, password=明文密码)
  -> Mosquitto 匿名允许连接
  -> 客户端发布 agent/bbs/{board}/register
     { "name": "user@example.com", "password": "xxx", "verify_code": "123456", "agent_id": "..." }

BoardService 收到注册请求:
  1. 从 payload 中提取 name + password + verify_code
  2. 查 users 表: SELECT * FROM users WHERE email = name
  3. 验证 verify_code 和 verify_token 有效
  4. bcrypt.verify(password, user.password_hash)
  5. 验证通过 -> 签发 JWT (含 user_id, role, email)
  6. 清除 verify_code/verify_token (一次性)
  7. upsert bbs_users (token=新UUID, name=email, board=board_key)
  8. 发布响应: { "token": "...", "jwt": "...", "user_id": "..." }
  9. 验证失败 -> 发布错误响应: { "error": "auth_failed" }
```

#### 1.4.4 BbsRequest 扩展

```rust
// models.rs 新增字段
pub struct BbsRequest {
    // ... 现有字段
    pub password: Option<String>,         // 新增: 登录密码
    pub email: Option<String>,            // 新增: 邮箱
    pub verify_code: Option<String>,      // 新增: 邮箱验证码
    pub verify_token: Option<String>,     // 新增: 验证token (防重放)
}
```

#### 1.4.5 Config 变更

**Gateway (Python):**

```python
# frontends/gateway/config.py 新增
JWT_SECRET = os.environ.get("JWT_SECRET", "dev-secret-change-in-prod")
JWT_EXPIRY_SECONDS = int(os.environ.get("JWT_EXPIRY_SECONDS", "86400"))

SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@example.com")

DEV_MODE = os.environ.get("DEV_MODE", "true").lower() == "true"
```

Gateway 依赖: `pip install bcrypt==4.1.0 pydantic[email] ...`

**BoardService (Rust) — 精简:**

```rust
// config.rs — 只保留 jwt_secret
pub struct Config {
    // ... 现有参数
    /// JWT 密钥 (与 Gateway 共享)
    #[arg(long, default_value = "dev-secret-change-in-prod", env = "JWT_SECRET")]
    pub jwt_secret: String,
}
```

### 1.5 密码安全

```python
# Gateway (Python) — bcrypt 哈希
import bcrypt

def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())
```

依赖: `pip install bcrypt==4.1.0` (Python), BoardService 无需密码处理

### 1.6 部署配置

Mosquitto 配置 (VPS 匿名模式):

```
# mosquitto.conf
listener 1883
allow_anonymous true

# 可选: TLS 加密
listener 8883
cafile /etc/mosquitto/certs/ca.crt
certfile /etc/mosquitto/certs/server.crt
keyfile /etc/mosquitto/certs/server.key
require_certificate false
```

Gateway (FastAPI:8000) 配置:

```env
# 邮箱验证码 (SMTP)
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USER=your_email@gmail.com
SMTP_PASS=app_password
SMTP_FROM=noreply@example.com
DEV_MODE=true              # 开发模式: 验证码打印到日志

# JWT
JWT_SECRET=your-jwt-secret
JWT_EXPIRY_SECONDS=86400

# MariaDB (已有, 复用 Gateway 配置)
# 参考 frontends/bbs_browser/config.py
```

BoardService 配置 (精简):

```env
# 不再需要 HTTP_PORT / SMTP
# 只需共享 JWT_SECRET
JWT_SECRET=your-jwt-secret
```

---

## 第二部分：MQTT Retain 策略

### 2.1 架构现状

当前 `mqtt_handler.rs` 中 `publish_response` 的 retain 标志始终为 `false`（见 L113）：

```rust
// mqtt_handler.rs L113
client.publish(&topic, QoS::AtLeastOnce, false, bytes).await;
```

### 2.2 建议 Retain 方案

#### 2.2.1 哪些消息值得 Retain

| 主题模式 | 内容 | 保留周期 | Retain? | 理由 |
|---------|------|---------|---------|------|
| `board/inspiration` | 最新灵感帖 | 24h | **是** | 新客户端上线立即看到最新灵感 |
| `board/stream/status` | 服务状态快照 | 1h | **是** | 新监控客户端知道全局状态 |
| `node/{agent_id}/status` | Agent 存活状态 | TTL*2 | **是** | 监控方立即知道是否在线 |
| `node/{agent_id}/capability` | 最新能力声明 | TTL*2 | **是** | 其他 Agent 不需要历史能力记录 |
| `bbs/register/response` | JWT 响应 | 不保留 | **否** | 每个客户端独立，retain 会导致串号 |
| `bbs/publish/notify` | 新帖推送 | 不保留 | **否** | 通知是即时事件，retain 无意义 |
| `board/curiosity` | 好奇心信号 | 不保留 | **否** | 流量型讨论，retain 丢失上下文 |

#### 2.2.2 实现方式

在 `mqtt_handler.rs` 的 `publish_response` 函数中，根据主题模式动态设置 retain：

```rust
/// 判断主题是否需要 retain
fn should_retain(topic: &str, payload: &serde_json::Value) -> bool {
    // 状态/信息类主题 retain
    if topic.contains("/status") || topic.contains("/capability") {
        return true;
    }
    // 灵感板最新帖 retain
    if topic.contains("/inspiration") && topic.contains("/response") {
        return true;
    }
    // 数据流状态 retain
    if topic.contains("/stream/status") {
        return true;
    }
    false
}

// publish_response 中:
let retain = should_retain(&topic, payload);
match client.publish(&topic, QoS::AtLeastOnce, retain, bytes).await {
    // ...
}
```

或者通过 MQTT v5 的 **Message Expiry Interval** 设置过期：

```rust
// 使用 MQTT v5 属性 (rumqttc 支持)
use rumqttc::{PublishProperties, QoS};

let mut props = PublishProperties::default();
props.message_expiry_interval = Some(3600); // 1小时后自动过期

client.publish_with_properties(&topic, QoS::AtLeastOnce, true, bytes, props).await;
```

#### 2.2.3 Mosquitto 配置

```conf
# mosquitto.conf — Retain 相关配置

# 最大 retain 消息数 (防止恶意填充)
retain_available true
max_queued_messages 1000

# 持久化 retain 消息到磁盘 (重启不丢失)
persistence true
persistence_file mosquitto.db
persistence_location /var/lib/mosquitto/
```

### 2.3 边界情况处理

1. **覆盖旧 Retain 消息**: 发布同主题新消息时 retain=true 会自动覆盖
2. **清除 Retain**: 发布空 payload 且 retain=true 的消息会清除该主题的 retained 消息
3. **客户端上线**: 订阅后立即收到所有匹配的 retained 消息（每个主题最多1条）
4. **大批量连接**: 如果1000个客户端同时连接，每个客户端都会收到 retained 消息，需要考虑带宽

---

## 第三部分：实施路线图

### 阶段一：数据库准备 (1天)
- [ ] 创建 `users` 表
- [ ] 修改 `bbs_users` 表添加 `user_id` 列
- [ ] 测试环境 Mariadb 执行迁移

### 阶段二：Gateway 认证模块开发 (2-3天)
- [ ] `frontends/gateway/routers/auth.py`: 新增注册/登录/邮箱验证码路由
- [ ] `frontends/gateway/database.py`: 新增 users 表 CRUD (insert_user, find_user_by_email, verify_user)
- [ ] `frontends/gateway/config.py`: 添加 JWT/SMTP 配置
- [ ] Gateway 依赖: `pip install bcrypt lettre` 等
- [ ] 修改 `BoardService register.rs`: 注册时验证 JWT, 不从 payload 取密码
- [ ] 修改 `BoardService config.rs`: 移除 HTTP_PORT/SMTP 参数, 添加 jwt_secret
- [ ] 修改 `BoardService publish_response`: 根据主题判断 retain

### 阶段三：Mosquitto 配置迁移 (0.5天)
- [ ] 切换到匿名模式或 TLS 模式
- [ ] 配置 retain 持久化

### 阶段四：客户端适配 (1天)
- [ ] `mqtt_client_register.py` 添加 jwt 参数
- [ ] 所有客户端更新注册逻辑：携带 JWT 注册 BoardService

---

## 附录：接口变更对照

| 接口 | 当前行为 | 新行为 |
|------|---------|--------|
| MQTT 连接 | Mosquitto 密码文件验证 | 匿名连接 |
| bbs/register | 只传 name, 接受任意客户端 | 传 jwt, BoardService 验证签名 |
| HTTP 注册/登录API | 无 | POST /api/register, POST /api/login (Gateway:8000) |
| HTTP 验证码API | 无 | POST /api/verify/send, POST /api/verify/check (Gateway:8000) |
| 消息发布 | retain=false | 状态类消息 retain=true |
