"""Agent 列表路由 — 从 MariaDB agent_sessions 读取"""

import os, sys
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from frontends.bbs_browser.auth import require_user
from frontends.bbs_browser.database import get_db

from jinja2 import Environment, FileSystemLoader

_TEMPLATES = Environment(loader=FileSystemLoader(
    Path(__file__).resolve().parent.parent / "templates"
))

router = APIRouter(dependencies=[Depends(require_user)])


def _render(name: str, **ctx) -> str:
    user = ctx.pop('user', None)
    return _TEMPLATES.get_template(name).render(user=user, nav_active='agents', **ctx)


def get_agent_list() -> list:
    """从 agent_sessions 表获取 Agent 列表"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT agent_id, status,
               COALESCE(last_online, '') as last_online,
               COALESCE(last_offline, '') as last_offline,
               COALESCE(created_at, '') as created_at,
               COALESCE(updated_at, '') as updated_at
        FROM agent_sessions
        ORDER BY updated_at DESC
    """)
    agents = cur.fetchall()
    db.close()
    return agents


def get_agent_detail(agent_id: str) -> dict | None:
    """单个 Agent 详情"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT agent_id, status, last_online, last_offline, created_at, updated_at
        FROM agent_sessions WHERE agent_id=%s
    """, (agent_id,))
    agent = cur.fetchone()
    db.close()
    return agent


@router.get("/agents", response_class=HTMLResponse)
def agents_index(request: Request, user: dict = Depends(require_user)):
    """Agent 列表"""
    agents = get_agent_list()
    return _render("agents/index.html", user=user, agents=agents)


@router.get("/agents/{agent_id}", response_class=HTMLResponse)
def agent_detail(request: Request, agent_id: str, user: dict = Depends(require_user)):
    """单个 Agent 详情"""
    agent = get_agent_detail(agent_id)
    if not agent:
        return _render("error.html", user=user, error="Agent 不存在")
    return _render("agents/detail.html", user=user, agent=agent)
