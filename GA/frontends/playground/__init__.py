"""Playground — Agent 游戏化沙盒"""

from pathlib import Path
from jinja2 import Environment, FileSystemLoader

_TEMPLATES_DIR = Path(__file__).resolve().parent / "templates"
templates = Environment(loader=FileSystemLoader(_TEMPLATES_DIR))
