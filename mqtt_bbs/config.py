"""MQTT BBS 默认配置"""

# 公共 EMQX 测试 Broker（无需注册）
BROKER_HOST = "127.0.0.1"
BROKER_PORT = 1883

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

# MariaDB 持久化配置
DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "mariadb",
    "database": "mqtt_bbs",
    "charset": "utf8mb4",
}
