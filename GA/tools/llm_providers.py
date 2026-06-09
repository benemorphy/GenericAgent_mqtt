"""
LLM Provider Registry — 统一的LLM提供方注册与发现

用法:
    from tools.llm_providers import ProviderRegistry
    session = ProviderRegistry.create("deepseek", {})
    response = session.chat("你的问题")
"""

import json
from typing import Optional, Dict, Any, List


class LLMSession:
    def __init__(self, provider: str, config: dict):
        self.provider = provider
        self.config = config

    def chat(self, prompt: str) -> str:
        raise NotImplementedError


class ProviderRegistry:
    _providers = {}

    @classmethod
    def register(cls, name: str, session_class):
        cls._providers[name] = session_class

    @classmethod
    def create(cls, name: str, config: dict = None) -> LLMSession:
        config = config or {}
        if name in cls._providers:
            return cls._providers[name](config)
        raise ValueError(f"Unknown provider: {name}")

    @classmethod
    def available_providers(cls) -> List[str]:
        return list(cls._providers.keys())
