"""
FastAPI 统一网关 — 入口

聚合 Board Browser / Dashboard / Agents / md_server_rs 到一个服务。
共享 JWT 认证，路由区分，单端口 8000 部署。
"""

import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from frontends.gateway.config import HOST, PORT
from frontends.bbs_browser.auth import optional_user

# ── Jinja2 模板引擎 ──
from jinja2 import Environment, FileSystemLoader
_TEMPLATES = Environment(loader=FileSystemLoader(
    Path(__file__).resolve().parent / "templates"
))

app = FastAPI(title="GenericAgent Gateway", docs_url="/api/docs")

# ── 静态文件 ──
static_dir = Path(__file__).resolve().parent / "static"
if static_dir.is_dir():
    app.mount("/static", StaticFiles(directory=str(static_dir)), name="static")

# ── 路由注册 ──
from frontends.gateway.routers import auth, boards, agents, dashboard, docs_proxy, mindflow
from frontends.playground.router import router as play_router

app.include_router(auth.router)         # /login, /register, /api/login, /api/register
app.include_router(boards.router)       # /boards, /boards/{id}
app.include_router(agents.router)       # /agents, /agents/{id}
app.include_router(dashboard.router)    # /dashboard, /api/dashboard/*
app.include_router(docs_proxy.router)   # /docs/{path:path}
app.include_router(play_router)         # /play/*
app.include_router(mindflow.router)     # /coursewares/*


# ── 根路径 ──
@app.get("/")
def root(request: Request):
    user = optional_user(request)
    if user:
        return RedirectResponse(url="/boards")
    return RedirectResponse(url="/login")


# ── 入口 ──
if __name__ == "__main__":
    import uvicorn
    print(f"  Gateway: http://localhost:{PORT}/")
    print(f"  Boards:  http://localhost:{PORT}/boards")
    print(f"  Agents:  http://localhost:{PORT}/agents")
    print(f"  Docs:    http://localhost:{PORT}/docs/")
    uvicorn.run("frontends.gateway.main:app", host=HOST, port=PORT, reload=False)
