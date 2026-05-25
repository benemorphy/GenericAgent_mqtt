#!/usr/bin/env python3
"""
Secrets Manager — 统一凭据加载接口

支持加载顺序（后覆盖前）:
  1. 默认值 (开发环境 fallback)
  2. 文件系统 (K8s Secret 挂载, Docker secrets)
  3. 环境变量 (最高优先级)

用法:
  from tools.secrets import get_secret
  
  # 从任意来源读取
  db_pass = get_secret("DB_PASSWORD", default="mariadb")
  
  # 从 K8s Secret 文件读取
  jwt_key = get_secret("JWT_SECRET", secret_path="/etc/secrets/jwt_secret")
"""

import os

def get_secret(key: str, default: str = "", secret_path: str = None) -> str:
    """获取凭据，优先级: env var > file > default
    
    Args:
        key: 环境变量名
        default: 默认值（开发环境用）
        secret_path: K8s Secret 挂载路径（如 /etc/secrets/db_password）
    
    Returns:
        凭据字符串
    """
    # 1. 环境变量最高优先级
    val = os.environ.get(key)
    if val:
        return val
    
    # 2. K8s Secret 文件挂载
    if secret_path and os.path.isfile(secret_path):
        with open(secret_path, 'r') as f:
            val = f.read().strip()
        if val:
            return val
    
    # 3. 默认值（开发环境 fallback）
    if default:
        return default
    
    return ""


def ensure_env(env_file: str = ".env") -> dict:
    """加载 .env 文件到 os.environ（不会覆盖已存在的环境变量）
    
    Args:
        env_file: .env 文件路径
    
    Returns:
        已加载的键值对字典
    """
    loaded = {}
    if not os.path.isfile(env_file):
        return loaded
    
    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith('#'):
                continue
            if '=' not in line:
                continue
            key, val = line.split('=', 1)
            key, val = key.strip(), val.strip()
            if key and not os.environ.get(key):
                os.environ[key] = val
                loaded[key] = val
    
    return loaded


# 快速测试
if __name__ == '__main__':
    print("=== Secrets Manager ===")
    loaded = ensure_env()
    if loaded:
        print(f"已加载 {len(loaded)} 个环境变量")
    else:
        print("无 .env 文件或已全部加载")
    
    # 测试读取
    for key in ['MQTT_USERNAME', 'MQTT_PASSWORD', 'DB_PASSWORD', 'JWT_SECRET']:
        val = get_secret(key, default="(未设置)")
        if 'PASSWORD' in key or 'SECRET' in key:
            val_display = val[:4] + '****' if len(val) > 4 else '****'
        else:
            val_display = val
        print(f"  {key} = {val_display}")
