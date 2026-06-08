"""FastAPI Web UI — 聚合 Board Browser / Dashboard / Agents"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))


def create_template_env(template_dir: Path) -> Environment:
    """创建 Jinja2 Environment 工厂函数"""
    return Environment(loader=FileSystemLoader(template_dir))


def render_template(name: str, nav_active: str = "", **ctx) -> str:
    """渲染模板，自动注入用户上下文"""
    user = ctx.pop("user", None)
    return templates.get_template(name).render(user=user, nav_active=nav_active, **ctx)
