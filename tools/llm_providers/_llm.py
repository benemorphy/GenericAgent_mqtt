"""
诊断 LLM 接口 — Provider 工厂优先 + urllib 降级

用法:
    from tools._llm import DiagnosisLLM
    llm = DiagnosisLLM()
    analysis = llm.analyze(context)
"""
import os, json, urllib.request
from typing import Optional

class DiagnosisLLM:
    """统一的 LLM 分析接口，工厂优先、urllib 降级"""

    def __init__(self):
        self._llm = None
        self.available = False
        self._init()

    def _init(self):
        """初始化 LLM — 优先使用统一的 LLM Provider 工厂"""
        enabled = os.environ.get("SKILL_LLM_ENABLE", "0") == "1"
        if not enabled:
            return
        try:
            from tools.llm_provider_factory import get_llm
            api_key = os.environ.get("DEEPSEEK_API_KEY") or os.environ.get("LLM_API_KEY", "")
            self._llm = get_llm(provider="deepseek", api_key=api_key)
            self.available = True
            print("[LLM] 已通过 Provider 工厂初始化")
        except ImportError:
            self.available = bool(os.environ.get("LLM_API_KEY", ""))
            print(f"[LLM] Provider 工厂不可用，降级 urllib; {'可用' if self.available else '不可用'}")
        except Exception as e:
            print(f"[LLM] 初始化失败: {e}")

    def analyze(self, context: str) -> str:
        """执行 LLM 根因分析 — 使用统一接口或降级"""
        if not self.available:
            return "LLM 不可用，使用规则诊断"

        # 统一接口
        if self._llm is not None and hasattr(self._llm, 'chat'):
            try:
                resp = self._llm.chat([
                    {"role": "system", "content": "你是 IT 系统诊断专家，用中文回答。"},
                    {"role": "user", "content": f"分析以下系统状态，给出根因和建议：\n{context}\n\n格式：根因: ... 建议: ..."}
                ])
                return str(resp)[:500]
            except Exception as e:
                return f"LLM 分析失败: {e}"

        # 降级: urllib 直接调用
        return self._urllib_analyze(context)

    def _urllib_analyze(self, context: str) -> str:
        """urllib 降级调用 DeepSeek API"""
        try:
            api_key = os.environ.get("LLM_API_KEY", "")
            prompt = f"你是一个系统诊断专家。分析以下系统状态，给出根因和建议：\n{context}\n\n格式：根因: ... 建议: ..."
            data = json.dumps({
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": "你是 IT 系统诊断专家，用中文回答。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": 0.3
            }).encode()
            req = urllib.request.Request(
                "https://api.deepseek.com/v1/chat/completions",
                data=data,
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
            )
            with urllib.request.urlopen(req, timeout=15) as resp:
                result = json.loads(resp.read())
                return result["choices"][0]["message"]["content"][:500]
        except Exception as e:
            return f"LLM 调用失败: {e}"
