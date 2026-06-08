"""Playground 路由 - 游戏化沙盒界面"""

from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from frontends.auth import require_user
from frontends.playground import templates as _T

router = APIRouter(dependencies=[Depends(require_user)])


def _render(name: str, **ctx) -> str:
    user = ctx.pop('user', None)
    return _T.get_template(name).render(user=user, nav_active='play', **ctx)


@router.get("/play", response_class=HTMLResponse)
def play_index(request: Request, user: dict = Depends(require_user)):
    """Playground 首页"""
    from frontends.playground.room import ROOMS
    return _render("playground/index.html", user=user, rooms=ROOMS)
