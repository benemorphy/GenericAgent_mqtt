"""Agent 列表路由 — 从 MariaDB agent_sessions 读取"""

from pathlib import Path

from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse

from frontends.auth import require_user
from frontends.bbs_browser.database import get_db
from frontends.web_ui import render_template

router = APIRouter(dependencies=[Depends(require_user)])


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
    return render_template("agents/index.html", nav_active="agents", user=user, agents=agents)


@router.get("/agents/{agent_id}", response_class=HTMLResponse)
def agent_detail(request: Request, agent_id: str, user: dict = Depends(require_user)):
    """单个 Agent 详情"""
    agent = get_agent_detail(agent_id)
    if not agent:
        return render_template("error.html", nav_active="agents", user=user, error="Agent 不存在")
    return render_template("agents/detail.html", nav_active="agents", user=user, agent=agent)
