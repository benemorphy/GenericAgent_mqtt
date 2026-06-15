"""frontends package — 共享 sys.path 注入 + 模板工厂"""

import sys
from pathlib import Path
from jinja2 import Environment, FileSystemLoader

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))


def create_template_env(template_dir: Path) -> Environment:
    """创建 Jinja2 Environment 工厂函数"""
    return Environment(loader=FileSystemLoader(template_dir))
