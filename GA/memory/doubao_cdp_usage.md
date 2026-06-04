# Doubao CDP 使用SOP — "使用豆包，找xxx"

## 触发词
用户说含 **"使用豆包"** 的指令 → 调用本机豆包APP搜索

## 用法
```python
from tools.llm_providers import ProviderRegistry

# 方式1：直接获取DoubaoBackend（推荐）
session = ProviderRegistry.create('doubao', {})
for chunk in session.raw_ask([{"role": "user", "content": "搜索xxx"}]):
    print(chunk)

# 方式2：通过resolve_client获取ToolClient
client = resolve_client('doubao')  # 返回包装后的ToolClient
client.chat("搜索xxx")
```

## 工作流程
1. **懒启动**: 首次调用时自动启动本机豆包APP（`Doubao.exe`）
2. **CDP连接**: 通过 `ws://127.0.0.1:9222` 的Chrome DevTools Protocol连接
3. **导航**: 确保页面在 `https://www.doubao.com/chat`
4. **输入**: 用 `nativeSetter` + `dispatchEvent` 向textarea注入文本（兼容Semi Design UI）
5. **发送**: 模拟Enter键（keydown + keyup）
6. **读取**: 等待豆包生成回复后提取结果

## 关键配置
| 项 | 值 |
|---|---|
| CDP端口 | 9222 |
| 豆包路径 | `C:\Users\user\AppData\Local\Doubao\Application\app\Doubao.exe` |
| 自动重试 | 2次（失败自动重建CDP连接） |

## 已知坑（已验证）
- 登录：`--user-data-dir=临时目录`（原版）会丢失登录态，必须用真实目录 `%LocalAppData%/Doubao/User Data`
- 页面选择：`_get_page_target()` 会从3个页面中选，必须跳过 `doubao-launcher`，优先选 `doubao-chat/chat`，否则body文本为空
- SPA渲染：导航到web版后仅等待textarea出现不够，需要额外等15秒让SPA完全渲染
- 发送消息：synthetic `KeyboardEvent('Enter')` 在web版无效（`event.isTrusted`检测），必须使用CDP原生命令 `Input.dispatchKeyEvent`
- 发送按钮：web版send按钮通常以SVG图标形式存在，无"发送"文字，需通过 `querySelectorAll('button')` 全量扫描
- 回复提取：`document.body.innerText` 在web版可获取AI回复，需设置 `bl > 300` 进入检测，连续5秒稳定才确认完成
- 流式限制：CDP方式不能流式读取回复，只能等完整回复后一次性提取
