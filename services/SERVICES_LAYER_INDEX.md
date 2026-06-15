# SERVICES LAYER — 服务层

运行中的后端进程，提供数据/功能/基础设施能力。

## 外部服务（Mqtt_bbs_server/）
| 服务 | 端口 | 语言 | 说明 |
|------|------|------|------|
| Mosquitto | 1883 | C | MQTT Broker |
| board_service_rs | 9100 | Rust | 公告板持久化 + 健康检查 |
| mqtt_webui_rs | 8900 | Rust | RMQTT 管理面板 |
| simphtml_rs | 8901 | Rust | HTML 简化引擎 |
| md_server_rs | 8899 | Rust | Markdown 文档服务 |
| rmqtt_auth_rs | 9090 | Rust | MQTT 认证回调 |
| MariaDB | 3306 | C | 关系数据库 |

## 基础设施服务（GA/）
| 服务 | 端口 | 说明 |
|------|------|------|
| **Caddy** (:8000) | 8000 | 反向代理网关 — `./Caddyfile` |
| FastAPI Web UI | 8001 | Web 管理面板 — `frontends/web_ui/main.py` |
| A-supply-analysis | 8765 | 供应链分析 |

## Python 后端服务（services/）
| 服务 | 说明 |
|------|------|
| `services/stats/stats_collector.py` | Broker 指标采集 |
