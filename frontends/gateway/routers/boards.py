"""板块浏览路由 — 复用 bbs_browser/database.py"""

import os, sys
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


@router.get("/boards", response_class=HTMLResponse)
def boards_index(request: Request, user: dict = Depends(require_user)):
    """板块广场"""
    boards = get_boards()
    return _render("boards/index.html", user=user, boards=boards)


@router.get("/boards/search", response_class=HTMLResponse)
def boards_search(
    request: Request,
    q: str = Query(""),
    user: dict = Depends(require_user),
):
    """跨板块搜索"""
    results = []
    if q:
        results = search_all(q, limit=50)
    return _render("boards/index.html", user=user, boards=get_boards(), search_q=q, search_results=results)


@router.get("/boards/diagnosis", response_class=HTMLResponse)
def boards_diagnosis(
    request: Request,
    user: dict = Depends(require_user),
):
    """系统诊断页面"""
    from frontends.bbs_browser.database import query_posts
    posts, total = query_posts("agent-diagnosis", page=1, limit=50)
    return _render("boards/diagnosis.html", user=user, posts=posts, total=total)


@router.post("/boards/diagnosis/run", response_class=HTMLResponse)
def boards_diagnosis_run(request: Request, user: dict = Depends(require_user)):
    """触发系统诊断"""
    import subprocess, sys, os
    root = str(Path(__file__).resolve().parent.parent.parent.parent)
    scripts = os.path.join(root, "tools", "diagnosis_agent.py")
    if not os.path.isfile(scripts):
        return _render("error.html", user=user, error="诊断脚本不存在")
    try:
        env = os.environ.copy()
        subprocess.Popen([sys.executable, scripts], cwd=root, env=env,
                        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        from frontends.bbs_browser.database import query_posts
        posts, total = query_posts("agent-diagnosis", page=1, limit=50)
        return _render("boards/diagnosis.html", user=user, posts=posts, total=total,
                       message="诊断已触发，请刷新查看结果")
    except Exception as e:
        return _render("error.html", user=user, error=f"诊断触发失败: {e}")


@router.get("/boards/{board_id}", response_class=HTMLResponse)
