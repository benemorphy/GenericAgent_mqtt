# Pip Use SOP
## Rule
Any library installation must use `uv pip` instead of `pip`:
```
uv pip install <package>
```
Do NOT use `pip install` or `python -m pip install`.

## Background
User found `pip install matplotlib` was unnecessary (text output suffices).
Established to avoid unnecessary package bloat and use the faster `uv` tool.
