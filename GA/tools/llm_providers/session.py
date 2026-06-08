"""
LLM Session 层 — 会话管理与多模型回退
提取自 llmcore.py Phase 1：保持对 llmcore 的单向依赖，后续逐步解耦。
"""

import time
import copy
from tools.utils.retry_utils import retry_stream
from tools.utils.logger import log

# ── 临时依赖：从 llmcore 导入工具函数（后续独立到 utils.py） ──
from llmcore import (
    auto_make_url, _record_usage, _raw_api_post,
    _openai_stream, _msgs_claude2oai, _parse_claude_sse, _parse_claude_json,
    _fix_messages, _drop_unsigned_thinking, BaseSession,
)


class ClaudeSession(BaseSession):
    """Claude API 原生 Session"""

    @retry_stream()
    def raw_ask(self, messages):
        messages = _fix_messages(messages)
        if self.max_tokens is None:
            self.max_tokens = 8192
        headers = {
            "x-api-key": self.api_key,
            "Content-Type": "application/json",
            "anthropic-version": "2023-06-01",
            "anthropic-beta": "prompt-caching-2024-07-31",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "max_tokens": self.max_tokens,
            "stream": self.stream,
        }
        if self.temperature != 1:
            payload["temperature"] = self.temperature
        self._apply_claude_thinking(payload)
        if self.system:
            payload["system"] = [{
                "type": "text",
                "text": self.system,
                "cache_control": {"type": "persistent"},
            }]
        url = auto_make_url(self.api_base, "messages")
        if self.stream:
            parse_fn = lambda r: _parse_claude_sse(r.iter_lines(), _record_usage)
        else:
            parse_fn = lambda r: _parse_claude_json(r.json(), _record_usage)
        return (yield from _raw_api_post(self, url, headers, payload, parse_fn))

    def make_messages(self, raw_list):
        msgs = _drop_unsigned_thinking([
            {"role": m['role'], "content": list(m['content'])} for m in raw_list
        ])
        user_idxs = [i for i, m in enumerate(msgs) if m['role'] == 'user']
        for idx in user_idxs[-2:]:
            msgs[idx]["content"][-1] = dict(
                msgs[idx]["content"][-1],
                cache_control={"type": "ephemeral"},
            )
        return msgs


class LLMSession(BaseSession):
    """OpenAI 兼容 API Session"""

    def raw_ask(self, messages):
        return (yield from _openai_stream(self, messages))

    def make_messages(self, raw_list):
        return _msgs_claude2oai(_fix_messages(raw_list))


class MixinSession:
    """多模型回退会话 — primary 失败时自动切换备用模型，超时后回弹。"""

    def __init__(self, all_sessions, cfg):
        self._retries = cfg.get('max_retries', 3)
        self._base_delay = cfg.get('base_delay', 1.5)
        self._spring_sec = cfg.get('spring_back', 300)
        self._sessions = [
            all_sessions[i].backend if isinstance(i, int) else
            next(s.backend for s in all_sessions if type(s) is not dict and s.backend.name == i)
            for i in cfg.get('llm_nos', [])
        ]
        is_native = lambda s: 'Native' in s.__class__.__name__
        groups = {is_native(s) for s in self._sessions}
        assert len(groups) == 1, (
            f"MixinSession: sessions must be in same group (Native or non-Native), "
            f"got {[type(s).__name__ for s in self._sessions]}"
        )
        self.name = '|'.join(s.name for s in self._sessions)
        self._sessions = [copy.copy(s) for s in self._sessions]
        for s in self._sessions:
            s.max_retries = 0
        self._orig_raw_asks = [s.raw_ask for s in self._sessions]
        self._sessions[0].raw_ask = self._raw_ask
        self.model = getattr(self._sessions[0], 'model', None)
        self._cur_idx = 0
        self._switched_at = 0.0

    def __getattr__(self, name):
        return getattr(self._sessions[0], name)

    _BROADCAST_ATTRS = frozenset({
        'system', 'tools', 'temperature', 'max_tokens',
        'reasoning_effort', 'history',
    })

    def __setattr__(self, name, value):
        if name in self._BROADCAST_ATTRS:
            from llmcore import NativeClaudeSession, openai_tools_to_claude
            for s in self._sessions:
                v = openai_tools_to_claude(value) if name == 'tools' and type(s) is NativeClaudeSession else value
                setattr(s, name, v)
        else:
            object.__setattr__(self, name, value)

    @property
    def primary(self):
        return self._sessions[0]

    def _pick(self):
        if self._cur_idx and time.time() - self._switched_at > self._spring_sec:
            self._cur_idx = 0
        return self._cur_idx

    def _raw_ask(self, *args, **kwargs):
        base, n = self._pick(), len(self._sessions)
        test_error = lambda x: isinstance(x, str) and x.lstrip().startswith(('!!!Error:', '[Error:'))
        for attempt in range(self._retries + 1):
            idx = (base + attempt) % n
            gen = self._orig_raw_asks[idx](*args, **kwargs)
            log.info('MixinSession using session (%s)', self._sessions[idx].name)
            last_chunk = None
            return_val = []
            yielded = False
            try:
                while True:
                    chunk = next(gen)
                    last_chunk = chunk
                    if not yielded and test_error(chunk):
                        continue
                    yield chunk
                    yielded = True
            except StopIteration as e:
                return_val = e.value or []
            is_err = test_error(last_chunk)
            if not is_err:
                if attempt > 0:
                    self._cur_idx = idx
                    self._switched_at = time.time()
                elif isinstance(last_chunk, str) and '[!!! 流异常中断' in last_chunk and n > 1:
                    self._cur_idx = (idx + 1) % n
                    self._switched_at = time.time()
                    log.warning('MixinSession partial failure, next call -> s%d (%s)', self._cur_idx, self._sessions[self._cur_idx].name)
                return return_val
            if attempt >= self._retries:
                yield last_chunk
                return return_val
            nxt = (base + attempt + 1) % n
            if nxt == base:
                rnd = (attempt + 1) // n
                delay = min(30, self._base_delay * (1.5 ** rnd))
                log.warning('MixinSession %s..., round %d exhausted, retry in %.1fs', last_chunk[:80], rnd, delay)
                time.sleep(delay)
            else:
                log.warning('MixinSession %s..., retry %d/%d (s%d->s%d)', last_chunk[:80], attempt + 1, self._retries, idx, nxt)
