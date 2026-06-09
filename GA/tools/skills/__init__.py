"""/tools/skills"""

# 自动导入 gbrain 技能，注册到 Registry
try:
    from . import gbrain_skill  # noqa: F401
except Exception:
    pass
