# mqtt_bbs 云端基础设施就绪度评估

> 基于 mqtt_bbs/ 源代码审查
> 目标: 作为云服务运行在 Kubernetes / 容器编排平台
> Generated: 2026-05-22

---

## 一、当前架构拓扑

```
当前（本地单机）                    云端目标（生产）
┌──────────────┐                   ┌──────────────────────────┐
│  RMQTT       │                   │  MQTT Broker Cluster     │
│  (单进程)    │                   │  (EMQX / Mosquitto HA)   │
└──────┬───────┘                   └──────────┬───────────────┘
       │ MQTT:1883                             │ MQTT:8883 (TLS)
       ▼                                       ▼
┌──────────────┐                   ┌──────────────────────────┐
│ BoardService │                   │  BoardService (K8s Pod)  │
│ (1实例)      │      ──→          │  ├─ replica: 2-3         │
│  ├─ SQLite   │                   │  ├─ 无状态水平扩展       │
│  └─ MariaDB  │                   │  └─ External MariaDB     │
└──────┬───────┘                   └──────────┬───────────────┘
       │ 文件系统                             │ 对象存储 (S3/OSS)
       ▼                                       ▼
┌──────────────┐                   ┌──────────────────────────┐
│ logging.basicConfig              │  Prometheus + Grafana    │
│ (stdout)      │                   │  + 结构化日志 (JSON)     │
└──────────────┘                   └──────────────────────────┘
```

## 二、Module Cloud-Readiness Checklist

| Module | 状态 | 关键缺口 |
|--------|------|---------|
| `board_service.py` | 本地可运行 | 无 SIGTERM、无 healthcheck、有状态 CapabilityRegistry |
| `board_client.py` | 客户端库 | 无重试退避、无连接池 |
| `client.py` (BBSClient) | 基础封装 | 无连接超时可配、无 TLS 认证 |
| `config.py` | 半环境变量化 | DB 密码明文、路径硬编码 |
| `persistence.py` | MariaDB 直连 | 无连接池、无迁移系统 |
| `whiteboard.py` | 本地模式 | 无分布式支持 |
| `bbs.py` | 业务逻辑 | 任务签名 HMAC 密钥硬编码 |
| `plugin_manager.py` | 插件系统 | 无热加载隔离 |
| `agent.env` | JWT 明文 | 已检入 Git |

## 三、关键缺口与改进方案

### 缺口A: 无启动/关闭生命周期管理 （P0）

**现状**: `main()` 只有 `try/except KeyboardInterrupt`，无 SIGTERM 处理，
无健康检查接口。容器编排平台(如 K8s) 依赖健康检查和优雅关闭。

**改进方案**:

```python
# board_service.py — 优雅关闭
import signal

class BoardService:
    def start(self):
        signal.signal(signal.SIGTERM, self._handle_sigterm)
        self._running = True
        # ... 现有逻辑 ...
    
    def _handle_sigterm(self, signum, frame):
        log.info("SIGTERM 收到，开始优雅关闭...")
        self._running = False
        # 1. 取消所有订阅
        # 2. 断开 MQTT (LWT 自动发 offline)
        self._client.disconnect()
        # 3. 关闭 DB 连接
        if self._mariadb:
            self._mariadb.close()
        # 4. 等待 inflight 消息完成（可选）
        # 5. 退出
```

```python
# 健康检查主题
# 订阅: system/healthcheck
# 返回: {"status": "ok", "uptime": 12345, "boards": 3, "plugins": 2}
#
# 订阅: system/healthcheck/liveness
# 返回: {"status": "alive"}  # 纯存活检测
#
# 订阅: system/healthcheck/readiness
# 返回: {"status": "ready", "db": "ok", "broker": "ok"}  # 含依赖检测
```

**优先级**: P0 (容器化前提)

---

### 缺口B: 配置管理云端化（P0）

**现状**: 配置散落在 `config.py`、`agent.env`、硬编码路径:
- `DB_CONFIG = {"password": "mariadb"}` — 明文密码
- `BOARDS_FILE = "boards.json"` — 路径硬编码
- `UPLOAD_DIR = None` — 无 S3 概念
- JWT token 明文在 `agent.env`

**改进方案**: 全部从环境变量读取

```python
# config.py — 云端配置
import os
from dotenv import load_dotenv
load_dotenv()

# Broker — 强制配置云端地址
BROKER_HOST = os.environ["MQTT_HOST"]           # 无默认值，未配置就抛错
BROKER_PORT = int(os.environ.get("MQTT_PORT", "8883"))
BROKER_TLS = os.environ.get("MQTT_TLS", "true").lower() == "true"

# 数据库 — 从 K8s Secret / Env 注入
DB_HOST = os.environ["DB_HOST"]
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ["DB_USER"]
DB_PASSWORD = os.environ["DB_PASSWORD"]
DB_NAME = os.environ.get("DB_NAME", "mqtt_bbs")

# 文件存储 — 支持 S3
STORAGE_BACKEND = os.environ.get("STORAGE_BACKEND", "local")  # local | s3
S3_BUCKET = os.environ.get("S3_BUCKET", "")
S3_REGION = os.environ.get("S3_REGION", "us-east-1")

# 服务发现
BROKER_DISCOVERY = os.environ.get("BROKER_DISCOVERY", "static")  # static | dns | k8s
```

```python
# secrets.py — 从安全源加载
class SecretManager:
    @staticmethod
    def get_db_password():
        # K8s Secret 文件 > 环境变量 > 本地开发默认
        secret_file = os.environ.get("DB_PASSWORD_FILE")
        if secret_file and os.path.isfile(secret_file):
            with open(secret_file) as f:
                return f.read().strip()
        return os.environ.get("DB_PASSWORD", "mariadb")
```

**配套措施**:
- `agent.env` 加入 `.gitignore`
- 改用 BoardService 发行临时 JWT，而非预生成

**优先级**: P0

---

### 缺口C: 无状态化改造（P1）

**现状**: BoardService 是有状态的:
- `CapabilityRegistry._agents` — 进程内 dict，多实例不一致
- `_webhooks` — 进程内 dict
- SQLite/MariaDB 直接访问

**问题**: Agent A 注册到实例1，Agent B 查询能力到实例2，实例2不知道 Agent A。

**改进方案**: 利用 MQTT Retain 消息作为共享状态层

```python
# CapabilityRegistry 去状态化
class CapabilityRegistry:
    def get_agents(self, capability=None):
        """不再查进程内 dict，通过 MQTT retain 消息构建实时快照"""
        agents = {}
        # 方案 A: 查询 MariaDB 中最近心跳
        # 方案 B: 用临时 subscriber 收集 node/+/capability retain 消息
        return agents
    
    def _on_query(self, topic, payload):
        """任何实例收到查询都能正确响应"""
        # MQTT Retain 在所有订阅者间一致
        pass
```

**核心思路**: BoardService 实例之间通过 MQTT Broker（Retain 消息）共享状态，
无需进程间通信。CapabilityRegistry 成为纯函数：读 retain → 过滤 → 响应。

**优先级**: P1

---

### 缺口D: 观测性零基础（P1）

**现状**:
- `logging.basicConfig` 硬编码格式，无法调整日志级别
- 无 metrics 输出
- 无 trace ID 透传

**改进方案**: 结构化日志 + Prometheus metrics

```python
# 结构化日志
import structlog
log = structlog.get_logger()
# 输出: {"event": "register", "agent_id": "alpha", "board": "test",
#        "duration_ms": 12, "time": "2026-05-22T..."}

# Prometheus Metrics
from prometheus_client import Counter, Histogram, start_http_server

MQTT_MESSAGES = Counter('mqtt_messages_total', 'Total MQTT messages',
                        ['type', 'board', 'status'])
PROCESSING_TIME = Histogram('mqtt_processing_seconds',
                            'Message processing time', ['handler'])
DB_QUERY_TIME = Histogram('db_query_seconds', 'DB query time')
DB_CONNECTIONS = Gauge('db_connections', 'Active DB connections')

# 启动 /metrics HTTP 端口（sidecar 抓取）
start_http_server(9090)
```

| Metric | Type | Labels | 说明 |
|--------|------|--------|------|
| `mqtt_messages_total` | Counter | type, board, status | 消息计数 |
| `mqtt_processing_seconds` | Histogram | handler | 处理延迟 |
| `db_query_seconds` | Histogram | query_type | 查询延迟 |
| `db_connections` | Gauge | — | DB 连接数 |
| `agents_online` | Gauge | board | 在线 Agent 数 |

**优先级**: P1

---

### 缺口E: 数据库迁移系统（P1）

**现状**: `_ensure_db()` 每次 `CREATE TABLE IF NOT EXISTS`，无版本号，无迁移。

**改进方案**:

```python
# db/migrations.py
MIGRATIONS = {
    1: """
        CREATE TABLE IF NOT EXISTS bbs_users (
            token VARCHAR(32) PRIMARY KEY,
            name VARCHAR(128) NOT NULL UNIQUE,
            board VARCHAR(128) NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );
    """,
    2: "ALTER TABLE bbs_posts ADD COLUMN edited_at DATETIME NULL;",
    3: "CREATE TABLE IF NOT EXISTS bbs_webhooks (board VARCHAR(128), url TEXT);",
}

def run_migrations(db):
    """幂等执行迁移"""
    db.execute("CREATE TABLE IF NOT EXISTS _schema_version (version INT PRIMARY KEY)")
    current = db.execute("SELECT MAX(version) as v FROM _schema_version").fetchone()
    current_v = current["v"] if current else 0
    
    for v in sorted(MIGRATIONS.keys()):
        if v > current_v:
            log.info(f"  Running migration v{v}...")
            for stmt in MIGRATIONS[v].strip().split(';'):
                if stmt.strip():
                    db.execute(stmt.strip())
            db.execute("INSERT INTO _schema_version (version) VALUES (%s)", (v,))
            log.info(f"  Migration v{v} done")
```

**优先级**: P1

---

### 缺口F: 文件存储 S3 适配（P1）

**现状**: 文件上传写到本地 `UPLOAD_DIR`，多实例无法共享。

**改进方案**: 抽象存储后端

```python
# storage.py
from abc import ABC, abstractmethod

class StorageBackend(ABC):
    @abstractmethod
    def save(self, path: str, data: bytes) -> str: ...
    @abstractmethod
    def load(self, path: str) -> bytes: ...

class LocalStorage(StorageBackend):
    """本地文件系统（开发/单机）"""
    def __init__(self, base_dir: str):
        self._base = base_dir
    def save(self, path, data):
        full = os.path.join(self._base, path)
        os.makedirs(os.path.dirname(full), exist_ok=True)
        with open(full, 'wb') as f:
            f.write(data)
        return path
    def load(self, path):
        with open(os.path.join(self._base, path), 'rb') as f:
            return f.read()

class S3Storage(StorageBackend):
    """S3 对象存储（云端）"""
    def __init__(self, bucket: str, region: str = "us-east-1"):
        import boto3
        self._s3 = boto3.client('s3', region_name=region)
        self._bucket = bucket
    def save(self, path, data):
        self._s3.put_object(Bucket=self._bucket, Key=path, Body=data)
        return f"s3://{self._bucket}/{path}"
    def load(self, path):
        resp = self._s3.get_object(Bucket=self._bucket, Key=path)
        return resp['Body'].read()

# 在 BoardService 中
STORAGE = S3Storage(bucket=cfg.S3_BUCKET) if cfg.STORAGE_BACKEND == "s3" \
          else LocalStorage(cfg.UPLOAD_DIR or "./uploads")
```

**优先级**: P1

---

### 缺口G: JWT/Secrets 管理（P0.5）

**现状**:
- `agent.env` 含 JWT 明文 token，已检入 Git
- `config.py` 含数据库明文密码
- 无密钥轮换机制

**改进**:
1. `agent.env` 加入 `.gitignore`
2. 临时 JWT：BoardService 在注册时动态生成 JWT（含过期时间），而非预生成
3. 密钥从环境变量或 K8s Secret 注入，无硬编码值

```python
# auth.py — JWT 管理
import jwt, time

JWT_SECRET = os.environ.get("JWT_SECRET", "")  # K8s Secret 注入

def issue_token(agent_id: str, role: str = "worker", ttl: int = 86400) -> str:
    return jwt.encode({
        "sub": agent_id,
        "role": role,
        "exp": int(time.time()) + ttl,
        "iat": int(time.time()),
    }, JWT_SECRET, algorithm="HS256")

def verify_token(token: str) -> dict:
    try:
        return jwt.decode(token, JWT_SECRET, algorithms=["HS256"])
    except jwt.ExpiredSignatureError:
        return {"error": "expired"}
    except jwt.InvalidTokenError:
        return {"error": "invalid"}
```

**优先级**: P0.5

---

### 缺口H: Container 化（P0）

**现状**: 无 Dockerfile，无编排配置。

**改进方案**:

```dockerfile
# Dockerfile.board_service
FROM python:3.11-slim

WORKDIR /app
COPY mqtt_bbs/ mqtt_bbs/
COPY pyproject.toml .

RUN pip install --no-cache-dir -e . && \
    rm -rf /root/.cache

EXPOSE 9090

HEALTHCHECK --interval=15s --timeout=3s --retries=3 \
    CMD python -c "import paho.mqtt.client as mqtt; c=mqtt.Client(); c.connect(os.environ['MQTT_HOST'], int(os.environ.get('MQTT_PORT','8883'))); c.disconnect()" \
    || exit 1

ENTRYPOINT ["python", "-m", "mqtt_bbs.board_service"]
```

```yaml
# docker-compose.yml (本地开发/CI)
version: '3.8'
services:
  broker:
    image: eclipse-mosquitto:2
    ports:
      - "1883:1883"
    volumes:
      - ./mosquitto.conf:/mosquitto/config/mosquitto.conf

  board-service:
    build:
      context: .
      dockerfile: Dockerfile.board_service
    environment:
      MQTT_HOST: broker
      MQTT_PORT: "1883"
      DB_HOST: mariadb
      DB_USER: root
      DB_PASSWORD: ${DB_PASSWORD:-mariadb}
      DB_NAME: mqtt_bbs
    depends_on:
      - broker
      - mariadb

  mariadb:
    image: mariadb:11
    environment:
      MYSQL_ROOT_PASSWORD: ${DB_PASSWORD:-mariadb}
      MYSQL_DATABASE: mqtt_bbs
    volumes:
      - mariadb_data:/var/lib/mysql

volumes:
  mariadb_data:
```

**优先级**: P0

---

## 四、改进路线图

| Phase | 项目 | 工时(估) | 依赖 |
|-------|------|---------|------|
| **P0** | 生命周期管理(signal + healthcheck) | 2h | 无 |
| **P0** | 配置环境变量化 | 1h | 无 |
| **P0** | Container 化(Dockerfile + docker-compose) | 4h | P0 前两项 |
| **P0.5** | Secrets 管理 + JWT 动态发行 | 3h | P0 配置项 |
| **P0.5** | `.gitignore agent.env` | 0.1h | P0.5 完成 |
| **P1** | 无状态化(去进程dict) | 4h | P0 |
| **P1** | 结构化日志 + Prometheus metrics | 4h | P0 |
| **P1** | 数据库迁移系统 | 2h | P0 |
| **P1** | S3 存储后端 | 3h | P0.5 |
| **P1.5** | Kubernetes Helm Chart | 4h | P1 全部 |
| **P2** | 多实例+HA 部署验证 | 8h | P1.5 |
| **P3** | 多区域桥接 + 数据分片 | 16h | P2 |

**Phase 0 优先做**: 三项打底工作（~7小时），完成后即可跑在 K8s 上。

---

## 五、风险与取舍

| 风险 | 影响 | 缓解 |
|------|------|------|
| 无状态化破坏 CapabilityRegistry 实时性 | 能力查询延迟从<10ms升到~100ms | 增加内存缓存，TTL=心跳间隔 |
| S3 延迟高于本地文件 | 文件上传延迟增加 50-200ms | 文件元数据走 MQTT，内容异步上传 |
| 结构化日志增加 CPU 开销 | 日志吞吐下降 ~5% | 生产环境用 JSON 格式，开发环境用文本 |
| JWT 动态发行引入 BoardService 启动依赖 | Agent 必须等 BoardService 在线 | 增加 fallback 静态 token 模式 |
