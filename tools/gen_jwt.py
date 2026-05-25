#!/usr/bin/env python3
"""JWT 令牌生成工具 — 替代 agent.env 中的预生成 JWT 明文

用法:
  python tools/gen_jwt.py master          # 生成 master 角色的 JWT
  python tools/gen_jwt.py agent_gpt       # 生成 agent_gpt 的 JWT
  python tools/gen_jwt.py --list          # 列出所有预置角色

输出: stdout 打印 JWT, 可通过管道写入文件或环境变量

安全性:
  - 不在磁盘上存储 JWT 明文
  - 只在运行时通过环境变量 MQTT_USERNAME / MQTT_PASSWORD 传递
  - 配合 .env / mykey.py 中的 JWT_SECRET 使用
"""
import sys, json, time, hmac, hashlib, base64

# 从环境变量读取密钥，fallback 到默认值（开发环境）
JWT_SECRET = __import__('os').environ.get('JWT_SECRET', 'bbs-browser-dev-secret-change-in-production')

# 预置角色
ROLES = {
    'master':    {'sub': 'master',    'clientid': 'master',    'username': 'master',    'role': 'board'},
    'dashboard': {'sub': 'dashboard', 'clientid': 'dashboard', 'username': 'dashboard', 'role': 'observer'},
    'agent_gpt': {'sub': 'agent_gpt', 'clientid': 'agent_gpt', 'username': 'agent_gpt', 'role': 'worker'},
    'agent_wang':{'sub': 'agent_wang','clientid': 'agent_wang','username': 'agent_wang','role': 'worker'},
}

def base64url_encode(data: bytes) -> str:
    return base64.urlsafe_b64encode(data).rstrip(b'=').decode()

def encode_jwt(payload: dict, secret: str) -> str:
    header = {'alg': 'HS256', 'typ': 'JWT'}
    header_b64 = base64url_encode(json.dumps(header, separators=(',', ':')).encode())
    payload_b64 = base64url_encode(json.dumps(payload, separators=(',', ':')).encode())
    signature = hmac.new(secret.encode(), f'{header_b64}.{payload_b64}'.encode(), hashlib.sha256).digest()
    sig_b64 = base64url_encode(signature)
    return f'{header_b64}.{payload_b64}.{sig_b64}'

def main():
    if len(sys.argv) < 2 or sys.argv[1] in ('-h', '--help'):
        print(__doc__)
        return
    
    if sys.argv[1] == '--list':
        print('可用角色:')
        for name, claims in ROLES.items():
            print(f'  {name:<15} role={claims["role"]}')
        return
    
    role_name = sys.argv[1]
    claims = ROLES.get(role_name)
    if not claims:
        print(f'错误: 未知角色 "{role_name}"', file=sys.stderr)
        print(f'可用: {", ".join(ROLES.keys())}', file=sys.stderr)
        sys.exit(1)
    
    now = int(time.time())
    payload = {
        **claims,
        'iat': now,
        'exp': now + 365 * 86400,  # 1年有效期
    }
    jwt = encode_jwt(payload, JWT_SECRET)
    print(jwt)

if __name__ == '__main__':
    main()
