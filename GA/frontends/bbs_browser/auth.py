"""BBS Board Browser — 用户认证模块

认证依赖（require_user, optional_user, decode_jwt）已统一移至 frontends/auth.py，
消费者请从 frontends.auth 直接导入。
"""

import time
import hashlib
import secrets
from fastapi import Request, HTTPException

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
    import json
    import base64
    header = base64.urlsafe_b64encode(json.dumps({"alg": "HS256", "typ": "JWT"}).encode()).rstrip(b"=").decode()
    body = base64.urlsafe_b64encode(json.dumps(payload, ensure_ascii=False).encode()).rstrip(b"=").decode()
    import hmac
    sig = base64.urlsafe_b64encode(
        hmac.new(JWT_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
    ).rstrip(b"=").decode()
    return f"{header}.{body}.{sig}"


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
    """通过 email 登录（users 表），bcrypt 密码验证，需已验证邮箱"""
    db = get_db()
    cur = db.cursor(DictCursor)
    cur.execute(
        "SELECT id, email, password_hash, nickname, role, verified FROM users WHERE email=%s",
        (email,),
    )
    user = cur.fetchone()
    db.close()
    if not user:
        raise HTTPException(401, "邮箱或密码错误")
    if not verify_password_bcrypt(password, user["password_hash"]):
        raise HTTPException(401, "邮箱或密码错误")
    if not user.get("verified"):
        raise HTTPException(403, "邮箱未验证，请先查收验证码并完成验证")
    token = create_jwt({"id": user["id"], "username": user["email"], "display_name": user["nickname"], "role": user["role"]})
    return {"ok": True, "token": token, "user": {
        "id": user["id"], "email": user["email"],
        "nickname": user["nickname"], "role": user["role"],
    }}


def send_email_smtp(to: str, code: str) -> bool:
    """通过 SMTP 发送验证码邮件（自动重试 1 次，总超时 10s 防止卡死）"""
    import smtplib
    import time
    import ssl
    import os
    import threading
    from email.mime.text import MIMEText
    from .config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_USE_SSL
    # 直接读取环境变量，确保不被子进程丢失
    SMTP_PASSWORD = os.environ.get("SMTP_PASSWORD", "")
    if not SMTP_PASSWORD:
        # 尝试从 .env 文件手动加载
        _env_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "..", ".env")
        if os.path.isfile(_env_path):
            with open(_env_path) as _f:
                for _line in _f:
                    _line = _line.strip()
                    if _line.startswith("SMTP_PASSWORD="):
                        SMTP_PASSWORD = _line.split("=", 1)[1].strip()
                        break
    _result = False
    def _do_send():
        nonlocal _result
        for attempt in range(2):
            try:
                msg = MIMEText(f"您的验证码是: {code}\n有效期 10 分钟", "plain", "utf-8")
                msg["Subject"] = f"BBS 验证码: {code}"
                msg["From"] = SMTP_USER
                msg["To"] = to
                ctx = ssl.create_default_context()
                if SMTP_USE_SSL:
                    with smtplib.SMTP_SSL(SMTP_HOST, SMTP_PORT, timeout=8, context=ctx) as s:
                        s.login(SMTP_USER, SMTP_PASSWORD)
                        s.send_message(msg)
                else:
                    with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=8) as s:
                        s.ehlo()
                        s.starttls(context=ctx)
                        s.ehlo()
                        s.login(SMTP_USER, SMTP_PASSWORD)
                        s.send_message(msg)
                _result = True
                return
            except Exception as e:
                print(f"[SMTP ERROR] attempt {attempt+1}/2: {e}")
                import traceback
                traceback.print_exc()
                if attempt == 0:
                    time.sleep(1)
    _t = threading.Thread(target=_do_send, daemon=True)
    _t.start()
    _t.join(timeout=10)
    return _result


_last_send_time: dict[str, int] = {}  # email -> timestamp, 频率控制


def send_verify_code(email: str) -> dict:
    """生成 6 位验证码，存入 users 表，通过 SMTP 发送（含 60s 频率限制）"""
    import random
    import string
    import time

    # 频率限制：60 秒内不能重复发送
    last = _last_send_time.get(email, 0)
    cooldown = 60
    elapsed = int(time.time()) - last
    if elapsed < cooldown:
        raise HTTPException(429, f"发送过于频繁，请 {cooldown - elapsed} 秒后再试")

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
    # 通过 SMTP 真实发送验证码邮件
    ok = send_email_smtp(email, code)
    # 更新频率控制时间戳（成功/失败都更新，防止恶意刷接口）
    _last_send_time[email] = int(time.time())
    if ok:
        return {"ok": True, "msg": "验证码已发送", "debug_code": code, "debug_token": token}
    else:
        # 发送失败时降级：仍然保留 debug 信息供手动排查
        print(f"[SMTP FAILED] To: {email}  Code: {code}  Token: {token[:16]}...")
        return {"ok": True, "msg": "验证码已发送（SMTP 发送失败，可看 debug_code 手动验证）", "debug_code": code, "debug_token": token}


def check_verify(email: str, code: str, token: str) -> dict:
    """校验验证码，通过后将 verified 标记为 1"""
    db = get_db()
    cur = db.cursor(DictCursor)
    cur.execute(
        "SELECT verify_code, verify_token, verify_expire, status FROM users WHERE email=%s",
        (email,),
    )
    user = cur.fetchone()
    if not user:
        db.close()
        raise HTTPException(404, "邮箱未注册")
    if user.get("status") is not None and user["status"] != 1:
        db.close()
        raise HTTPException(403, "账号已被禁用")
    if int(time.time()) > user["verify_expire"]:
        db.close()
        raise HTTPException(400, "验证码已过期")
    if user["verify_code"] != code or user["verify_token"] != token:
        db.close()
        raise HTTPException(400, "验证码或 token 无效")
    # 验证通过，标记邮箱已验证，清除验证码
    cur.execute(
        "UPDATE users SET verified=1, verify_code=NULL, verify_token=NULL, verify_expire=NULL WHERE email=%s",
        (email,),
    )
    db.commit()
    db.close()
    return {"ok": True, "msg": "验证通过"}
