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

## 已知坑
- 首次调用需等待豆包启动（~5-10s）
- CDP端口9222不与其他CDP调试端口冲突
- Semi Design UI的textarea需要特殊注入方式（普通赋值无法触发React状态更新）
- 无流式支持：CDP方式只能等完整回复后一次性返回
