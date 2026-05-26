"""MQTT BBS 默认配置 — 全部从环境变量读取，无硬编码密码"""

import os as _os

# Broker
BROKER_HOST = _os.environ.get("MQTT_HOST", "127.0.0.1")
BROKER_PORT = int(_os.environ.get("MQTT_PORT", "1883"))

# 主题前缀
TOPIC_PREFIX = _os.environ.get("TOPIC_PREFIX", "agent/")

# 客户端
KEEPALIVE = int(_os.environ.get("MQTT_KEEPALIVE", "60"))
RECONNECT_DELAY = int(_os.environ.get("MQTT_RECONNECT_DELAY", "3"))
MAX_RECONNECT_DELAY = int(_os.environ.get("MQTT_MAX_RECONNECT_DELAY", "60"))

# 任务
DEFAULT_TASK_TIMEOUT = int(_os.environ.get("DEFAULT_TASK_TIMEOUT", "300"))

# QoS
QOS = {
    "input": int(_os.environ.get("QOS_INPUT", "1")),
    "output": int(_os.environ.get("QOS_OUTPUT", "1")),
    "signal": int(_os.environ.get("QOS_SIGNAL", "2")),
    "stdout": int(_os.environ.get("QOS_STDOUT", "0")),
    "stderr": int(_os.environ.get("QOS_STDERR", "0")),
    "status": int(_os.environ.get("QOS_STATUS", "1")),
    "claim": int(_os.environ.get("QOS_CLAIM", "1")),
}

# HMAC
HMAC_SECRET = _os.environ.get("MQTT_HMAC_SECRET", "Mqtt_bbs_hmac_secret_2026")

# MQTT 5.0
MQTT_VERSION = int(_os.environ.get("MQTT_VERSION", "5"))
CLEAN_START = _os.environ.get("MQTT_CLEAN_START", "true").lower() == "true"
SESSION_EXPIRY_INTERVAL = int(_os.environ.get("MQTT_SESSION_EXPIRY", "3600"))
MESSAGE_EXPIRY_INTERVAL = int(_os.environ.get("MQTT_MESSAGE_EXPIRY", "300"))
TOPIC_ALIAS_MAXIMUM = int(_os.environ.get("MQTT_TOPIC_ALIAS_MAX", "32"))

# 心跳
HEARTBEAT_INTERVAL = int(_os.environ.get("HEARTBEAT_INTERVAL", "30"))
HEARTBEAT_TIMEOUT = int(_os.environ.get("HEARTBEAT_TIMEOUT", "90"))

# MariaDB
DB_CONFIG = {
    "host": _os.environ.get("DB_HOST", "127.0.0.1"),
    "port": int(_os.environ.get("DB_PORT", "3306")),
    "user": _os.environ.get("DB_USER", "root"),
    "password": _os.environ.get("DB_PASSWORD", ""),
    "database": _os.environ.get("DB_NAME", "Mqtt_bbs"),
    "charset": "utf8mb4",
}
