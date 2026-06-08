"""
FastAPI Web UI — 入口

聚合 Board Browser / Dashboard / Agents 到一个服务。
共享 JWT 认证，路由区分，单端口 8000 部署。
"""

from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse

from frontends.web_ui.config import HOST, PORT
from frontends.auth import optional_user

app = FastAPI(title="GenericAgent Web UI", docs_url="/api/docs")

# ── 路由注册 ──
from frontends.web_ui.routers import auth, boards, agents, dashboard
from frontends.playground.router import router as play_router

app.include_router(auth.router)         # /login, /register, /api/login, /api/register
app.include_router(boards.router)       # /boards, /boards/{id}
app.include_router(agents.router)       # /agents, /agents/{id}
app.include_router(dashboard.router)    # /dashboard, /api/dashboard/*
app.include_router(play_router)         # /play/*


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
    print(f"  Web UI (internal): http://localhost:{PORT}/")
    print(f"  Boards:  http://localhost:{PORT}/boards")
    print(f"  Agents:  http://localhost:{PORT}/agents")
    uvicorn.run("frontends.web_ui.main:app", host="127.0.0.1", port=8001, reload=False)
