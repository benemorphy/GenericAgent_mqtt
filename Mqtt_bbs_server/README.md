# Mqtt_bbs 在 Beneh 中的使用

## Beneh 项目内的 MQTT 客户端代码

```
Beneh/
├── Mqtt_bbs_client/           ← 客户端库（自有副本，不依赖外部）
│   ├── client.py              BBSClient — MQTT连接封装
│   ├── board_client.py        BoardClient — 公告板 CRUD
│   ├── types.py               TaskMessage / TaskOutput / TaskStatus
│   ├── config.py              配置（全环境变量驱动）
│   ├── plugin.py              插件系统
│   ├── registry.py            能力注册表
│   ├── rate_limiter.py        速率限制
│   └── audit_log.py           审计日志
│
└── README.md  ← 本文件
```

## 服务端（外部）

MQTT BBS 服务端代码位于独立项目：
**`D:\open_claw_agent\Mqtt_bbs`**

包含 BoardService、BBScheduler、DAGWorkflow 等服务端组件。

## 引入方式

```python
# 直接从 Beneh 内引入（无需 pip install 外部包）
from Mqtt_bbs_client import BBSClient, BoardClient
from Mqtt_bbs_client.types import TaskMessage, TaskOutput, TaskStatus
```
