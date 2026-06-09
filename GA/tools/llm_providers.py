"""
LLM Provider Registry — 统一的LLM提供方注册与发现

用法:
    from tools.llm_providers import ProviderRegistry
    session = ProviderRegistry.create("doubao", {})
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


class DouBaoSession(LLMSession):
    """本机豆包 (vLLM/SGLang部署)"""
    def __init__(self, config: dict):
        super().__init__("doubao", config)
        self.endpoint = config.get("endpoint", "http://localhost:8000/v1/chat/completions")
        self.model = config.get("model", "doubao-pro-32k")
        self._available = False
        try:
            import urllib.request
            models_url = self.endpoint.replace("/chat/completions", "/models")
            req = urllib.request.Request(models_url, headers={"Content-Type": "application/json"})
            resp = urllib.request.urlopen(req, timeout=3)
            self._available = resp.status == 200
        except Exception:
            pass

    @property
    def available(self) -> bool:
        return self._available

    def chat(self, prompt: str) -> str:
        if not self._available:
            return "[Doubao不可用]"
        import urllib.request
        payload = json.dumps({
            "model": self.model,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": self.config.get("temperature", 0.7),
            "max_tokens": self.config.get("max_tokens", 4096),
        }).encode()
        req = urllib.request.Request(
            self.endpoint, data=payload,
            headers={"Content-Type": "application/json"}, method="POST"
        )
        resp = urllib.request.urlopen(req, timeout=self.config.get("timeout", 120))
        result = json.loads(resp.read().decode())
        return result["choices"][0]["message"]["content"]


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


ProviderRegistry.register("doubao", DouBaoSession)
