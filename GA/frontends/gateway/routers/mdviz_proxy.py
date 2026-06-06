"""mdviz 反向代理路由 — 将 /mdviz/ 代理到 mvivz:20000
   自动重写 HTML 链接，使其在 /mdviz/ 命名空间下工作。"""

import sys
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse, Response
import httpx

from frontends.bbs_browser.auth import require_user
from fastapi import Depends
from frontends.gateway.config import MDVIZ_SERVER_URL

router = APIRouter(dependencies=[Depends(require_user)])

# 需要重写的 HTML 属性中的路径 — 把 /xxx 重写为 /mdviz/xxx
_REWRITE_PATTERN = re.compile(r'''\b(href|src|action)=["'](/(?:[^"']*))["']''')


def _rewrite_html(content: str) -> str:
    """将 HTML 中的绝对路径 /xxx 重写为 /mdviz/xxx"""
    def _replace(m):
        attr, path = m.group(1), m.group(2)
        # 跳过已经带 /mdviz/ 的路径
        if path.startswith('/mdviz/'):
            return m.group(0)
        # 跳过来自网关自己的路径（如 /login, /boards）
        if path in ('/login', '/register', '/boards', '/agents', '/dashboard',
                    '/api/login', '/api/register', '/api/logout'):
            return m.group(0)
        return f'{attr}="/mdviz{path}"'
    return _REWRITE_PATTERN.sub(_replace, content)


@router.get("/mdviz/{path:path}", response_class=HTMLResponse)
async def proxy_mdviz(path: str, request: Request):
    """反向代理到 mvivz, 重写 HTML 链接"""
    query = request.url.query
    url = f"{MDVIZ_SERVER_URL}/{path}"
    if query:
        url += f"?{query}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            content_type = resp.headers.get("content-type", "text/html")
            content = resp.content

            # HTML 响应需要重写链接
            if 'text/html' in content_type:
                text = content.decode('utf-8', errors='replace')
                text = _rewrite_html(text)
                content = text.encode('utf-8')

            return Response(content=content, status_code=resp.status_code,
                          media_type=content_type)
        except httpx.ConnectError:
            return HTMLResponse(
                "<h2>mdviz 服务未启动</h2>"
                "<p>请启动 mvivz (port 20000)</p>"
                "<p><code>cd tools/mdviz && cargo run</code></p>",
                status_code=503,
            )
