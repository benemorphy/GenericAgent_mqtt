"""网关认证路由 — 登录/注册页面 + API + JWT 验证"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request, Form, HTTPException
from fastapi.responses import RedirectResponse, HTMLResponse, JSONResponse

from frontends.bbs_browser.auth import (
    optional_user, register_user, login_user,
    register_user_email, login_user_email,
    send_verify_code, check_verify,
)

from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Environment(loader=FileSystemLoader(
    Path(__file__).resolve().parent.parent / "templates"
))

router = APIRouter()


def _render(name: str, **ctx) -> str:
    """渲染模板，自动注入基础上下文"""
    return _TEMPLATES.get_template(name).render(**ctx)


@router.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = "", need_verify: str = "", email: str = "", verify_token: str = ""):
    """登录页"""
    user = optional_user(request)
    if user:
        return RedirectResponse(url="/boards")
    return _render("login.html", error=error, need_verify=need_verify, email=email, verify_token=verify_token, user=None)


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
    """Email 注册 API → 自动发验证码，跳转登录页显示验证码区"""
    result = register_user_email(email, password, nickname)
    if "error" in result:
        return _render("register.html", error=result["error"], user=None)
    # 注册成功 → 自动发送验证码
    try:
        send_result = send_verify_code(email)
    except HTTPException as e:
        # HTTPException 有明确状态码（如 429 频率限制），传递给用户
        return _render("register.html", error=e.detail, user=None)
    except Exception as e:
        print(f"[auth] send_verify_code 失败: {e}", flush=True)
        return _render("register.html", error="验证码发送失败，请稍后重试", user=None)
    verify_token = send_result.get("debug_token", "") if isinstance(send_result, dict) else ""
    return RedirectResponse(
        url=f"/login?need_verify=邮箱未验证，请查收验证码&email={email}&verify_token={verify_token}",
        status_code=302,
    )


@router.post("/api/email/login")
def api_email_login(request: Request, email: str = Form(...), password: str = Form(...)):
    """Email 登录 API → 设置 JWT cookie（兼容现有前端）"""
    try:
        result = login_user_email(email, password)
    except HTTPException as e:
        # 403 邮箱未验证 → 返回 JSON 给 AJAX 前端
        if e.status_code == 403:
            # 从数据库读取 verify_token
            try:
                from frontends.bbs_browser.auth import get_db
                from pymysql.cursors import DictCursor
                db = get_db()
                cur = db.cursor(DictCursor)
                cur.execute("SELECT verify_token FROM users WHERE email=%s", (email,))
                row = cur.fetchone()
                db.close()
                verify_token = row["verify_token"] if row else ""
            except Exception:
                verify_token = ""
            return JSONResponse({"error": e.detail, "need_verify": True, "email": email, "verify_token": verify_token})
        return _render("login.html", error=e.detail, user=None)
    if "error" in result:
        return JSONResponse({"error": result["error"]})
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
    except Exception as e:
        import traceback
        traceback.print_exc()
        return JSONResponse({"error": f"验证失败: {str(e)}"}, status_code=400)
