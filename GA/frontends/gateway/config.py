"""网关配置 — 继承 bbs_browser 配置，扩展 MQTT 配置"""

from frontends.bbs_browser.config import *

# MQTT Broker 配置（Dashboard 实时推送用）
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

# md_server_rs 地址
MD_SERVER_URL = os.environ.get("MD_SERVER_URL", "http://127.0.0.1:8899")
