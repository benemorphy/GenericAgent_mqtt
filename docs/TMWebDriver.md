### Python TMWebDriver 库

**TMWebDriver** 是 **GenericAgent 框架**中的一个**自研浏览器控制模块**（非 PyPI 官方库），用于接管**真实浏览器**（保留登录态），解决 Selenium/Playwright 难以处理的**复杂浏览器交互**（如跨域、文件上传、HttpOnly Cookie、物理坐标点击）。

### 一、核心定位

- 不属于 Selenium/Playwright，是**轻量自研驱动**
- 特点：**注入真实浏览器、持久化登录态、突破前端限制、支持远程控制**
- 场景：AI 智能体网页自动化、复杂爬虫、人机协作浏览器控制

### 二、安装与依赖

无官方 PyPI 包，需从 GenericAgent 仓库获取：

```bash
git clone https://github.com/lsdefine/GenericAgent.git
cd GenericAgent
# 安装依赖
pip install bottle simple_websocket_server beautifulsoup4
```

依赖：`bottle`（HTTP 服务）、`simple_websocket_server`（WebSocket）、`bs4`（解析）

### 三、核心原理

- 启动本地 **HTTP+WebSocket 双服务**（默认端口 18765/18766）
- 浏览器安装\*\*用户脚本（*Tampermonkey*）\*\*作为通信桥梁
- Python 服务 ↔ 浏览器插件 ↔ 真实页面，双向通信
- 支持**会话管理、JS 注入、DOM 解析、远程调用**

### 四、基础用法

```python
from TMWebDriver import TMWebDriver

# 1. 启动驱动（本地模式，自动启服务）
driver = TMWebDriver(host="127.0.0.1", port=18765)

# 2. 绑定浏览器（需手动安装 Tampermonkey 脚本）
# 脚本地址：仓库 tmwebdriver.user.js

# 3. 打开网页
driver.open("https://example.com")

# 4. 执行 JS
driver.execute_js("document.title")

# 5. 获取页面内容
html = driver.get_html()

# 6. 关闭会话
driver.close()
```

### 五、关键能力（对比 Selenium）

| 能力                 | TMWebDriver | Selenium  |
| ------------------ | ----------- | --------- |
| 真实浏览器登录态           | ✅ 持久化       | ❌ 每次重启清空  |
| HttpOnly Cookie 读取 | ✅ 支持        | ❌ 无法获取    |
| 跨域 iframe 操作       | ✅ 突破限制      | ❌ 受同源策略限制 |
| 文件上传（含目录）          | ✅ 物理路径      | ❌ 仅文件路径   |
| 远程控制（跨机器）          | ✅ 内置服务      | ❌ 需额外配置   |
| 前端反爬绕过             | ✅ 真实环境      | ❌ 易被检测    |

### 六、适用场景

1. **AI 智能体网页操作**：GenericAgent 内置工具，支持复杂交互
2. **复杂爬虫**：需登录、跨域、文件上传的场景
3. **自动化测试**：保留登录态，模拟真实用户
4. **人机协作**：AI 操作+人工确认，安全可控

### 七、局限性

- **非标准库**：无官方文档，依赖仓库更新
- **需浏览器插件**：依赖 Tampermonkey，部署稍复杂
- **安全性**：控制真实浏览器，需警惕恶意操作

### 总结

TMWebDriver 是 Python 生态中**小众但强大的浏览器控制工具**，核心优势是**真实浏览器注入+持久化登录态+突破前端限制**，适合 AI 智能体和复杂自动化场景，替代 Selenium/Playwright 难以胜任的任务。

需要我帮你整理一份 TMWebDriver 与 Selenium/Playwright 的选型决策清单吗？
