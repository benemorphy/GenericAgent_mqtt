"""文档阅读路由 — 反向代理到 md_server_rs:8899
   自动重写 HTML 链接，使其在 /docs/ 命名空间下工作。"""

import sys
import re
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse, Response
import httpx

from frontends.bbs_browser.auth import require_user
from frontends.gateway.config import MD_SERVER_URL

router = APIRouter(dependencies=[Depends(require_user)])

# 需要重写的 HTML 属性中的路径
_REWRITE_PATTERN = re.compile(r'''\b(href|src|action)=["'](/(?:[^"']*))["']''')


def _rewrite_html(content: str) -> str:
    """将 HTML 中的绝对路径 /xxx 重写为 /docs/xxx"""
    def _replace(m):
        attr, path = m.group(1), m.group(2)
        # 跳过已经带 /docs/ 的路径
        if path.startswith('/docs/'): return m.group(0)
        # 跳过来自网关自己的路径（如 /login, /boards）
        if path in ('/login', '/register', '/boards', '/agents', '/dashboard',
                    '/api/login', '/api/register', '/api/logout'):
            return m.group(0)
        return f'{attr}="/docs{path}"'
    return _REWRITE_PATTERN.sub(_replace, content)


@router.get("/docs/{path:path}", response_class=HTMLResponse)
async def proxy_docs(path: str, request: Request):
    """反向代理到 md_server_rs, 重写 HTML 链接"""
    # 传递 query 参数（如 ?dir=architecture）
    query = request.url.query
    url = f"{MD_SERVER_URL}/{path}"
    if query:
        url += f"?{query}"
    async with httpx.AsyncClient(timeout=10) as client:
        try:
            resp = await client.get(url)
            # 404 时检查本地文件系统（ROADMAP.md 等文件在项目根）
            if resp.status_code == 404:
                local_path = _PROJECT_ROOT / path
                if local_path.is_file():
                    if local_path.suffix == '.md':
                        import markdown
                        md = local_path.read_text(encoding='utf-8')
                        body = markdown.markdown(md, extensions=['fenced_code', 'codehilite', 'tables'])
                        html = f'''<!DOCTYPE html><html><head>
<meta charset="utf-8"><title>{local_path.stem}</title>
<style>
body {{ font-family: -apple-system, 'Segoe UI', sans-serif; max-width: 900px; margin: 0 auto; padding: 20px; line-height: 1.6; background: #fafafa; }}
pre {{ background: #f0f0f0; padding: 12px; border-radius: 6px; overflow-x: auto; }}
code {{ background: #f0f0f0; padding: 2px 6px; border-radius: 3px; font-size: 0.9em; }}
table {{ border-collapse: collapse; width: 100%; }}
th, td {{ border: 1px solid #ddd; padding: 8px 12px; text-align: left; }}
th {{ background: #f0f0f0; }}
a {{ color: #e94560; }}
h1, h2, h3 {{ margin-top: 24px; }}
</style></head><body>{body}</body></html>'''
                        return HTMLResponse(content=html)
                    content = local_path.read_bytes()
                    return Response(content=content, media_type="application/octet-stream")
                return HTMLResponse("File not found", status_code=404)

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
                "<h2>文档服务器未启动</h2>"
                "<p>请启动 md_server_rs (port 8899)</p>"
                "<p><code>cd tools/md_server_rs && cargo run</code></p>",
                status_code=503,
            )
