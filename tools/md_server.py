#!/usr/bin/env python3
"""
Markdown 文件 Web 查看器

用法:
    python tools/md_server.py              # 默认 docs/ 目录, 端口 8899
    python tools/md_server.py --dir memory  # 指定目录
    python tools/md_server.py --port 8080   # 指定端口

启动后浏览器打开 http://localhost:8899
"""

import os, sys, json, argparse
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse, quote

try:
    from markdown_it import MarkdownIt
except ImportError:
    print("请安装 markdown-it-py: pip install markdown-it-py")
    sys.exit(1)

PROJECT_ROOT = Path(__file__).resolve().parent.parent

MD = MarkdownIt('js-default', {'linkify': True, 'html': True})

HTML_TPL = """<!DOCTYPE html>
<html lang="zh-CN">
<head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{title}</title>
<style>
* {{margin:0;padding:0;box-sizing:border-box;}}
body {{font:15px/1.7 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,sans-serif;color:#2c3e50;background:#fafafa;}}
nav {{width:240px;min-width:100px;background:#1a1a2e;color:#eee;padding:15px;overflow-y:auto;flex-shrink:0;box-sizing:border-box;}}
nav .parent-btn {{display:block;margin-bottom:12px;border-bottom:1px solid #333;padding:0 0 10px 0;color:#e94560;font-weight:bold;font-size:14px;text-decoration:none;}}
nav .parent-btn:hover {{color:#ff6b6b;}}
nav h3 {{font-size:14px;color:#e94560;margin:20px 0 8px 0;text-transform:uppercase;letter-spacing:1px;}}
nav a {{display:block;color:#ccc;text-decoration:none;padding:3px 8px;border-radius:4px;font-size:13px;margin:1px 0;}}
nav a:hover,nav a.active {{background:#e94560;color:#fff;}}
nav a.active {{font-weight:bold;}}
#container {{display:flex;width:100%;min-height:100vh;}}
#divider {{width:6px;cursor:col-resize;background:#2a2a4e;flex-shrink:0;user-select:none;}}
#divider:hover {{background:#e94560;}}
main {{flex:1;min-width:0;padding:30px 40px;max-width:900px;overflow-y:auto;}}
main h1 {{color:#1a1a2e;border-bottom:3px solid #e94560;padding-bottom:10px;margin:0 0 25px 0;}}
main h2 {{color:#1a1a2e;border-bottom:1px solid #eee;padding-bottom:8px;margin:30px 0 15px 0;}}
main h3 {{color:#1a1a2e;margin:25px 0 10px 0;}}
main p {{margin:10px 0;}}
main code {{background:#f0f0f0;padding:2px 7px;border-radius:4px;font-size:13px;color:#e94560;}}
main pre {{background:#1a1a2e;color:#e8e8e8;padding:18px;border-radius:8px;overflow-x:auto;font:13px/1.6 "SF Mono","Fira Code",Consolas,monospace;}}
main pre code {{background:transparent;color:#e8e8e8;padding:0;}}
main table {{border-collapse:collapse;width:100%;margin:15px 0;}}
main th,main td {{border:1px solid #ddd;padding:8px 12px;text-align:left;}}
main th {{background:#1a1a2e;color:#fff;}}
main tr:nth-child(even) {{background:#f5f5f5;}}
main blockquote {{border-left:4px solid #e94560;margin:15px 0;padding:10px 20px;background:#f5f5f5;border-radius:0 4px 4px 0;}}
main img {{max-width:100%;border-radius:6px;margin:10px 0;}}
main ul,main ol {{margin:10px 0;padding-left:25px;}}
main li {{margin:4px 0;}}
main hr {{border:none;border-top:1px solid #ddd;margin:30px 0;}}
.dir-list {{list-style:none;padding:0;}}
.dir-list li {{padding:8px 0;border-bottom:1px solid #eee;}}
.dir-list a {{color:#1a1a2e;text-decoration:none;font-size:16px;}}
.dir-list a:hover {{color:#e94560;}}
.dir-list .size {{color:#999;font-size:13px;margin-left:10px;}}
#toast {{position:fixed;bottom:30px;right:30px;background:#1a1a2e;color:#e94560;padding:10px 20px;border-radius:6px;font-size:13px;opacity:0;transition:opacity .3s;z-index:9999;}}
#toast.show {{opacity:1;}}
</style></head><body>
<div id="container">
<nav id="sidebar">
<h3>📂 {dir_name}</h3>
{nav_links}
</nav>
<div id="divider"></div>
<main>
{content}
</main>
</div>
<div id="toast"></div>
<script>
var sidebar = document.getElementById('sidebar');
var divider = document.getElementById('divider');
var isDragging = false;

// 恢复上次保存的宽度
var saved = localStorage.getItem('md_sidebar_w');
if (saved) sidebar.style.width = saved + 'px';

divider.addEventListener('mousedown', function(e) {{
    isDragging = true; e.preventDefault();
}});
document.addEventListener('mousemove', function(e) {{
    if (!isDragging) return;
    var w = Math.max(100, Math.min(600, e.clientX - sidebar.getBoundingClientRect().left));
    sidebar.style.width = w + 'px';
}});
document.addEventListener('mouseup', function() {{
    if (isDragging) {{
        isDragging = false;
        localStorage.setItem('md_sidebar_w', parseInt(sidebar.style.width));
    }}
}});
document.querySelectorAll('nav a').forEach(function(a) {{
    if(a.href === location.href || a.href === location.href.split('?')[0]) a.classList.add('active');
}});
</script>
</body></html>"""


class MDHandler(BaseHTTPRequestHandler):
    root_dir = None          # 启动时指定的根目录
    project_root = None      # 项目根目录（限制不能跳出）

    def _parse_query(self):
        """解析查询参数，返回 dir 参数值（相对于启动根目录）"""
        qs = urlparse(self.path).query
        params = {}
        for part in qs.split("&"):
            if "=" in part:
                k, v = part.split("=", 1)
                params[k] = v
        return params

    def _current_root(self):
        """根据 ?dir= 查询参数获取当前根目录，保证不超出 project_root"""
        params = self._parse_query()
        raw_dir = params.get("dir", "")
        if not raw_dir:
            return self.root_dir
        # 解析相对路径，限制不能超出 project_root
        resolved = (self.root_dir / raw_dir).resolve()
        pr = self.project_root.resolve()
        if not str(resolved).startswith(str(pr)):
            return pr  # 超出项目根则卡在 project_root
        if resolved.is_dir():
            return resolved
        return resolved.parent

    def _url_for(self, path_str, new_dir=None):
        """生成带 dir 参数的 URL"""
        params = self._parse_query()
        cur_dir = params.get("dir", "")
        if new_dir is not None:
            cur_dir = new_dir
        base = f"/{path_str}" if path_str else "/"
        if cur_dir:
            base += f"?dir={cur_dir}" if "?" not in base else f"&dir={cur_dir}"
        return base

    def log_message(self, fmt, *args):
        """静默日志，只输出访问路径"""
        print(f"[MD] {args[0]}", file=sys.stderr)

    def _send(self, data, mime="text/html;charset=utf-8"):
        self.send_response(200)
        self.send_header("Content-Type", mime)
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(data)

    def _send_404(self, msg="Not Found"):
        self.send_response(404)
        self.send_header("Content-Type", "text/plain;charset=utf-8")
        self.end_headers()
        self.wfile.write(msg.encode())

    def _read_file(self, rel_path):
        cr = self._current_root()
        full = cr / rel_path
        if full.exists() and full.is_file():
            try:
                return full.read_bytes()
            except Exception:
                return None
        # 回退：在子目录中递归搜索（应对不带 ?dir= 参数直接访问子目录内的文件）
        try:
            for child in cr.rglob(rel_path):
                if child.is_file():
                    return child.read_bytes()
        except Exception:
            pass
        return None

    def _build_nav(self, active_file=None):
        """生成左侧导航HTML：子目录 + 当前目录下的 .md 文件"""
        cr = self._current_root()
        pr = self.project_root.resolve()
        root_str = str(self.root_dir.resolve())
        parts = []

        def _rel_path(target):
            """计算 target 相对于 root_dir 的路径（支持 ../ 上溯）"""
            return os.path.relpath(str(target), root_str).replace('\\', '/')

        # --- 上一级按钮 ---
        is_top = (cr.resolve() == pr)
        if not is_top:
            parent_dir = cr.parent
            dir_param = _rel_path(parent_dir)
            parts.append(
                f'<div style="margin-bottom:12px;border-bottom:1px solid #333;padding-bottom:8px;">'
                f'<a href="{self._url_for("", new_dir=dir_param)}" '
                f'style="color:#e94560;font-weight:bold;font-size:14px;">'
                f'&#x2191; 上一级: {parent_dir.name}/</a></div>'
            )

        # --- 子目录（可点击进入） ---
        subdirs = sorted([
            d for d in cr.iterdir()
            if d.is_dir() and not d.name.startswith('.')
        ])
        if subdirs:
            parts.append('<h3>目录</h3>')
            for d in subdirs:
                dir_param = _rel_path(d)
                url = self._url_for("", new_dir=dir_param)
                parts.append(f'<a href="{url}">📁 {d.name}/</a>')

        # --- 当前目录下的 .md 文件 ---
        md_files = sorted([
            f for f in cr.iterdir()
            if f.is_file() and f.suffix.lower() == '.md'
        ])
        if md_files:
            parts.append('<h3>文件</h3>')
            for f in md_files:
                url = self._url_for(f.name)
                cls = ' class="active"' if f.name == active_file else ""
                parts.append(f'<a{cls} href="{url}">{f.name}</a>')

        return "\n".join(parts)

    def _render_md(self, rel_path):
        """渲染Markdown文件"""
        raw = self._read_file(rel_path)
        if raw is None:
            return self._send_404("File not found")

        text = raw.decode("utf-8", errors="replace")
        body = MD.render(text)
        nav = self._build_nav(active_file=rel_path)

        cr = self._current_root()

        html = HTML_TPL.format(
            title=f"{rel_path} — MD Viewer",
            dir_name=cr.name,
            nav_links=nav,
            content=body,
        )
        self._send(html.encode())

    def _serve_file(self, rel_path):
        """服务非md文件（如图片等）"""
        raw = self._read_file(rel_path)
        if raw is None:
            # 当前目录找不到时，回退到项目根目录
            # 修复：markdown 中相对路径（如 assets/images/GGA.png）
            # 是相对 md 文件位置而非 root_dir, 浏览器请求时不带 ?dir= 参数
            alt_path = self.project_root / rel_path
            if alt_path.exists() and alt_path.is_file():
                raw = alt_path.read_bytes()
        if raw is None:
            return self._send_404("File not found")

        ext = Path(rel_path).suffix.lower()
        mime_map = {
            ".png": "image/png",
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".gif": "image/gif",
            ".svg": "image/svg+xml",
            ".webp": "image/webp",
            ".ico": "image/x-icon",
            ".css": "text/css;charset=utf-8",
            ".js": "application/javascript;charset=utf-8",
            ".json": "application/json;charset=utf-8",
        }
        mime = mime_map.get(ext, "application/octet-stream")
        self._send(raw, mime=mime)

    def do_GET(self):
        path = urlparse(self.path).path.strip("/")
        # URL decode 处理 %20 等编码（应对文件名含空格等情况）
        from urllib.parse import unquote
        path = unquote(path)

        if not path:
            # 未选择md文件时，只显示侧边栏，内容区留空
            nav = self._build_nav()
            cr = self._current_root()
            display_name = cr.name
            html = HTML_TPL.format(
                title=f"{display_name}/ — MD Viewer",
                dir_name=display_name,
                nav_links=nav,
                content="",
            )
            self._send(html.encode())
            return

        # 尝试作为md文件
        if Path(path).suffix == ".md":
            return self._render_md(path)

        # 尝试查找匹配的md文件（支持无后缀，用当前目录而非启动目录）
        cr = self._current_root()
        md_candidate = cr / f"{path}.md"
        if md_candidate.exists():
            return self._render_md(f"{path}.md")

        # 静态文件
        self._serve_file(path)


def main():
    parser = argparse.ArgumentParser(description="Markdown Web Viewer")
    parser.add_argument("--dir", "-d", default="docs",
                        help="要浏览的目录 (默认: docs)")
    parser.add_argument("--port", "-p", type=int, default=8899,
                        help="端口号 (默认: 8899)")
    parser.add_argument("--host", default="127.0.0.1",
                        help="监听地址 (默认: 127.0.0.1)")
    args = parser.parse_args()

    target_dir = (PROJECT_ROOT / args.dir).resolve()
    if not target_dir.exists():
        print(f"[ERROR] 目录不存在: {target_dir}")
        sys.exit(1)
    if not target_dir.is_dir():
        print(f"[ERROR] 路径不是目录: {target_dir}")
        sys.exit(1)

    MDHandler.root_dir = target_dir
    MDHandler.project_root = PROJECT_ROOT

    server = HTTPServer((args.host, args.port), MDHandler)
    print(f"\n  {'='*50}")
    print(f"   MD Viewer 已启动")
    print(f"   目录: {target_dir}")
    print(f"   地址: http://{args.host}:{args.port}")
    print(f"   退出: Ctrl+C")
    print(f"  {'='*50}\n")

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n  已停止.")
        server.server_close()


if __name__ == "__main__":
    main()
