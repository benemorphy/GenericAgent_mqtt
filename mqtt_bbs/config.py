"""MQTT BBS 默认配置"""

# 本地 RMQTT Broker（已部署在 D:\tools\rmqtt-0.20.0）
# 可通过环境变量 MQTT_HOST / MQTT_PORT 覆写
import os as _os
BROKER_HOST = _os.environ.get("MQTT_HOST", "127.0.0.1")
BROKER_PORT = int(_os.environ.get("MQTT_PORT", "1883"))

# 主题前缀（多团队隔离用，例如 "team_a/"）
TOPIC_PREFIX = "agent/"

# 客户端配置
KEEPALIVE = 60
RECONNECT_DELAY = 3
MAX_RECONNECT_DELAY = 60

# 任务超时（秒）
DEFAULT_TASK_TIMEOUT = 300

# QoS 策略（按场景）
QOS = {
    "input": 1,     # 任务输入：至少一次
    "output": 1,    # 任务输出：至少一次
    "signal": 2,    # 信号：[ROUND_END] 精确一次
    "stdout": 0,    # 流式输出：最多一次
    "stderr": 0,    # 流式错误：最多一次
    "status": 1,    # 状态变更：至少一次
    "claim": 1,     # 认领：至少一次
}

# HMAC 任务签名密钥（Zero Trust：防消息篡改）
# 所有 AgentBoard 和 WorkerAgent 共享此密钥
# 可通过环境变量 MQTT_HMAC_SECRET 覆盖
import os as _os
HMAC_SECRET = _os.environ.get("MQTT_HMAC_SECRET", "mqtt_bbs_hmac_secret_2026")

# MariaDB 持久化配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "mariadb",
    "database": "mqtt_bbs",
    "charset": "utf8mb4",
}
