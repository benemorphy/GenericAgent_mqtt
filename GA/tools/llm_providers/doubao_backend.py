"""Doubao CDP Backend — 包装 DoubaoCDPSession 为 BaseSession 兼容接口

功能:
  1. 实现 raw_ask(messages) 生成器接口，与 GA Adapter 兼容
  2. 自动管理 CDP 生命周期（lazy init, 自动重连）
  3. 注册到 ProviderFactory，可通过 resolve_client('doubao') 获取

使用:
  from tools.llm_providers import ProviderRegistry
  session = ProviderRegistry.create('doubao', {})  # -> DoubaoCDPSession
  # 或通过 resolve_client('doubao') 获取包装后的 ToolClient
"""

import os, sys, json, re, time, threading
from typing import List, Dict, Generator, Optional

# 导入 doubao CDP 会话
_PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

from tools.llm_providers.doubao import DoubaoCDPSession


class DoubaoBackend:
    """Doubao CDP 后端 — 实现 BaseSession 兼容接口。

    属性（与 BaseSession 一致）:
      name: 显示名称 ("Doubao(本地)")
      model: 模型标识 ("doubao")
      history: 对话历史
      lock: 线程锁
    """

    def __init__(self, cfg: dict = None):
        self.cfg = cfg or {}
        self.name = "Doubao(本地)"
        self.model = "doubao"
        self.history = []
        self.lock = threading.Lock()
        self.system = ""
        self.max_retries = 2
        self.stream = True
        # 懒初始化 CDP 会话
        self._session = None
        self._session_lock = threading.Lock()

    def _ensure_session(self):
        """懒初始化 CDP 会话。"""
        if self._session is None:
            with self._session_lock:
                if self._session is None:
                    self._session = DoubaoCDPSession(cfg=self.cfg)

    def ask(self, prompt: str) -> Generator[str, None, None]:
        """兼容 ToolClient 接口 — 单字符串入参。

        ToolClient.chat() 调 self.backend.ask(string)，
        此处包装为 messages 格式委托给 raw_ask。
        """
        return self.raw_ask([{"role": "user", "content": prompt}])

    def raw_ask(self, messages: List[dict]) -> Generator[str, None, None]:
        """实现 BaseSession.raw_ask 接口 — 生成器。

        Args:
          messages: [{"role": "user", "content": "..."}, ...]

        Yields:
          文本片段（首段包含完整回复，CDP 暂不支持流式）
        """
        # 提取用户最后一条消息
        user_text = ""
        for m in reversed(messages):
            if m["role"] == "user":
                content = m.get("content", "")
                if isinstance(content, list):
                    for block in content:
                        if isinstance(block, dict) and block.get("type") == "text":
                            user_text = block.get("text", "")
                            break
                elif isinstance(content, str):
                    user_text = content
                break

        if not user_text:
            yield "（错误：未找到用户消息）"
            return

        # 调用 doubao CDP
        self._ensure_session()
        for attempt in range(self.max_retries + 1):
            try:
                response = self._session.chat(user_text)
                yield response
                return
            except Exception as e:
                if attempt < self.max_retries:
                    time.sleep(2)
                    # 重新创建会话
                    with self._session_lock:
                        try:
                            self._session.close()
                        except Exception:
                            pass
                        self._session = DoubaoCDPSession(cfg=self.cfg)
                else:
                    yield f"（Doubao CDP 错误: {e}）"
                    return

    def close(self):
        """关闭 CDP 会话。"""
        if self._session is not None:
            try:
                self._session.close()
            except Exception:
                pass
            self._session = None


# ── 注册到 ProviderFactory ──────────────────────────────────
from tools.llm_providers import ProviderRegistry, ProviderProtocol


class DoubaoBackendProvider(ProviderProtocol):
    """Doubao Backend Provider — 返回包装后的 Backend 对象。"""
    NAME = "doubao_backend"

    @classmethod
    def match(cls, cfg_name: str) -> bool:
        low = cfg_name.lower().replace("-", "_").replace(" ", "")
        return low == "doubao_backend" or low.startswith("doubao_backend")

    @classmethod
    def create_session(cls, cfg: dict):
        return DoubaoBackend(cfg=cfg)


ProviderRegistry.register(DoubaoBackendProvider)
