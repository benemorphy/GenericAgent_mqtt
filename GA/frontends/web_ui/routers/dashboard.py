"""Dashboard 仪表盘路由 — 实时 MQTT 监控（重写自 dashboard_mqtt.py Streamlit 版）"""

import json
import threading
from pathlib import Path

from fastapi import APIRouter, Request, WebSocket, WebSocketDisconnect, Depends
from fastapi.responses import HTMLResponse

from frontends.auth import require_user
from services.bbs_data.database import get_db
from frontends.web_ui import render_template

router = APIRouter(dependencies=[Depends(require_user)])

# ── 全局缓存（MQTT 订阅线程写入，HTTP 请求读取） ──
_cache = {
    "agents": {},       # agent_id -> {status, last_seen, capabilities}
    "tasks": {},        # task_id -> {type, status, input_preview, created_at}
    "recent_posts": [],  # [{board, author, content_preview, time}]
    "_lock": threading.Lock(),
}





def _get_overview() -> dict:
    """从缓存 + DB 获取总览数据"""
    db = get_db()
    cur = db.cursor()

    # Agent 统计
    cur.execute("SELECT COUNT(*) as total, SUM(status='online') as online, SUM(status='offline') as offline FROM agent_sessions")
    agent_stats = cur.fetchone() or {"total": 0, "online": 0, "offline": 0}

    # 任务统计（从 bbs_posts 的 board/task 类消息推断，或从 agent_sessions 的活跃度）
    cur.execute("SELECT COUNT(*) as total FROM bbs_posts")
    total_posts = cur.fetchone()["total"] or 0

    # 板块统计
    cur.execute("SELECT board, COUNT(*) as cnt FROM bbs_posts GROUP BY board ORDER BY cnt DESC")
    board_stats = cur.fetchall()

    # 最近活动
    cur.execute("""
        SELECT board, author, LEFT(content, 120) as preview, created_at
        FROM bbs_posts ORDER BY id DESC LIMIT 10
    """)
    recent_posts = cur.fetchall()

    db.close()

    online_count = agent_stats["online"] or 0
    offline_count = agent_stats["offline"] or 0

    with _cache["_lock"]:
        _cache["recent_posts"] = list(recent_posts)

    return {
        "agents_total": (agent_stats["total"] or 0),
        "agents_online": online_count,
        "agents_offline": offline_count,
        "total_posts": total_posts,
        "boards": board_stats,
        "recent_posts": recent_posts,
    }


# ── 页面路由 ──

@router.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request, user: dict = Depends(require_user)):
    """仪表盘主页面"""
    overview = _get_overview()
    return render_template("dashboard/index.html", nav_active="dashboard", user=user, **overview)


# ── JSON API（供前端 AJAX 刷新） ──

@router.get("/api/dashboard/overview")
def api_dashboard_overview(user: dict = Depends(require_user)):
    """总览数据 JSON"""
    return _get_overview()


@router.get("/api/dashboard/agents")
def api_dashboard_agents(user: dict = Depends(require_user)):
    """Agent 列表 JSON"""
    db = get_db()
    cur = db.cursor()
    cur.execute("""
        SELECT agent_id, status, last_online, last_offline, created_at
        FROM agent_sessions ORDER BY updated_at DESC LIMIT 100
    """)
    agents = cur.fetchall()
    db.close()
    return {"agents": agents}


@router.get("/api/dashboard/posts")
def api_dashboard_posts(board: str = "", limit: int = 20, user: dict = Depends(require_user)):
    """帖子列表 JSON"""
    db = get_db()
    cur = db.cursor()
    if board:
        cur.execute("""
            SELECT id, board, author, LEFT(content, 200) as preview, created_at
            FROM bbs_posts WHERE board=%s ORDER BY id DESC LIMIT %s
        """, (board, limit))
    else:
        cur.execute("""
            SELECT id, board, author, LEFT(content, 200) as preview, created_at
            FROM bbs_posts ORDER BY id DESC LIMIT %s
        """, (limit,))
    posts = cur.fetchall()
    db.close()
    return {"posts": posts}


# ── WebSocket 实时推送 ──

_ws_clients: list[WebSocket] = []


@router.websocket("/dashboard/ws")
async def dashboard_ws(websocket: WebSocket):
    """WebSocket 实时推送 MQTT 事件到浏览器"""
    await websocket.accept()
    _ws_clients.append(websocket)
    try:
        # 发送初始数据
        overview = _get_overview()
        await websocket.send_json({"type": "init", "data": overview})
        # 保持连接，接收心跳
        while True:
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        pass
    finally:
        if websocket in _ws_clients:
            _ws_clients.remove(websocket)


def broadcast_to_ws(event_type: str, data: dict):
    """广播消息到所有 WS 客户端（由 MQTT 回调线程调用）"""
    import asyncio
    message = json.dumps({"type": event_type, "data": data})
    for ws in _ws_clients[:]:
        try:
            # 在线程中调用异步需要小心；这里用简单方式
            asyncio.run_coroutine_threadsafe(
                ws.send_text(message), 
                _get_event_loop()
            )
        except Exception:
            pass


def _get_event_loop():
    """获取事件循环（兼容不同上下文）"""
    import asyncio
    try:
        return asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        return loop
