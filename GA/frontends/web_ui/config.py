"""Web UI 配置 — 继承 bbs_browser 配置，扩展 MQTT 及上游服务地址"""

from services.bbs_data.config import *

# MQTT Broker 配置（Dashboard 实时推送用）
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

# 上游服务地址（Caddy 直接反代，仅 Dashboard 等内部使用需直接 URL）
MD_SERVER_URL = os.environ.get("MD_SERVER_URL", "http://127.0.0.1:8899")
MF_SERVER_URL = os.environ.get("MF_SERVER_URL", "http://127.0.0.1:9900")
