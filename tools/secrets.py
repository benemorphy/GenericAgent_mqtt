"""
Secrets Manager — 统一密钥加载

优先级: K8s Secret 文件 > 环境变量 > 默认值
本地开发: 环境变量
K8s 部署: Secret 挂载到 /etc/secrets/{KEY}

用法:
    from tools.secrets import get_secret
    pw = get_secret("DB_PASSWORD", "mariadb")
    jwt = get_secret("MQTT_PASSWORD")
"""

import os

def get_secret(key: str, default: str = "") -> str:
    """获取密钥，优先级：Secret 文件 > 环境变量 > 默认值

    Args:
        key: 密钥名称（如 DB_PASSWORD）
        default: 本地开发默认值

    Returns:
        密钥值
    """
    # 1. K8s Secret 文件（挂载到 /etc/secrets/{KEY}）
    secret_file = f"/etc/secrets/{key}"
    if os.path.isfile(secret_file):
        with open(secret_file) as f:
            return f.read().strip()

    # 2. 环境变量
    env_val = os.environ.get(key, "")
    if env_val:
        return env_val

    # 3. 默认值（仅本地开发）
    return default
