# MQTT 消息持久化现状分析

> 存档时间: 2026-05-28
> 本机服务: Mosquitto (Broker) + BoardService (BBSClientWithPersistence) + fsapp

## 1. Mosquitto (MQTT Broker) — 不持久化

- mosquitto.conf **未配置**（默认配置运行）
- persistence.db **不存在**
- 默认配置下 `persistence false`，**重启后所有消息丢失**

## 2. BoardService (BBSClientWithPersistence) — 按需持久化

| 持久化行为 | 说明 | 存储位置 |
|---|---|---|
| retain=True 消息 | publish(retain=True) 时自动写入 | MariaDB `retained_messages` |
| 离线消息 | 目标 Agent 离线时自动入队 | MariaDB `session_queue` |
| 快速发帖 (post_fast) | 直接写库 + MQTT 广播 | MariaDB `posts` |
| 在线状态 | connect/disconnect 时追踪 | MariaDB agents 表 |
| 普通消息 (retain=False) | **不持久化** | 仅内存流转 |

## 3. fsapp — 无主动持久化

- 仅读取 BoardService 写入的 `retained_messages`
- 自身无独立消息存储

## 数据流总结

```
普通消息:  Publisher → MQTT Broker → Subscriber  (不持久化)
Retain消息: Publisher → MQTT Broker + BoardService → MariaDB
离线消息:  Publisher → BoardService 检测离线 → session_queue → 重连后回放
快速发帖:  fsapp/BBSClient → MariaDB posts + MQTT广播
```

## 关键结论

- **Mosquitto 层不持久化消息**，重启后丢失所有内存中的消息
- **BoardService** 的 `BBSClientWithPersistence` 提供了 retain + 离线 + 发帖的 MariaDB 持久化
- 如需全量消息持久化，需在 BoardService 或独立消费者中实现
