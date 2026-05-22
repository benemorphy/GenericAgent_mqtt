"""文档阅读路由 — 反向代理到 md_server_rs:8899"""

import os, sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse, Response
import httpx

from frontends.bbs_browser.auth import require_user
from frontends.gateway.config import MD_SERVER_URL

router = APIRouter(dependencies=[Depends(require_user)])


@router.get("/docs/{path:path}", response_class=HTMLResponse)
async def proxy_docs(path: str):
    """反向代理到 md_server_rs"""
    url = f"{MD_SERVER_URL}/{path}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            content_type = resp.headers.get("content-type", "text/html")
            return Response(content=resp.content, status_code=resp.status_code,
                          media_type=content_type)
        except httpx.ConnectError:
            return HTMLResponse(
                "<h2>文档服务器未启动</h2>"
                "<p>请启动 md_server_rs (port 8899)</p>"
                f"<p><code>cd tools/md_server_rs && cargo run</code></p>",
                status_code=503,
            )
