"""板块浏览路由 — 复用 bbs_browser/database.py"""

import os
import sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from frontends.bbs_browser.auth import require_user
from frontends.bbs_browser.database import get_boards, get_board, query_posts, query_all_posts as search_all
from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Environment(loader=FileSystemLoader(
    Path(__file__).resolve().parent.parent / "templates"
))

router = APIRouter(dependencies=[Depends(require_user)])


def _render(name: str, **ctx) -> str:
    """渲染模板，注入用户上下文"""
    user = ctx.pop('user', None)
    return _TEMPLATES.get_template(name).render(user=user, nav_active='boards', **ctx)


def _make_diag_board():
    """动态创建诊断板块字典（如果数据库中没有）"""
    return {"id": "agent-diagnosis", "name": "诊断板", "icon": "\U0001f52c",
            "description": "系统健康检查与本体模型偏差报告",
            "source_table": "bbs_posts", "source_filter": "board='agent-diagnosis'",
            "sort_field": "created_at", "sort_dir": "DESC",
            "post_count": 0, "order": 99}


@router.get("/boards", response_class=HTMLResponse)
def boards_index(request: Request, user: dict = Depends(require_user)):
    """板块广场"""
    boards = get_boards()
    return _render("boards/index.html", user=user, boards=boards)


@router.get("/boards/search", response_class=HTMLResponse)
def boards_search(request: Request, q: str = Query(""), user: dict = Depends(require_user)):
    """跨板块搜索"""
    results = []
    if q:
        results = search_all(q, limit=50)
    return _render("boards/index.html", user=user, boards=get_boards(), search_q=q, search_results=results)


@router.get("/boards/diagnosis", response_class=HTMLResponse)
def boards_diagnosis(request: Request, user: dict = Depends(require_user)):
    """系统诊断页面"""
    board = get_board("agent-diagnosis") or _make_diag_board()
    posts, total = query_posts(board, page=1, limit=50)
    return _render("boards/diagnosis.html", user=user, posts=posts, total=total)


@router.post("/boards/diagnosis/run", response_class=HTMLResponse)
def boards_diagnosis_run(request: Request, user: dict = Depends(require_user)):
    """触发系统诊断（带PID锁，防止重复启动）"""
    import subprocess
    root = str(Path(__file__).resolve().parent.parent.parent.parent)
    pid_path = os.path.join(root, "run", "diagnosis_agent.pid")
    scripts = os.path.join(root, "tools", "diagnosis_agent.py")
    if not os.path.isfile(scripts):
        return _render("error.html", user=user, error="诊断脚本不存在")
    
    # PID lock check
    if os.path.isfile(pid_path):
        try:
            with open(pid_path) as f:
                pid = int(f.read().strip())
            os.kill(pid, 0)  # signal 0 = check existence only
            board = get_board("agent-diagnosis") or _make_diag_board()
            posts, total = query_posts(board, page=1, limit=50)
            return _render("boards/diagnosis.html", user=user, posts=posts, total=total,
                           message=f"诊断代理已在运行 (PID {pid})")
        except (OSError, ValueError):
            pass  # stale pid file, ignore
    
    try:
        env = os.environ.copy()
        proc = subprocess.Popen([sys.executable, scripts], cwd=root, env=env,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        # Write PID file
        os.makedirs(os.path.dirname(pid_path), exist_ok=True)
        with open(pid_path, "w") as f:
            f.write(str(proc.pid))
        board = get_board("agent-diagnosis") or _make_diag_board()
        posts, total = query_posts(board, page=1, limit=50)
        return _render("boards/diagnosis.html", user=user, posts=posts, total=total,
                       message=f"诊断已触发 (PID {proc.pid})，请刷新查看结果")
    except Exception as e:
        return _render("error.html", user=user, error=f"诊断触发失败: {e}")


@router.get("/boards/{board_id}", response_class=HTMLResponse)
def board_posts(request: Request, board_id: str, page: int = Query(1, ge=1),
               q: str = Query(""), user: dict = Depends(require_user)):
    """板块帖子列表"""
    board = get_board(board_id)
    if not board:
        return _render("error.html", user=user, error="板块不存在")
    posts, total = query_posts(board, page=page, q=q)
    limit = 50
    total_pages = max(1, (total + limit - 1) // limit)
    return _render("boards/board.html", user=user, board=board, posts=posts,
                   total=total, page=page, total_pages=total_pages, q=q)
