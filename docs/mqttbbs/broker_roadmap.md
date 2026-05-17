# Broker 路线图 — EMQX → rmqtt 迁移规划

> 时间: 2026-05-16
> 来源: https://github.com/rmqtt/rmqtt (947 Star, Rust, MIT, 活跃开发)

---

## 1. 当前状态

```
Broker: broker.emqx.io:1883 (公共 EMQX)
  └── 开发/测试阶段，零部署成本
  └── 已验证: Retain + LWT + 通配符订阅 + QoS 全部正常
  └── 依赖外部服务，不能用于生产
```

## 2. 备选方案对比

| 维度 | EMQX | rmqtt | Mosquitto |
|:----|:------|:------|:----------|
| 语言 | Erlang/OTP | Rust | C |
| 二进制大小 | ~200MB (Docker) | ~15MB (单文件) | ~3MB |
| 内存占用 | ~50-200MB | ~10-30MB | ~5-10MB |
| 公共测试 Broker | 有(broker.emqx.io) | 无 | 有(test.mosquitto.org) |
| Dashboard | 有(18083端口) | 无(需HTTP API) | 无 |
| 集群 | 自研方案 | Raft共识 | 桥接 |
| Library Mode | 无 | 有(嵌入Rust应用) | 无 |
| Windows部署 | Docker | ZIP二进制即用 | 安装包 |
| MQTT v5 | 支持 | 支持 | 部分支持 |
| WebHook | 支持 | 支持 | 需插件 |

## 3. rmqtt 关键特性（对 BBS 的价值）

| BBS 需求 | rmqtt 支持 | 说明 |
|:---------|:----------:|:-----|
| Retain 消息 | 有 | BBS帖子持久化的核心 |
| LWT 遗嘱 | 有 | Agent在线/离线检测 |
| 共享订阅 `$share` | 有 | 多个Worker负载均衡 |
| ACL 鉴权 | 有(内置+HTTP+JWT) | Agent级权限控制 |
| WebHook | 有 | 消息到达时触发回调 |
| HTTP API | 有 | 程序化管理主题 |
| QoS 0/1/2 | 有 | 流式输出/QoS2信号 |
| 离线消息 | 有 | Session持久化 |
| WebSocket | 有 | 浏览器Agent连接 |
| MQTT over QUIC | 有 | 低延迟连接 |
| Topic Rewrite | 有 | 主题重写/路由 |
| 消息桥接 | 有(Kafka/Pulsar/NATS) | 跨系统数据同步 |

## 4. 迁移路线图

```
Phase 1: 开发期 (当前)
  Broker: broker.emqx.io:1883 (公共EMQX, 零部署)
  工作: 开发BBS业务逻辑、调试Agent协作流程
  优势: 不用管Broker，专注代码

Phase 2: 本地测试
  Broker: rmqtt 单节点 (Docker或ZIP)
  部署:
    # Docker单行启动
    docker run -d --name rmqtt -p 1883:1883 -p 11883:11883 \
      -p 6060:6060 rmqtt/rmqtt:latest
    
    # 或Windows下载ZIP解压后:
    rmqtt -c rmqtt.toml
  
  验证: 所有已通过的测试在rmqtt上重跑一次
  风险: 公共EMQX和rmqtt在Retain行为上的细微差异

Phase 3: 多Agent生产
  Broker: rmqtt 3节点 Raft集群
  部署:
    # 3节点 Docker 集群
    docker run -d --name rmqtt1 ... --id 1
    docker run -d --name rmqtt2 ... --id 2
    docker run -d --name rmqtt3 ... --id 3
  
  配置: ACL + WebHook + 持久化
  优势: 高可用，本地控制，零外部依赖
```

## 5. 选择建议

### 选 rmqtt 的场景
- 需要本地控制 Broker（不能依赖公共服务）
- 需要单二进制部署（解压即用，无依赖）
- 需要 Library Mode（把Broker嵌入Rust应用）
- 对 Dashboard 没有强需求（用 HTTP API 代替）
- 需要高性能低资源占用（Rust vs Erlang）

### 选 EMQX 的场景
- 需要公共 Broker 做快速开发测试
- 需要 Dashboard 可视化管理
- 需要消息追踪调试能力
- 国内中文社区/文档需求

### 选 Mosquitto 的场景
- 最简单的部署（winget install）
- 极其有限的资源环境
- 只需要基础 MQTT 功能

## 6. rmqtt 单节点部署

### Docker
```bash
# 单节点
docker run -d --name rmqtt \
  -p 1883:1883 \
  -p 8883:8883 \
  -p 11883:11883 \
  -p 6060:6060 \
  rmqtt/rmqtt:latest
```

### Windows ZIP
```
1. 从 https://github.com/rmqtt/rmqtt/releases 下载最新ZIP
2. 解压到 D:/rmqtt/
3. 修改 rmqtt.toml 配置
4. 运行: rmqtt -c rmqtt.toml
```

### 验证
```bash
# 健康检查
curl "http://127.0.0.1:6060/api/v1/health/check"

# 订阅测试
mosquitto_sub -h 127.0.0.1 -t "agent/board/task/+/signal"

# 发布测试
mosquitto_pub -h 127.0.0.1 -t "test/hello" -m "world" -r
```

## 7. 客户端切换

从 EMQX 切换到 rmqtt 只需改一行代码：

```python
# 之前: 公共 EMQX
client = BBSClientWithPersistence("agent_a")

# 之后: 本地 rmqtt
client = BBSClientWithPersistence("agent_a", host="127.0.0.1", port=1883)
```

所有业务逻辑（AgentBoard / WorkerAgent / BBSClientWithPersistence）
完全不需要修改。

## 8. rmqtt 已知限制

1. 无 Dashboard -> 查看Agent在线状态需调 HTTP API
2. 无消息追踪 -> 调试消息流需要自己打日志
3. 公共社区 < EMQX -> 遇到问题可能需要读源码
4. 插件生态 < EMQX -> 大部分功能已内置，但扩展需要Rust

## 附: 参考资源

- rmqtt GitHub: https://github.com/rmqtt/rmqtt
- rmqtt DockerHub: https://hub.docker.com/r/rmqtt/rmqtt
- EMQX 公共 Broker: broker.emqx.io:1883
