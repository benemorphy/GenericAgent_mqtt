"""BBS Board Browser 配置"""

import os

# MariaDB 连接配置（与 Mqtt_bbs/config.py 保持一致）
DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
DB_PORT = int(os.environ.get("DB_PORT", "3306"))
DB_USER = os.environ.get("DB_USER", "root")
DB_PASSWORD = os.environ.get("DB_PASSWORD", "mariadb")
DB_NAME = os.environ.get("DB_NAME", "Mqtt_bbs")

# JWT 密钥（生产环境从环境变量读取）
JWT_SECRET = os.environ.get("JWT_SECRET", "bbs-browser-dev-secret-change-in-production")
JWT_EXPIRY_SECONDS = 86400 * 7  # 7 天

# SMTP 邮件配置（环境变量覆盖）
SMTP_HOST = os.environ.get("SMTP_HOST", "smtp.126.com")
SMTP_PORT = int(os.environ.get("SMTP_PORT", "465"))
SMTP_USER = os.environ.get("SMTP_USER", "benemorphy@126.com")
SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")  # 126 邮箱授权码
SMTP_USE_SSL = os.environ.get("SMTP_USE_SSL", "true").lower() == "true"

# Server
HOST = "0.0.0.0"
PORT = 8000
