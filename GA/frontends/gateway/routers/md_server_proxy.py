"""md_server_rs 反向代理 — 将 /md_server/ 代理到 md_server_rs:20100
   自动重写 HTML 链接，使其在 /md_server/ 命名空间下工作。"""

import sys
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
import httpx

from frontends.gateway.config import MD_SERVER_URL

router = APIRouter()

# 匹配 HTML 中的 href/src/action="/xxx"（排除外部链接 /http, /https, /#）
_REWRITE_PATTERN = re.compile(r'''((?:href|src|action)\s*=\s*["'])/(?!/|http|https|#)([^"']*)''')


def _rewrite_html_links(content: str) -> str:
    """将 HTML 中的绝对路径 /xxx 改为 /md_server/xxx"""
    def _replace(m):
        attr = m.group(1)
        path = m.group(2) if m.lastindex == 2 else ""
        # 跳过来自网关自己的路径（这些应该由网关处理）
        skip_paths = ('login', 'register', 'boards', 'agents', 'dashboard',
                     'api/', 'static/', 'docs/', 'mdviz/', 'coursewares/')
        if any(path.startswith(p) for p in skip_paths):
            return m.group(0)
        return f'{attr}/md_server/{path}'
    return _REWRITE_PATTERN.sub(_replace, content)


@router.get("/md_server/{path:path}")
async def proxy_md_server(path: str, request: Request):
    """反向代理到 md_server_rs, 重写 HTML 链接"""
    query = request.url.query
    target = f"{MD_SERVER_URL}/{path}"
    if query:
        target += f"?{query}"

    async with httpx.AsyncClient() as client:
        try:
            resp = await client.get(target, timeout=10)
            content_type = resp.headers.get("content-type", "")

            if "text/html" in content_type:
                content = _rewrite_html_links(resp.text)
                return HTMLResponse(content=content, status_code=resp.status_code)
            return Response(content=resp.content, status_code=resp.status_code,
                          media_type=content_type)
        except httpx.ConnectError:
            return HTMLResponse(
                "<h2>md_server_rs 未启动</h2>"
                "<p>请启动 md_server_rs (port 20100)</p>"
                "<p><code>cd tools/md_server_rs && cargo run 20100 D:/</code></p>",
                status_code=503,
            )


@router.get("/md_server")
async def proxy_md_server_root(request: Request):
    return await proxy_md_server("", request)
