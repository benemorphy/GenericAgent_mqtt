"""frontends/auth.py — 共享认证模块

提供 FastAPI 依赖注入函数，供 web_ui 和 playground 使用。
不依赖 bbs_browser 内部的 database 模块，保持层级清晰。
"""

import time
import hashlib
import hmac
import json
import base64
from fastapi import Request, HTTPException
from frontends.bbs_browser.config import JWT_SECRET, JWT_EXPIRY_SECONDS


def decode_jwt(token: str) -> dict:
    """解码验证 JWT"""
    try:
        parts = token.split(".")
        if len(parts) != 3:
            raise ValueError("invalid token")
        header, body, sig = parts
        expected_sig = base64.urlsafe_b64encode(
            hmac.new(JWT_SECRET.encode(), f"{header}.{body}".encode(), hashlib.sha256).digest()
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
    """FastAPI 依赖注入 — 从 cookie 解析用户（强制登录）"""
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
