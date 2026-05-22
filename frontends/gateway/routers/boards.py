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


@router.get("/boards/{board_id}", response_class=HTMLResponse)
def board_posts(
    request: Request,
    board_id: str,
    page: int = Query(1, ge=1),
    q: str = Query(""),
    user: dict = Depends(require_user),
):
    """板块帖子列表"""
    board = get_board(board_id)
    if not board:
        return _render("error.html", user=user, error="板块不存在")
    posts, total = query_posts(board, page=page, q=q)
    limit = 50
    total_pages = max(1, (total + limit - 1) // limit)
    return _render("boards/board.html", user=user, board=board, posts=posts,
                   total=total, page=page, total_pages=total_pages, q=q)
