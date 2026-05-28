"""网关配置 — 继承 bbs_browser 配置，扩展 MQTT 配置"""

from frontends.bbs_browser.config import *

# MQTT Broker 配置（Dashboard 实时推送用）
MQTT_HOST = os.environ.get("MQTT_HOST", "127.0.0.1")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_USERNAME = os.environ.get("MQTT_USERNAME", "")
MQTT_PASSWORD = os.environ.get("MQTT_PASSWORD", "")

# md_server_rs 地址
MD_SERVER_URL = os.environ.get("MD_SERVER_URL", "http://127.0.0.1:8899")

# ── Email 认证配置 ──
SMTP_HOST = os.environ.get("SMTP_HOST", "")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "587"))
SMTP_USER = os.environ.get("SMTP_USER", "")
SMTP_PASS = os.environ.get("SMTP_PASS", "")
SMTP_FROM = os.environ.get("SMTP_FROM", "noreply@example.com")

# JWT 密钥（与 bbs_browser 共享，生产环境从环境变量读取）
JWT_SECRET = os.environ.get("JWT_SECRET", "bbs-browser-dev-secret-change-in-production")
