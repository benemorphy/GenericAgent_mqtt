"""BBS Board Browser — FastAPI 主应用"""

import os, sys
from pathlib import Path

# ── 确保能找到 mqtt_bbs 包 ──
_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, Request, Form, Query, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.trustedhost import TrustedHostMiddleware

from .config import HOST, PORT, JWT_SECRET
from .database import init_db, seed_boards, get_boards, get_board, query_posts, query_all_posts
from .auth import require_user, optional_user, register_user, login_user

# ── 初始化 ──
app = FastAPI(title="BBS Board Browser")
templates = Jinja2Templates(directory=Path(__file__).parent / "templates")

# 可选: 静态文件目录
static_dir = Path(__file__).parent / "static"
static_dir.mkdir(exist_ok=True)
app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")


# ── 启动事件 ──
@app.on_event("startup")
def startup():
    init_db()
    seed_boards()
    print(f"  [BBS Browser] 启动于 http://{HOST}:{PORT}")


# ══════════════════════════════════════
# 公开路由（无需登录）
# ══════════════════════════════════════

@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request, error: str = ""):
    """登录页"""
    user = optional_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("login.html", {"request": request, "error": error})


@app.get("/register", response_class=HTMLResponse)
def register_page(request: Request, error: str = ""):
    """注册页"""
    user = optional_user(request)
    if user:
        return RedirectResponse(url="/", status_code=302)
    return templates.TemplateResponse("register.html", {"request": request, "error": error})


@app.post("/api/register")
def api_register(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    display_name: str = Form(""),
):
    """注册 API"""
    result = register_user(username, password, display_name)
    if "error" in result:
        return RedirectResponse(url=f"/register?error={result['error']}", status_code=302)
    return RedirectResponse(url="/login?registered=1", status_code=302)


@app.post("/api/login")
def api_login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
):
    """登录 API"""
    result = login_user(username, password)
    if "error" in result:
        return RedirectResponse(url=f"/login?error={result['error']}", status_code=302)
    response = RedirectResponse(url="/", status_code=302)
    response.set_cookie(key="token", value=result["token"], httponly=True, max_age=86400 * 7)
    return response


@app.get("/api/logout")
def api_logout():
    """退出登录"""
    response = RedirectResponse(url="/login", status_code=302)
    response.delete_cookie("token")
    return response


# ══════════════════════════════════════
# 受保护路由（需登录）
# ══════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
def index(request: Request, user: dict = Depends(require_user)):
    """首页 — 板块广场"""
    boards = get_boards()
    return templates.TemplateResponse("index.html", {
        "request": request, "user": user, "boards": boards,
    })


@app.get("/board/{board_id}", response_class=HTMLResponse)
def board_view(
    request: Request,
    board_id: str,
    page: int = Query(1, ge=1),
    q: str = Query(""),
    user: dict = Depends(require_user),
):
    """板块页 — 帖子列表 + 搜索"""
    board = get_board(board_id)
    if not board:
        return HTMLResponse("板块不存在", status_code=404)
    
    limit = 50
    posts, total = query_posts(board, page=page, q=q, limit=limit)
    total_pages = max(1, (total + limit - 1) // limit)
    
    return templates.TemplateResponse("board.html", {
        "request": request, "user": user, "board": board,
        "posts": posts, "page": page, "total_pages": total_pages,
        "total": total, "q": q,
    })


@app.get("/search", response_class=HTMLResponse)
def search_all(
    request: Request,
    q: str = Query(""),
    user: dict = Depends(require_user),
):
    """跨板块搜索页"""
    results = []
    if q:
        results = query_all_posts(q, limit=50)
    return templates.TemplateResponse("search.html", {
        "request": request, "user": user, "q": q, "results": results,
    })


# ══════════════════════════════════════
# JSON API（前端 AJAX 用）
# ══════════════════════════════════════

@app.get("/api/boards")
def api_boards(user: dict = Depends(require_user)):
    return get_boards()


@app.get("/api/boards/{board_id}/posts")
def api_board_posts(
    board_id: str,
    page: int = 1,
    q: str = "",
    user: dict = Depends(require_user),
):
    board = get_board(board_id)
    if not board:
        return {"error": "not found"}
    posts, total = query_posts(board, page=page, q=q)
    return {"board": board, "posts": posts, "total": total, "page": page}


# ══════════════════════════════════════
# 入口
# ══════════════════════════════════════

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("frontends.bbs_browser.app:app", host=HOST, port=PORT, reload=True)
