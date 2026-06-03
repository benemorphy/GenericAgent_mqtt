"""Doubao CDP Provider — 通过 Chrome DevTools Protocol 控制本机豆包

架构:
  LLM Provider 工厂模式 — 注册为 'doubao' Provider
  生命周期: lazy_init → launch_doubao → connect_cdp → navigate → chat → close

使用:
  配置 cfg_name 包含 'doubao' 即自动匹配此 Provider
"""

import os
import sys
import json
import time
import subprocess
import tempfile
import asyncio
import threading
from typing import Any, AsyncGenerator

import httpx
import websockets

from tools.llm_providers import ProviderRegistry, ProviderProtocol

# ── 常量 ──
DOUBAO_EXE = r"C:\Users\user\AppData\Local\Doubao\Application\app\Doubao.exe"
CDP_PORT = 9222
CDP_URL = f"http://127.0.0.1:{CDP_PORT}"
WS_BROWSER_URL = f"ws://127.0.0.1:{CDP_PORT}/devtools/browser/"
CHAT_URL = "https://www.doubao.com/chat"

# ── CDP 工具函数 ──

async def _cdp_send(ws, method: str, params: dict = None) -> dict:
    """发送 CDP 命令并等待响应。"""
    msg_id = int(time.time() * 1000) % 100000
    cmd = {"id": msg_id, "method": method}
    if params:
        cmd["params"] = params
    await ws.send(json.dumps(cmd))
    async for raw in ws:
        resp = json.loads(raw)
        if resp.get("id") == msg_id:
            return resp.get("result", {})
    return {}


async def _cdp_listen(ws, timeout: float = 30.0) -> AsyncGenerator[dict, None]:
    """监听 CDP 事件流。"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            raw = await asyncio.wait_for(ws.recv(), timeout=1.0)
            yield json.loads(raw)
        except asyncio.TimeoutError:
            continue
        except websockets.exceptions.ConnectionClosed:
            break


async def _get_page_target() -> str | None:
    """获取豆包页面的 targetId (page类型)。"""
    r = httpx.get(f"{CDP_URL}/json", timeout=5)
    for t in r.json():
        if t.get("type") == "page":
            return t["id"]
    return None


async def _wait_for_page_target(timeout: float = 30.0) -> str:
    """等待页面 target 出现。"""
    for i in range(int(timeout / 2)):
        tid = await _get_page_target()
        if tid:
            return tid
        await asyncio.sleep(2)
    raise RuntimeError("Doubao page target not found")


async def _navigate_and_wait(ws, target_id: str, url: str, timeout: float = 20.0):
    """导航到 URL 并等待 DOM 就绪。"""
    # 获取 page 的 WS URL
    r = httpx.get(f"{CDP_URL}/json", timeout=5)
    page_ws_url = None
    for t in r.json():
        if t["id"] == target_id:
            page_ws_url = t["webSocketDebuggerUrl"]
            break
    if not page_ws_url:
        raise RuntimeError(f"Cannot find WS URL for target {target_id}")

    async with websockets.connect(page_ws_url) as page_ws:
        # 启用 Page 和 DOM 域
        await _cdp_send(page_ws, "Page.enable")
        await _cdp_send(page_ws, "DOM.enable")

        # 导航
        await _cdp_send(page_ws, "Page.navigate", {"url": url})

        # 等待 DOMContentLoaded
        async for evt in _cdp_listen(page_ws, timeout=timeout):
            if evt.get("method") == "Page.frameStoppedLoading":
                break

    return page_ws_url


async def _evaluate_js(ws, target_id: str, js_code: str) -> Any:
    """在页面中执行 JS 并返回结果。"""
    async with websockets.connect(
        f"ws://127.0.0.1:{CDP_PORT}/devtools/page/{target_id}"
    ) as page_ws:
        result = await _cdp_send(page_ws, "Runtime.evaluate", {
            "expression": js_code,
            "returnByValue": True,
            "awaitPromise": True,
        })
        if "result" in result:
            val = result["result"].get("value")
            if result["result"].get("type") == "string":
                return val
            if result["result"].get("type") == "object" and val:
                return val
            exc = result.get("exceptionDetails")
            if exc:
                raise RuntimeError(f"JS Error: {exc}")
            return val
        return None


async def _chat_with_doubao(prompt: str, timeout: float = 120.0) -> str:
    """通过 CDP 在豆包页面完成一次对话。

    DOM 结构（doubao.com/chat）:
      - 输入框: textarea.semi-input-textarea  placeholder="发消息..."
      - 发送: Enter 键触发（Semi Design UI 无独立发送按钮）
    """
    # 1. 获取页面 target
    target_id = await _wait_for_page_target()
    page_ws_url = f"ws://127.0.0.1:{CDP_PORT}/devtools/page/{target_id}"

    # 2. 确保在 chat 页面
    async with websockets.connect(page_ws_url) as page_ws:
        await _cdp_send(page_ws, "Page.enable")
        await _cdp_send(page_ws, "Runtime.enable")

        # 检查当前 URL
        result = await _cdp_send(page_ws, "Runtime.evaluate", {
            "expression": "window.location.href",
            "returnByValue": True,
        })
        current_url = result.get("result", {}).get("value", "")

        if CHAT_URL not in current_url:
            # 导航到 chat 页面
            await _cdp_send(page_ws, "Page.navigate", {"url": CHAT_URL})
            async for evt in _cdp_listen(page_ws, timeout=20):
                if evt.get("method") == "Page.frameStoppedLoading":
                    break
            await asyncio.sleep(5)  # 等待 SPA 渲染

        # 3. 发送 prompt
        safe_prompt = json.dumps(prompt)
        send_js = f"""
(async () => {{
    // 查找输入框 (Semi Design textarea)
    const ta = document.querySelector('textarea.semi-input-textarea');
    if (!ta) return 'NO_INPUT_FOUND';

    // 使用原生 value setter 触发 React/Semi 状态更新
    const nativeSetter = Object.getOwnPropertyDescriptor(
        window.HTMLTextAreaElement.prototype, 'value'
    ).set;
    nativeSetter.call(ta, {safe_prompt});

    // 触发 React SyntheticEvent
    ta.dispatchEvent(new Event('input', {{bubbles: true}}));
    ta.dispatchEvent(new Event('change', {{bubbles: true}}));

    // 等待 React 状态同步
    await new Promise(r => setTimeout(r, 300));

    // 回车发送 (keydown + keyup)
    ta.dispatchEvent(new KeyboardEvent('keydown', {{
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
    }}));
    ta.dispatchEvent(new KeyboardEvent('keyup', {{
        key: 'Enter', code: 'Enter', keyCode: 13, which: 13,
        bubbles: true, cancelable: true
    }}));

    return 'SENT';
}})()
"""

        result = await _cdp_send(page_ws, "Runtime.evaluate", {
            "expression": send_js,
            "returnByValue": True,
            "awaitPromise": True,
        })
        status = result.get("result", {}).get("value", "UNKNOWN")
        if status == "NO_INPUT_FOUND":
            # 尝试获取页面结构
            html_snap = await _cdp_send(page_ws, "Runtime.evaluate", {
                "expression": "document.body.innerText.substring(0, 2000)",
                "returnByValue": True,
            })
            page_text = html_snap.get("result", {}).get("value", "")
            raise RuntimeError(
                f"Cannot find input on doubao page. Status: {status}. "
                f"Page text: {page_text[:500]}"
            )

        # 4. 等待 AI 回复完成 — 轮询 body text 直到稳定
        await asyncio.sleep(3)  # 初始等待 AI 开始生成
        last_text = ""
        stable_count = 0
        for _ in range(int(timeout / 1)):
            await asyncio.sleep(1)
            result = await _cdp_send(page_ws, "Runtime.evaluate", {
                "expression": "document.body.innerText",
                "returnByValue": True,
            })
            full_text = result.get("result", {}).get("value", "")
            # 提取不同于初始页面文本的新增内容
            if full_text and full_text == last_text:
                stable_count += 1
                if stable_count >= 3:  # 连续3秒无变化 → 认为完成
                    return full_text
            elif full_text:
                last_text = full_text
                stable_count = 0

        return last_text or "TIMEOUT_NO_RESPONSE"


class DoubaoCDPSession:
    """豆包 CDP 会话 — 适配 GA Adapter 的 Session 接口。"""

    def __init__(self, cfg: dict = None):
        self.cfg = cfg or {}
        self._proc: subprocess.Popen | None = None
        self._user_data_dir: str | None = None
        self._loop: asyncio.AbstractEventLoop | None = None

    def _ensure_doubao(self):
        """确保豆包 CDP 进程运行。"""
        if self._proc and self._proc.poll() is None:
            return  # 已在运行

        # 清理旧进程
        subprocess.run(["taskkill", "/F", "/IM", "Doubao.exe"],
                       capture_output=True, timeout=5)
        time.sleep(2)

        # 创建临时用户数据目录
        self._user_data_dir = os.path.join(
            tempfile.gettempdir(), f"doubao_cdp_{int(time.time())}"
        )
        os.makedirs(self._user_data_dir, exist_ok=True)

        # 启动
        self._proc = subprocess.Popen(
            [DOUBAO_EXE,
             f"--remote-debugging-port={CDP_PORT}",
             f"--user-data-dir={self._user_data_dir}",
             "--no-first-run"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )

        # 等待 CDP 就绪
        for i in range(15):
            time.sleep(2)
            try:
                r = httpx.get(f"{CDP_URL}/json/version", timeout=3)
                if r.status_code == 200:
                    print(f"[DoubaoCDP] CDP ready ({2*(i+1)}s)")
                    return
            except Exception:
                continue
        raise RuntimeError("Failed to start Doubao CDP")

    def chat(self, prompt: str, timeout: float = 120.0) -> str:
        """同步对话入口。"""
        self._ensure_doubao()

        # 创建事件循环
        try:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(_chat_with_doubao(prompt, timeout))
            return result
        finally:
            loop.close()

    def close(self):
        """关闭豆包进程。"""
        if self._proc:
            self._proc.kill()
            self._proc = None
        # 清理临时目录
        if self._user_data_dir and os.path.exists(self._user_data_dir):
            import shutil
            try:
                shutil.rmtree(self._user_data_dir, ignore_errors=True)
            except Exception:
                pass


# ── Provider 注册 ──

class DoubaoCDPProvider(ProviderProtocol):
    """豆包本地 CDP Provider — 通过桌面端实现 LLM 调用。"""
    NAME = "doubao"

    @classmethod
    def match(cls, cfg_name: str) -> bool:
        low = cfg_name.lower().replace("-", "_").replace(" ", "")
        return low == "doubao" or low.startswith("doubao")

    @classmethod
    def create_session(cls, cfg: dict) -> Any:
        return DoubaoCDPSession(cfg=cfg)


# 模块级注册
ProviderRegistry.register(DoubaoCDPProvider)
