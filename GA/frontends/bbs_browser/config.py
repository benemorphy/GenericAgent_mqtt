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

# Server
HOST = "0.0.0.0"
PORT = 8000
