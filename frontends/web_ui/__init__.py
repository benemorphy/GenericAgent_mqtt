"""FastAPI Web UI — 聚合 Board Browser / Dashboard / Agents"""

from pathlib import Path
from frontends import create_template_env

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = create_template_env(_TEMPLATES_DIR)


def render_template(name: str, nav_active: str = "", **ctx) -> str:
    """渲染模板，自动注入用户上下文"""
    user = ctx.pop("user", None)
    return templates.get_template(name).render(user=user, nav_active=nav_active, **ctx)
