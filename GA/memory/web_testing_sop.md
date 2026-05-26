# Web Testing SOP (Playwright + Python)

> 来源: skills.sh/anthropics/skills/webapp-testing

## 核心原则

1. **黑盒优先** — 用 `--help` 了解脚本，不要先用代码阅读
2. **侦察-行动工作流** — 先截图/DOM分析，再定位元素，最后操作
3. **等待 networkidle** — 动态应用必须先等 networkidle 再检查 DOM

## 决策树

```
用户任务 → 是否静态HTML?
  ├─ Yes → 直接读取HTML定位选择器
  ├─ No (动态webapp) → 服务是否已运行?
  │   ├─ No → with_server.py 启动
  │   └─ Yes → 侦察-行动模式
```

## Playwright 标准模板

```python
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    page.goto('http://localhost:8000')
    page.wait_for_load_state('networkidle')  # 关键等待
    # 侦察: 截图 + 获取DOM
    page.screenshot(path='/tmp/inspect.png', full_page=True)
    content = page.content()
    buttons = page.locator('button').all()
    # 行动: 使用发现的选择器
    page.locator('text=计算').click()
    page.wait_for_timeout(500)
    browser.close()
```

## with_server.py 用法

```bash
# 单服务器
python scripts/with_server.py --server "uvicorn main:app" --port 8000 -- python test.py

# 多服务器 (前后端)
python scripts/with_server.py \
  --server "cd backend && python server.py" --port 3000 \
  --server "cd frontend && npm run dev" --port 5173 \
  -- python test.py
```

## 选择器最佳实践

| 类型 | 示例 | 优先级 |
|------|------|--------|
| text= | `text=计算` | ⭐ 首选 |
| role= | `role=button` | ⭐ 首选 |
| CSS | `button.btn-primary` | ✅ 好 |
| ID | `#btnCalculate` | ✅ 准确 |
| XPath | `//button[1]` | ⚠ 脆弱 |

## 常见陷阱

- ❌ 未等 networkidle 就检查 DOM → 收到未渲染的空页面
- ❌ 直接读 `with_server.py` 源码 → 浪费上下文窗口
- ✅ 先 `--help` 了解参数 → 黑盒调用
- ✅ 每次测试后关闭 browser

## 配合工具

| 工具 | 用途 |
|------|------|
| pytest | 单元/集成测试框架 |
| Playwright | 浏览器E2E自动化 |
| coverage.py | 覆盖率测量 |
| hypothesis | 基于属性测试 |
| tox | 多环境测试 |