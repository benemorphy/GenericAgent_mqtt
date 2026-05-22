"""BBS Board Browser — 用户认证模块"""

import time, hashlib, secrets
from fastapi import Request, HTTPException
from fastapi.responses import RedirectResponse

from .config import JWT_SECRET, JWT_EXPIRY_SECONDS
from .database import get_db


def hash_password(password: str) -> str:
    """简单的加盐哈希（生产环境建议换 bcrypt）"""
    salt = secrets.token_hex(8)
    return salt + ":" + hashlib.sha256((salt + password).encode()).hexdigest()


def verify_password(password: str, stored: str) -> bool:
    """验证密码"""
    try:
        salt, h = stored.split(":", 1)
        return h == hashlib.sha256((salt + password).encode()).hexdigest()
    except Exception:
        return False


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
