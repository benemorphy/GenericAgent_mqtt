"""网关认证路由 — 登录/注册页面 + API + JWT 验证"""

import os, sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request, Form, Depends, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse

from frontends.bbs_browser.auth import (
    require_user, optional_user, create_jwt, register_user, login_user,
    register_user_email, login_user_email,
    send_verify_code, check_verify,
)
from frontends.bbs_browser.config import JWT_SECRET

from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Environment(loader=FileSystemLoader(
    Path(__file__).resolve().parent.parent / "templates"
))

router = APIRouter()


def _render(name: str, **ctx) -> str:
    """渲染模板，自动注入基础上下文"""
    return _TEMPLATES.get_template(name).render(**ctx)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    """登录页"""
    user = optional_user(request)
    if user:
        return RedirectResponse(url="/boards")
    return _render("login.html", error=error, user=None)


@router.get("/register", response_class=HTMLResponse)
def register_page(request: Request):
    """注册页"""
    user = optional_user(request)
    if user:
        return RedirectResponse(url="/boards")
    return _render("register.html", error="", user=None)


@router.post("/api/register")
def api_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
):
    """注册 API"""
    if not display_name:
        display_name = username
    result = register_user(username, password, display_name)
    if "error" in result:
        return _render("register.html", error=result["error"], user=None)
    return RedirectResponse(url="/login?registered=1", status_code=302)


@router.post("/api/login")
def api_login(request: Request, username: str = Form(...), password: str = Form(...)):
    """登录 API → 设置 JWT cookie"""
    result = login_user(username, password)
    if "error" in result:
        return _render("login.html", error=result["error"], user=None)
    resp = RedirectResponse(url="/boards", status_code=302)
    resp.set_cookie(
        key="token", value=result["token"],
        httponly=True, max_age=86400 * 7,
        samesite="lax",
    )
    return resp


@router.get("/api/logout")
def api_logout():
    """退出 → 清除 cookie"""
    resp = RedirectResponse(url="/login")
    resp.delete_cookie("token")
    return resp


# ═══════════════════════════════════════════
# Email 认证 V2 API（基于 users 表）
# ═══════════════════════════════════════════

@router.post("/api/email/register")
def api_email_register(
    request: Request,
    email: str = Form(...),
    password: str = Form(...),
    nickname: str = Form(""),
):
    """Email 注册 API"""
    result = register_user_email(email, password, nickname)
    if "error" in result:
        return _render("register.html", error=result["error"], user=None)
    return RedirectResponse(url="/login?registered=1", status_code=302)


@router.post("/api/email/login")
def api_email_login(request: Request, email: str = Form(...), password: str = Form(...)):
    """Email 登录 API → 设置 JWT cookie（兼容现有前端）"""
    try:
        result = login_user_email(email, password)
    except HTTPException as e:
        return _render("login.html", error=e.detail, user=None)
    if "error" in result:
        return _render("login.html", error=result["error"], user=None)
    resp = RedirectResponse(url="/boards", status_code=302)
    resp.set_cookie(
        key="token", value=result["token"],
        httponly=True, max_age=86400 * 7,
        samesite="lax",
    )
    return resp


@router.post("/api/email/send_code")
def api_send_code(email: str = Form(...)):
    """发送邮箱验证码（模拟）"""
    try:
        result = send_verify_code(email)
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)


@router.post("/api/email/verify")
def api_verify(email: str = Form(...), code: str = Form(...), token: str = Form(...)):
    """校验邮箱验证码"""
    try:
        result = check_verify(email, code, token)
        return JSONResponse(result)
    except HTTPException as e:
        return JSONResponse({"error": e.detail}, status_code=e.status_code)
