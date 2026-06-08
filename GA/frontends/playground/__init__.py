"""Playground — Agent 游戏化沙盒"""

from pathlib import Path
from frontends.web_ui import create_template_env

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = create_template_env(_TEMPLATES_DIR)
