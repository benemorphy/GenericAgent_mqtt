"""LLM Provider 工厂模块 — ProviderProtocol + ProviderRegistry

Phase 1: 定义接口 + 注册表，包装现有 resolve_session 行为。
Phase 2+: 各 Provider 独立文件（claude.py, openai.py, ...）
          继承 ProviderProtocol 并 register 即可。

用法（在 llmcore.py resolve_session 中）:
    from tools.llm_providers import ProviderRegistry
    return ProviderRegistry.create(cfg_name, cfg)
"""

import os
import sys
import abc
import importlib
from typing import Any


class ProviderProtocol(abc.ABC):
    """LLM Provider 必须实现的接口。

    一个 Provider 负责：
    - 判断是否匹配某个配置名称（match）
    - 创建针对该 Provider 的 Session 实例（create_session）
    - 提供 SSE 解析、JSON 解析、消息格式转换等 Provider 专属方法
    """

    NAME: str = ""  # 唯一标识，如 'claude_native', 'openai'

    @classmethod
    @abc.abstractmethod
    def match(cls, cfg_name: str) -> bool:
        """判断该 Provider 是否能处理给定配置名。"""
        ...

    @classmethod
    @abc.abstractmethod
    def create_session(cls, cfg: dict) -> Any:
        """根据配置创建 Session 实例。"""
        ...


class ProviderRegistry:
    """Provider 注册表 — 注册式工厂。

    参考 tools.hooks_default 的注册模式。
    """

    _providers: dict[str, type[ProviderProtocol]] = {}

    @classmethod
    def register(cls, provider_cls: type[ProviderProtocol]) -> None:
        """注册一个 Provider 类到注册表。"""
        name = getattr(provider_cls, 'NAME', provider_cls.__name__)
        if name in cls._providers:
            print(f"[ProviderRegistry] Overwriting provider '{name}'")
        cls._providers[name] = provider_cls

    @classmethod
    def create(cls, cfg_name: str, cfg: dict) -> Any:
        """根据配置名匹配 Provider 并创建 Session。

        遍历注册表，调用每个 Provider 的 match(cfg_name)，
        第一个返回 True 的 Provider 负责创建。
        若无匹配，回退到 llmcore 的旧版 resolve_session 逻辑。
        """
        for name, provider_cls in cls._providers.items():
            if provider_cls.match(cfg_name):
                return provider_cls.create_session(cfg)
        # Fallback: 如果未注册任何 Provider，尝试旧版逻辑
        return _legacy_resolve_session(cfg_name, cfg)

    @classmethod
    def list_providers(cls) -> list[str]:
        """列出所有已注册的 Provider 名称。"""
        return list(cls._providers.keys())


# ── Legacy fallback — 在 Provider 未完全提取前保持兼容 ──

def _legacy_resolve_session(cfg_name: str, cfg: dict) -> Any:
    """旧版 resolve_session 逻辑的直接实现（不回调用 llmcore.resolve_session，避免循环递归）。

    当注册表为空或没有匹配的 Provider 时使用。
    等所有 Provider 提取完成后可删除此函数。
    """
    name_lower = cfg_name.lower()
    if 'native' in name_lower:
        if 'claude' in name_lower:
            from llmcore import NativeClaudeSession
            return NativeClaudeSession(cfg=cfg)
        # native + oai / openai / gpt
        from llmcore import NativeOAISession
        return NativeOAISession(cfg=cfg)
    if 'claude' in name_lower:
        from llmcore import ClaudeSession
        return ClaudeSession(cfg=cfg)
    # 非 Native OAI 兼容
    if name_lower.endswith('_oai') or name_lower.endswith('_api') or \
       'deepseek' in name_lower or 'gpt' in name_lower or \
       name_lower.startswith('o1') or name_lower.startswith('o3') or \
       'oai' in name_lower:
        from llmcore import LLMSession
        return LLMSession(cfg=cfg)
    raise ValueError(f"[ProviderRegistry] No provider matched for '{cfg_name}'")

# auto_import: 尝试导入各 Provider 模块（它们会在模块级自行 register）
for _mod_name in ['claude', 'openai', 'doubao', 'doubao_backend']:
    try:
        importlib.import_module(f'tools.llm_providers.{_mod_name}')
    except ImportError:
        pass  # 模块不存在时跳过
