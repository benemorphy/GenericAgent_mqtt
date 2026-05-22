# FastAPI 统一网关 — 结构设计

> 将 Board Browser / Dashboard / Agent 监控 / md_server_rs 整合到一个 FastAPI 服务
> 共享 JWT 认证，路由区分，单端口部署

---

## 一、目录架构

```
frontends/
├── bbs_browser/                  # ✅ 已有 — 板块浏览
│   ├── __init__.py
│   ├── app.py                   # FastAPI router: /boards/*
│   ├── auth.py                  # JWT 注册/登录/require_user
│   ├── config.py                # DB/JWT 配置
│   ├── database.py              # DB 连接 + 查询 + 搜索
...
[Tuncated]
...├── routers/
│   │   ├── __init__.py
│   │   ├── boards.py            # /boards/* 板块浏览 (继承 bbs_browser)
│   │   ├── dashboard.py         # /dashboard/* 仪表盘
│   │   ├── agents.py            # /agents/* Agent 列表
│   │   └── docs_proxy.py        # /docs/* 反向代理 → md_server_rs:8899
│   ├── templates/
│   │   ├── layout.html          # 统一布局
│   │   ├── login.html
│   │   ├── register.html
│   │   ├── boards/              # 板块相关模板
│   │   │   ├── index.html
│   │   │   └── board.html
│   │   ├── dashboard/           # 仪表盘模板
│   │   │   └── index.html
│   │   └── agents/              # Agent 相关模板
│   │       ├── index.html
│   │       └── detail.html
│   └── static/                  # CSS/JS
│       └── gateway.css
```

## 二、模块依赖图

```
gateway/main.py
    │
    ├── routers/boards.py ──────→ bbs_browser/database.py (复用)
    │                              bbs_browser/auth.py (复用 require_user)
    │
    ├── routers/dashboard.py ────→ mqtt_bbs/board_client.py (MQTT 实时)
    │                               bbs_browser/auth.py
    │                               Jinja2: dashboard/index.html
    │
    ├── routers/agents.py ───────→ bbs_browser/database.py (agent_sessions)
    │                               bbs_browser/auth.py
    │
    └── routers/docs_proxy.py ───→ httpx → md_server_rs:8899
                                    bbs_browser/auth.py
```

## 三、路由表

```
METHOD  PATH                     HANDLER                       AUTH
──────  ──────────────────────   ────────────────────────────  ─────────
GET     /                        302 → /boards                 否
GET     /login                   login_page                    否
GET     /register                register_page                 否
POST    /api/register            api_register                  否
POST    /api/login               api_login                     否
GET     /api/logout              api_logout                    是

── Board Browser ────────────────────────────────────────────────────
GET     /boards                  boards_index                   是
GET     /boards/search           boards_search                  是
GET     /boards/{id}             board_posts                    是

── Dashboard (重写自 dashboard_mqtt.py) ──────────────────────────────
GET     /dashboard               dashboard_index                是
WS      /dashboard/ws            dashboard_ws                   token in query
POST    /dashboard/tasks/{id}/cancel  task_cancel               是 (admin)

── Agent 列表 ────────────────────────────────────────────────────────
GET     /agents                  agents_index                   是
GET     /agents/{id}             agent_detail                   是
GET     /agents/{id}/tasks       agent_tasks                    是

── 文档阅读 (md_server_rs 代理) ──────────────────────────────────────
GET     /docs/{path}             proxy_docs                     是

── JSON API ──────────────────────────────────────────────────────────
GET     /api/boards              api_boards                     是
GET     /api/boards/{id}/posts   api_board_posts                是
GET     /api/search              api_search                     是
GET     /api/agents              api_agents                     是
```

## 四、重用策略

| 模块 | 来源 | 重用方式 |
|------|------|---------|
| `config.py` | `bbs_browser/config.py` | `gateway/config.py` import 并扩展（MQTT 配置） |
| `auth.py` | `bbs_browser/auth.py` | `gateway/auth.py` 直接 import `require_user`/`create_jwt` |
| `database.py` | `bbs_browser/database.py` | `gateway/database.py` import 并添加 dashboard 专用查询 |
| `boards` 路由 | `bbs_browser/app.py` | 抽出 `router` 对象，`gateway/routers/boards.py` 引用 |
| templates | `bbs_browser/templates/` | 迁移到 `gateway/templates/` 统一目录 |
| Dashboard | `dashboard_mqtt.py` (Streamlit) | 重写为 `gateway/routers/dashboard.py` (FastAPI) |

## 五、关键设计决策

### 5.1 auth 层位置

`require_user` 依赖放在 `gateway/routers/__init__.py` 或每个 router 文件单独导入。

**选择**: 每个 router 文件显式 `from frontends.bbs_browser.auth import require_user`。
好处: 每个 router 自包含，不依赖隐式加载顺序。

### 5.2 md_server_rs 代理方式

**选择**: `httpx.AsyncClient` 异步反向代理，而不是修改 Rust 代码加认证。

理由:
- Rust 代码不需要知道认证
- FastAPI 作为统一安全边界
- 如 md_server_rs 未来加认证，替换为 JWT token 传递即可

### 5.3 Dashboard 实时推送

**选择**: FastAPI WebSocket，后端订阅 MQTT，推送到浏览器。

```
浏览器 WS ←→ FastAPI WebSocket ← MQTT client ← MQTT Broker
```

理由:
- Streamlit 的实时模型是"脚本全量重跑"，不适合高频推送
- FastAPI WebSocket 可以精准推送增量更新
- HTMX + SSE 也是备选，但 WebSocket 更灵活

### 5.4 模板共享方式

**选择**: 所有模板在 `gateway/templates/` 统一目录，按子目录分模块。

```
templates/
├── layout.html         # 共享布局（导航栏 + 用户信息）
├── login.html
├── register.html
├── boards/
│   ├── index.html
│   └── board.html
├── dashboard/
│   └── index.html
├── agents/
│   ├── index.html
│   └── detail.html
└── error.html
```

`layout.html` 使用 Jinja2 block 机制，各页面扩展:

```html
{% extends "layout.html" %}
{% block title %}板块列表{% endblock %}
{% block nav_active %}boards{% endblock %}
{% block content %}...{% endblock %}
```

## 六、main.py 骨架

```python
# frontends/gateway/main.py
from fastapi import FastAPI, Request
from fastapi.responses import RedirectResponse
from fastapi.staticfiles import StaticFiles

from frontends.bbs_browser.auth import require_user, optional_user

app = FastAPI(title="GenericAgent Gateway")

# ── 静态文件 ──
app.mount("/static", StaticFiles(directory="frontends/gateway/static"), name="static")

# ── 路由注册（按功能域分模块） ──
from frontends.gateway.routers import (
    boards,      # /boards/*
    dashboard,   # /dashboard/*
    agents,      # /agents/*
    docs_proxy,  # /docs/*
)

app.include_router(boards.router)
app.include_router(dashboard.router)
app.include_router(agents.router)
app.include_router(docs_proxy.router)

# ── 根路径重定向 ──
@app.get("/")
def root(request: Request):
    user = optional_user(request)
    if user:
        return RedirectResponse(url="/boards")
    return RedirectResponse(url="/login")

# ── 入口 ──
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("frontends.gateway.main:app", host="0.0.0.0", port=8000, reload=True)
```

## 七、实施顺序

| 步骤 | 内容 | 工时 | 依赖 |
|------|------|------|------|
| **S1** | 建目录 + `main.py` 骨架 + routers/__init__.py | 0.5h | — |
| **S2** | 迁移 templates 到统一目录 + 共享 layout | 1h | S1 |
| **S3** | 抽出 boards router 到 `routers/boards.py` | 0.5h | S2 |
| **S4** | docs_proxy 路由 → md_server_rs | 0.5h | S1 |
| **S5** | agents 路由 → MariaDB agent_sessions | 1h | S2 |
| **S6** | dashboard 路由 (FastAPI + WebSocket) | 3h | S5 |
| **合计** | | **~6.5h** | |

每个步骤都是可独立验证的增量。

## 八、部署后形态

```
启动:
    md_server_rs &                 # 后端 Rust 文档服务器
    python -m frontends.gateway.main &  # 统一网关

访问:
    http://localhost:8000/         → 登录 → 板块广场
    http://localhost:8000/boards   → 板块浏览
    http://localhost:8000/dashboard → 实时仪表盘
    http://localhost:8000/agents   → Agent 列表
    http://localhost:8000/docs/    → Markdown 文档
```
