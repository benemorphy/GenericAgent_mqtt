"""
Playground 路由 — /play 入口，包含房间导航和 MQTT Console
"""

import os, sys, json, time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request, Query, Depends
from fastapi.responses import HTMLResponse
from frontends.bbs
...[Truncated]...
POST /play/api/post  → 发布消息
GET  /play/api/rooms → 房间列表
"""
router = APIRouter(dependencies=[Depends(require_user)])

@router.get("/play", response_class=HTMLResponse)
def play_index(request: Request, user: dict = Depends(require_user)):
    """Playground 首页：地图/房间列表"""
    from frontends.playground.room import ROOMS
    return _render("playground/index.html", user=user, rooms=ROOMS)

@router.get("/play/room/{room_id}", response_class=HTMLResponse)
def play_room(request: Request, room_id: str, user: dict = Depends(require_user)):
    """进入房间"""
    from frontends.playground.room import ROOMS
    room = next((r for r in ROOMS if r["id"] == room_id), None)
    if not room:
        return _render("playground/index.html", user=user, rooms=ROOMS, error="房间不存在")
    return _render("playground/room.html", user=user, room=room)
