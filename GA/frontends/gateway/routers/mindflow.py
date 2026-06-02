"""MindFlow 反向代理 — 将 /coursewares/ 请求转发到 MindFlow 服务
   不需重写 HTML 链接，MindFlow 本身是 API + 单页预览。"""

from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
import sys
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request
from fastapi.responses import Response, HTMLResponse
import httpx

from frontends.gateway.config import MF_SERVER_URL

router = APIRouter()


@router.get("/coursewares/{path:path}")
async def proxy_mindflow(path: str, request: Request):
    """反向代理到 MindFlow (localhost:9900)"""
    query = request.url.query
    url = f"{MF_SERVER_URL}/{path}"
    if query:
        url += f"?{query}"

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.get(url)
            content_type = resp.headers.get("content-type", "text/html")
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=content_type,
            )
        except httpx.ConnectError:
            return HTMLResponse(
                "<h2>MindFlow 课件引擎未启动</h2>"
                "<p>请启动 MindFlow 服务 (port 9900)</p>"
                "<p><code>cd D:\\open_claw_agent\\MindFlow && "
                "uvicorn app.main:app --host 0.0.0.0 --port 9900</code></p>",
                status_code=503,
            )


@router.post("/coursewares/{path:path}")
async def proxy_mindflow_post(path: str, request: Request):
    """反向代理 POST 请求到 MindFlow API"""
    url = f"{MF_SERVER_URL}/{path}"
    body = await request.body()
    content_type = request.headers.get("content-type", "application/json")

    async with httpx.AsyncClient(timeout=180) as client:
        try:
            resp = await client.post(
                url, content=body,
                headers={"content-type": content_type}
            )
            return Response(
                content=resp.content,
                status_code=resp.status_code,
                media_type=resp.headers.get("content-type", "application/json"),
            )
        except httpx.ConnectError:
            return HTMLResponse("MindFlow 未启动", status_code=503)
