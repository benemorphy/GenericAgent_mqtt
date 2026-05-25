"""Playground 路由 - 游戏化沙盒界面"""
import os, sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from frontends.bbs_browser.auth import require_user
from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Environment(loader=FileSystemLoader(
    Path(__file__).resolve().parent / "templates"
))

router = APIRouter(dependencies=[Depends(require_user)])


def _render(name: str, **ctx) -> str:
    user = ctx.pop('user', None)
    return _TEMPLATES.get_template(name).render(user=user, nav_active='play', **ctx)


@router.get("/play", response_class=HTMLResponse)
def play_index(request: Request, user: dict = Depends(require_user)):
    """Playground 首页"""
    from frontends.playground.room import ROOMS
    return _render("playground/index.html", user=user, rooms=ROOMS)
