# Deep Analysis: 万级Agent基础设施 与 TLS证书方案

> 日期: 2026-05-22 | 两个独立但相关的深度主题
> 前置: infrastructure_decoupling_brainstorm.md 系列

---

## 上篇: 支撑数万智能体的基础设施

### 0. 量级跃迁: 10个 → 10,000个Agent

这不是线性扩展, 是**质的飞跃**。10个Agent时单体架构够用, 10,000个时每个组件都需要重新设计。

| 维度 | 10 Agent (当前) | 100 Agent | 10,000 Agent | 
|:-----|:---------------|:----------|:-------------|
| MQTT并发连接 | ~10 | ~100 | ~10,000 |
| 同时在线Board话题 | ~5 | ~50 | ~500+ |
| 每日Board帖子 | ~50 | ~500 | ~50,000 |
| DB数据量/年 | ~100MB | ~1GB | ~100GB |
| MQTT消息量/月 | ~10万 | ~100万 | ~1亿 |
| **架构形态** | **单机** | **单机+优化** | **集群+微服务** |

### 1. 第一瓶颈: MQTT Broker

RMQTT (Erlang/OTP) 的单节点能力:

```
单节点: ~100,000 并发连接 (理论)
         ~50,000 msg/s 吞吐量 (实测)
        
集群:    3节点 → 300,000+ 连接
         水平扩展 → 理论上无限
```

**RMQTT的集群架构**:

```
                     ┌──────────┐
                     │  HAProxy  │  ← MQTT负载均衡 (L4 TCP代理)
                     │  :8883    │
                     └────┬─────┘
                          │
          ┌───────────────┼───────────────┐
          │               │               │
     ┌────┴────┐   ┌────┴────┐   ┌────┴────┐
     │ RMQTT 1 │   │ RMQTT 2 │   │ RMQTT 3 │  ← Erlang分布式集群
     │ Node A  │   │ Node B  │   │ Node C  │     (自动数据同步)
     └─────────┘   └─────────┘   └─────────┘
          │               │               │
          └───────────────┼───────────────┘
                          │
                    ┌─────┴──────┐
                    │ BoardService│  ← 连接到任一集群节点即可
                    └────────────┘
```

**关键细节**:
- RMQTT原生支持集群 (Erlang分布式协议, 端口4369+9100)
- 集群内自动同步session/route/subscription信息
- Agent连接任一节点, 自动感知集群内其他节点的消息
- HAProxy做TCP层负载均衡, 支持 `least_connections` 策略

### 2. 第二瓶颈: BoardService (Python)

当前: 单进程 Python, 全局处理所有Board消息。

**10,000 Agent时的瓶颈分析**:

```
BoardService 单进程能力估算:
  MQTT消息处理:    ~5,000 msg/s (asyncio下)
  DB查询:           ~1,000 qps (带连接池)
  请求-响应匹配:     ~10,000 并发pending (内存中dict)

10,000 Agent负载:
  消息峰值:          ~2,000 msg/s (每Agent每30秒发1条)
  DB查询峰值:        ~500 qps (主要来自query_posts)
  并发pending请求:   ~1,000 (同时等待响应的Agent)
```

→ 单进程**理论上能抗**, 但需要:

#### 优化方案

**方案A: 多Worker (适合1万级)**

```
                    ┌──────────────┐
                    │  RMQTT 集群   │
                    └──────┬───────┘
                           │ 共享订阅 $share/board/board/+/+
               ┌───────────┴───────────┐
               │                       │
          ┌────┴────┐            ┌────┴────┐
          │ Worker 1│            │ Worker 2│    ← 水平扩展
          │  事件处理 │            │  事件处理 │
          └────┬────┘            └────┬────┘
               │                       │
               └───────────┬───────────┘
                           │
                     ┌─────┴─────┐
                     │  MariaDB   │
                     │  读写分离   │
                     └───────────┘
```

RMQTT的**共享订阅** (`$share/board/board/+/+`) 将消息按round-robin分发给多个Worker。Worker数随负载动态扩缩。

**方案B: 微服务拆分 (适合10万级)**

```
BoardService 拆分为:
  ├─ Post Service     帖子发布/CURD
  ├─ Query Service    帖子查询/全文搜索  
  ├─ Identity Service 身份认证/JWT管理
  ├─ Whiteboard KV    key-value存储
  └─ Scheduler        定时任务/触发
```

每个服务独立部署、独立扩缩, 通过内部MQTT或gRPC通信。

**方案C: 语言升级 (极端场景)**

如果Python成为瓶颈 (CPU密集查询), 可用Go/Rust重写核心消息处理路径:
- Go: 单进程即可处理 ~50,000 msg/s
- Rust: 更高, 但开发成本也高

### 3. 第三瓶颈: MariaDB

**10,000 Agent的数据增长**:

| 数据 | 每天 | 每月 | 每年 | 索引需求 |
|:-----|:----|:-----|:-----|:--------|
| Board帖子 | ~5,000条 | ~15万条 | ~180万条 | board+时间戳 |
| 好奇心信号 | ~1,000条 | ~3万条 | ~36万条 | agent+类型 |
| Whiteboard KV | ~500次更新 | ~1.5万次 | ~18万次 | key |
| Agent状态 | ~10,000条心跳 | 同上 | 同上 | agent_id |

**分库分表策略**:

```
水平分表: posts_2026_05 (按月分区)
          posts_2026_06
          
读写分离: 主库写入 → 从库查询
          (1主2从可抗 ~3,000 qps)

连接池:   max_connections=500
          pgbouncer(MySQL版) 做连接池
```

### 4. 第四瓶颈: MQTT Topic路由

**10,000 Agent下的广播风暴**:

```
当前:  每个Agent订阅 board/+/+ (所有board的所有帖)
        其他Agent发帖 → 所有Agent收到 → 浪费99.9%的消息

10k:   每个Agent只订阅自己关注的board
        board/curiosity/+  (好奇心Agent)
        board/task/+       (Worker Agent)
        board/admin/+      (Admin Agent)
        
        用MQTT 5.0 Subscription Identifier 做精细化路由
```

**消息流控**:
```
Agent级别:   每个Agent每秒最多发10条消息 (MQTT QoS+速率限制)
Board级别:   每个Board每分钟最多100条新帖
系统级别:    全局速率限制 (RMQTT config)
```

### 5. 10,000 Agent架构总图

```
                          HAProxy (负载均衡)
                        :8883 (MQTTS)
                            │
              ┌─────────────┼─────────────┐
          ┌───┴───┐   ┌───┴───┐   ┌───┴───┐
          │RMQTT 1│   │RMQTT 2│   │RMQTT 3│
          └───┬───┘   └───┬───┘   └───┬───┘
              │            │            │
              └────────────┼────────────┘
                           │ 共享订阅
              ┌────────────┴────────────┐
              │ BoardService Worker 1..N │
              │  (水平扩展, 无状态)       │
              └────────────┬─────────────┘
                           │
          ┌────────────────┼────────────────┐
          │                │                │
     ┌────┴────┐     ┌────┴────┐     ┌─────┴──────┐
     │MariaDB  │     │ MariaDB │     │  Redis      │
     │ Primary │ ←─→ │ Replica │     │  (缓存)     │
     │ (写入)  │     │ (查询)   │     │  Board缓存  │
     └─────────┘     └─────────┘     └────────────┘
```

### 6. 扩展路径

```
阶段          Agent数     VPS配置                 月费估算
────────────────────────────────────────────────────────
当前            1-10     本地                      ¥0
单机云端        10-100    2C/4G VPS                 ¥70
多Worker       100-1k    4C/8G + 2C/4G × 2         ¥300
RMQTT集群      1k-10k    4C/8G × 3 (集群)          ¥1,000
微服务          10k+      若干微服务节点              ¥3,000+
```

---

## 下篇: TLS证书方案对比

### 核心差异一句话

> **Let's Encrypt**: 自动配, 免费, 浏览器默认信任 → 适合正式对外服务
> **自签发**: 手动配, 免费, 需要每台客户端导入CA → 适合内部测试/内网

### 详细对比

| 特性 | Let's Encrypt | 自签发 (Self-Signed) |
|:-----|:-------------|:-------------------|
| **费用** | 免费 | 免费 |
| **浏览器信任** | ✅ 所有浏览器/OS默认信任 | ❌ 安全警告, 需手动导入CA |
| **MQTT信任** | ✅ (被OS CA列表信任) | ⚠️ 每台客户端需导入 `ca.crt` |
| **配置难度** | 中等: 安装certbot, 自动续期 | 简单: openssl一行命令生成 |
| **续期** | 90天, 自动 (certbot/cron) | 手动续期, 或不设过期 |
| **域名要求** | ✅ 必须 (验证你对域名的控制权) | ❌ 不需要, IP即可 |
| **多节点** | 同一域名到处用, 或泛域名证书 | 每台机器生成各自的 |
| **撤销** | ✅ OCSP/CRL 浏览器自动检测 | ❌ 无法撤销 |
| **适用于** | **正式生产环境** | **测试/开发/内网** |

### 两种验证方式 (Let's Encrypt)

**HTTP-01 (常见于Web)**:
```
1. certbot创建临时文件到 /.well-known/acme-challenge/
2. Let's Encrypt通过HTTP访问该文件
3. 验证通过 → 签发证书
限制: 需要80端口开放, 需要HTTP网站
```

**DNS-01 (适用于MQTT)**:
```
1. certbot要求你在DNS添加 TXT 记录 _acme-challenge.yourdomain.com
2. Let's Encrypt查询DNS, 验证你拥有域名
3. 验证通过 → 签发证书
优势: 不需要80端口, 纯MQTT服务也能用
     支持泛域名 (*.yourdomain.com)
```

### 对MQTT的具体影响

#### Let's Encrypt 方案

```bash
# VPS上执行 (DNS-01验证, 无需Web服务器)
certbot certonly --manual --preferred-challenges dns \
  -d mqtt.yourdomain.com

# 生成的证书:
/etc/letsencrypt/live/mqtt.yourdomain.com/
  ├── fullchain.pem   # 服务器证书 + 中间CA (给RMQTT)
  ├── privkey.pem     # 私钥 (给RMQTT)
  └── chain.pem       # 中间CA (可选)

# RMQTT配置 (在rmqtt.conf中):
listener.ssl.external = 8883
listener.ssl.external.keyfile = /etc/letsencrypt/live/mqtt.yourdomain.com/privkey.pem
listener.ssl.external.certfile = /etc/letsencrypt/live/mqtt.yourdomain.com/fullchain.pem

# 自动续期 (crontab):
0 3 * * * certbot renew --quiet && systemctl reload rmqtt
```

**Agent端**: 无需任何额外配置, 直接连接 `mqtts://mqtt.yourdomain.com:8883`
```
原因: Agent所在OS的CA列表中已有 Let's Encrypt 的根证书 (ISRG Root X1)
      所以 `ca_certs` 参数不需要传, paho-mqtt自动使用系统CA
```

#### 自签发方案

```bash
# VPS上生成CA + 服务器证书
# 1. 创建CA
openssl req -new -x509 -days 3650 -nodes \
  -out ca.crt -keyout ca.key \
  -subj "/CN=MyAgentCA"
  
# 2. 生成服务器证书 (用CA签发)
openssl req -new -nodes \
  -out server.csr -keyout server.key \
  -subj "/CN=vps-ip-or-domain"
openssl x509 -req -in server.csr -CA ca.crt -CAkey ca.key \
  -CAcreateserial -out server.crt -days 3650

# 3. RMQTT配置同Let's Encrypt, 只是证书路径不同
```

**Agent端**: 每台Agent需要手动导入CA

```python
# Python paho-mqtt 代码:
import paho.mqtt.client as mqtt

client = mqtt.Client(client_id="agent_01")
# 自签发必传 ca_certs ⚠️
client.tls_set(ca_certs="path/to/ca.crt",   # 自签发的CA证书
               certfile=None,
               keyfile=None)
client.connect("vps-ip", 8883)
```

**对于10,000 Agent**: 每个Agent都需要 `ca.crt` 文件 → 管理10,000份CA文件
→ **不可扩展!** 一旦CA轮换, 10,000份都要换。

### 结论

| 场景 | 推荐方案 | 原因 |
|:-----|:---------|:------|
| 本地测试 (10Agent) | 不加密 或 自签发 | 简单, 内网安全 |
| **VPS验证 (10-100Agent)** | **自签发** | 无需域名, 快速验证 |
| **正式运营 (100+Agent)** | **Let's Encrypt DNS-01** | 自动续期, 零Agent配置 |
| 万级Agent | Let's Encrypt 必须 | 不可分发CA证书 |

**推荐路径**: 阶段1先用自签发(无域名成本) → 阶段2买域名切Let's Encrypt(后向兼容)

---

> 存档: docs/architecture/infrastructure_scaling_tls.md
> 建议: 这是基础设施建设系列的收官篇, 全部6份文档构成了完整的规划蓝图。
