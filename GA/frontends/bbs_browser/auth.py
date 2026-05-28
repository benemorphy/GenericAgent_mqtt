"""BBS Board Browser — 用户认证模块"""

import time, hashlib, secrets
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from pymysql.cursors import DictCursor
from .config import JWT_SECRET, JWT_EXPIRY_SECONDS
from .database import get_db

import bcrypt


def hash_password(password: str) -> str:
    """简单的加盐哈希（兼容旧 web_users 表，不破坏已有用户）"""
    salt = secrets.token_hex(8)
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(password: str, stored: str) -> bool:
    """验证密码（兼容旧 sha256+salt 格式）"""
    try:
        salt, h = stored.split(":", 1)
        return h == hashlib.sha256((salt + password).encode()).hexdigest()
    except Exception:
        return False


def hash_password_bcrypt(password: str) -> str:
    """bcrypt 哈希密码（users 表 V2 标准，符合设计文档）"""
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password_bcrypt(password: str, hashed: str) -> bool:
    """bcrypt 验证密码"""
    return bcrypt.checkpw(password.encode(), hashed.encode())


def create_jwt(user: dict) -> str:
    """签发 JWT（简化版，不用 pyjwt 依赖，防止额外安装）"""
    payload = {
        "sub": user["id"],
        "username": user["username"],
        "display_name": user["display_name"],
        "role": user.get("role", "viewer"),
        "exp": int(time.time()) + JWT_EXPIRY_SECONDS,
        "iat": int(time.time()),
    }
    # 简易 JWT 编码（无依赖，适合小型项目）
    import json, base64
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode()).rstrip(b"=").decode()
    sig = base64.urlsafe_b64encode(
        hashlib.sha256(f"{header}.{body}{JWT_SECRET}".encode()).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"


def decode_jwt(token: str) -> dict:
    """解码验证 JWT"""
    import json, base64
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("invalid token")
        header, body, sig = parts
        expected_sig = base64.urlsafe_b64encode(
            hashlib.sha256(f"{header}.{body}{JWT_SECRET}".encode()).digest()
        ).rstrip(b"=").decode()
        if sig != expected_sig:
            raise ValueError("signature mismatch")
        payload = json.loads(base64.urlsafe_b64decode(body + "=="))
        if payload.get("exp", 0) < time.time():
            raise ValueError("token expired")
        return payload
    except Exception as e:
        raise HTTPException(status_code=401, detail=f"登录无效: {e}")


def require_user(request: Request):
    """FastAPI 依赖注入 — 从 cookie 解析用户"""
    token = request.cookies.get("token")
    if not token:
        raise HTTPException(status_code=401, detail="请先登录")
    return decode_jwt(token)


def optional_user(request: Request):
    """可选用户注入（未登录时返回 None）"""
    token = request.cookies.get("token")
    if not token:
        return None
    try:
        return decode_jwt(token)
    except Exception:
        return None


def register_user(username: str, password: str, display_name: str = "") -> dict:
    """注册用户"""
    if len(username) < 2 or len(password) < 4:
        return {"error": "用户名至少2字符，密码至少4字符"}
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id FROM web_users WHERE username=%s", (username,))
    if cur.fetchone():
        db.close()
        return {"error": "用户名已存在"}
    pw_hash = hash_password(password)
    cur.execute(
        "INSERT INTO web_users (username, password_hash, display_name) VALUES (%s, %s, %s)",
        (username, pw_hash, display_name or username)
    )
    db.commit()
    uid = cur.lastrowid
    db.close()
    return {"ok": True, "user_id": uid}


def login_user(username: str, password: str) -> dict:
    """登录验证，返回 JWT"""
    db = get_db()
    cur = db.cursor()
    cur.execute("SELECT id, username, password_hash, display_name, role FROM web_users WHERE username=%s", (username,))
    user = cur.fetchone()
    if not user or not verify_password(password, user["password_hash"]):
        db.close()
        return {"error": "用户名或密码错误"}
    # 更新最后登录时间
    cur.execute("UPDATE web_users SET last_login=NOW() WHERE id=%s", (user["id"],))
    db.commit()
    db.close()
    token = create_jwt(user)
    return {"ok": True, "token": token, "user": {
        "id": user["id"], "username": user["username"],
        "display_name": user["display_name"], "role": user["role"],
    }}


# ═══════════════════════════════════════════
# Email 认证 V2（基于 users 表，替代 web_users）
# ═══════════════════════════════════════════

def register_user_email(email: str, password: str, nickname: str = "") -> dict:
    """通过 email 注册（users 表），密码用 bcrypt 哈希存储"""
    db = get_db()
    cur = db.cursor(DictCursor)
    # 检查是否已存在
    cur.execute("SELECT email FROM users WHERE email=%s", (email,))
    if cur.fetchone():
        db.close()
        raise HTTPException(400, "该邮箱已注册")
    password_hash = hash_password_bcrypt(password)
    cur.execute(
        "INSERT INTO users (email, password_hash, nickname, role) VALUES (%s,%s,%s,'user')",
        (email, password_hash, nickname),
    )
    db.commit()
    user_id = cur.lastrowid
    db.close()
    return {"ok": True, "user_id": user_id, "email": email, "nickname": nickname}


def login_user_email(email: str, password: str) -> dict:
    """通过 email 登录（users 表），bcrypt 密码验证"""
    db = get_db()
    cur = db.cursor(DictCursor)
    cur.execute(
        "SELECT id, email, password_hash, nickname, role FROM users WHERE email=%s",
        (email,),
    )
    user = cur.fetchone()
    db.close()
    if not user:
        raise HTTPException(401, "邮箱或密码错误")
    if not verify_password_bcrypt(password, user["password_hash"]):
        raise HTTPException(401, "邮箱或密码错误")
    token = create_jwt({"id": user["id"], "username": user["email"], "display_name": user["nickname"], "role": user["role"]})
    return {"ok": True, "token": token, "user": {
        "id": user["id"], "email": user["email"],
        "nickname": user["nickname"], "role": user["role"],
    }}


def send_verify_code(email: str) -> dict:
    """生成 6 位验证码，存入 users 表（模拟发送，不真发邮件）"""
    import random, string
    code = "".join(random.choices(string.digits, k=6))
    token = secrets.token_hex(32)
    expire = int(time.time()) + 600  # 10 分钟有效
    db = get_db()
    cur = db.cursor()
    cur.execute(
        "UPDATE users SET verify_code=%s, verify_token=%s, verify_expire=%s WHERE email=%s",
        (code, token, expire, email),
    )
    affected = cur.rowcount
    db.commit()
    db.close()
    if not affected:
        raise HTTPException(404, "该邮箱未注册")
    # 模拟发送（生产环境接入 SMTP）
    print(f"[SIMULATED EMAIL] To: {email}  Code: {code}  Token: {token[:16]}...")
    return {"ok": True, "msg": "验证码已发送（模拟）", "debug_code": code, "debug_token": token}


def check_verify(email: str, code: str, token: str) -> dict:
    """校验验证码"""
    db = get_db()
    cur = db.cursor(DictCursor)
    cur.execute(
        "SELECT verify_code, verify_token, verify_expire, status FROM users WHERE email=%s",
        (email,),
    )
    user = cur.fetchone()
    db.close()
    if not user:
        raise HTTPException(404, "邮箱未注册")
    if user.get("status") is not None and user["status"] != 1:
        raise HTTPException(403, "账号已被禁用")
    if int(time.time()) > user["verify_expire"]:
        raise HTTPException(400, "验证码已过期")
    if user["verify_code"] != code or user["verify_token"] != token:
        raise HTTPException(400, "验证码或 token 无效")
    return {"ok": True, "msg": "验证通过"}
