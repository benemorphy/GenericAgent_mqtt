"""
LLM Session 层 — 会话管理与多模型回退
提取自 llmcore.py Phase 1：保持对 llmcore 的单向依赖，后续逐步解耦。
"""

import time
import copy
import hashlib
import json
from collections import OrderedDict
from tools.utils.retry_utils import retry_stream
from tools.utils.logger import log
from tools.semantic_cache import get_semantic_cache

# 本地响应缓存 (LRU, 最多 200 条)
_RESP_CACHE = OrderedDict()
_RESP_CACHE_MAX = 200
_RESP_CACHE_STATS = {'hit': 0, 'miss': 0, 'store': 0, 'evict': 0}
# 语义缓存实例 (方案A+B融合)
_SEMANTIC_CACHE = get_semantic_cache()
# 分层缓存统计
_HIER_CACHE_STATS = {'hit': 0, 'miss': 0, 'partial': 0}

def _cache_key(messages, system=None, model=None) -> str:
    raw = json.dumps({'m': messages, 's': system, 'md': model}, sort_keys=True, ensure_ascii=False, default=str)
    return hashlib.sha256(raw.encode('utf-8')).hexdigest()[:24]

# ── P2: 分层缓存键 ──

def _get_last_user_message(messages):
    """提取最后一条 user message 的内容."""
    for msg in reversed(messages):
        if isinstance(msg, dict) and msg.get('role') == 'user':
            content = msg.get('content', '')
            return content if isinstance(content, str) else str(content)
    return ''

def _extract_pattern(text):
    """将具体值替换为占位符, 提取意图模式."""
    import re
    text = re.sub(r'\b\d+\b', '{num}', text)
    text = re.sub(r'["\'][^"\']*["\']', '{str}', text)
    text = re.sub(r'[a-zA-Z]:\\[^\s,;)]+', '{path}', text)
    text = re.sub(r'[0-9a-f]{8,}', '{hex}', text)
    return text.strip()

def _hierarchical_cache_key(messages, system=None, model=None) -> str:
    """分层缓存键: system_key:intent_key:context_key"""
    system_key = hashlib.sha256(
        json.dumps({'s': system, 'md': model}, sort_keys=True).encode()
    ).hexdigest()[:16]
    last_user_msg = _get_last_user_message(messages)
    intent_pattern = _extract_pattern(last_user_msg)
    intent_key = hashlib.sha256(intent_pattern.encode()).hexdigest()[:16]
    context_key = hashlib.sha256(
        json.dumps({'m': messages[-10:]}, sort_keys=True).encode()
    ).hexdigest()[:16]
    return f"{system_key}:{intent_key}:{context_key}"

# P3: 模式预计算缓存
PRECOMPUTED_CACHE = {
    "code_run_success": "代码执行成功，输出如下:\n{output}",
    "file_read_first_N": "已读取文件前{N}行:\n{content}",
    "search_no_results": "未找到匹配结果",
    "tool_call_error": "工具调用出错，请检查参数后重试",
}

def _check_precomputed_cache(messages):
    """检查消息是否命中模式预计算缓存. 返回 (是否命中, 响应元组)."""
    last_user = _get_last_user_message(messages).lower()
    for key, template in PRECOMPUTED_CACHE.items():
        if key.replace('_', ' ') in last_user or key in last_user:
            return True, (template,)
    return False, None

def _cache_stats_str() -> str:
    s = _RESP_CACHE_STATS
    total = s['hit'] + s['miss']
    rate = f"{s['hit']/total*100:.1f}%" if total else "N/A"
    sem_stats = _SEMANTIC_CACHE.get_stats_str() if _SEMANTIC_CACHE else ''
    h = _HIER_CACHE_STATS
    hier_stats = f"hier_hit={h['hit']} hier_partial={h['partial']}"
    return f"hit={s['hit']} miss={s['miss']} rate={rate} store={s['store']} evict={s['evict']} size={len(_RESP_CACHE)} | sem:{sem_stats} | {hier_stats}"

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
        msgs, sys_prompt = (args[0] if args else kwargs.get('messages', [])), getattr(self, 'system', None)
        # P3: 模式预计算缓存 (最快, 完全跳过 LLM)
        try:
            p3_hit, p3_resp = _check_precomputed_cache(msgs)
            if p3_hit:
                log.info('PRECOMPUTED CACHE HIT session=%s', self._sessions[base].name)
                for ch in p3_resp:
                    yield ch
                return p3_resp[-1] if p3_resp else []
        except Exception:
            pass
        # 计算缓存键
        try:
            ck = _cache_key(msgs, sys_prompt, self.model)
            hk = _hierarchical_cache_key(msgs, sys_prompt, self.model)
        except Exception:
            ck = None
            hk = None
        # 检查精确缓存 (SHA256 hash)
        if ck is not None and ck in _RESP_CACHE:
            _RESP_CACHE_STATS['hit'] += 1
            log.info('CACHE HIT  key=%s session=%s | %s', ck, self._sessions[base].name, _cache_stats_str())
            _RESP_CACHE.move_to_end(ck)
            for ch in _RESP_CACHE[ck]:
                yield ch
            return _RESP_CACHE[ck][-1] if _RESP_CACHE[ck] else []
        if ck is not None:
            _RESP_CACHE_STATS['miss'] += 1
            log.info('CACHE MISS key=%s session=%s | %s', ck, self._sessions[base].name, _cache_stats_str())
        # P2: 分层缓存 (意图级重用)
        if hk is not None:
            hk_prefix = ':'.join(hk.split(':')[:2])
            for existing_key in list(_RESP_CACHE.keys()):
                if existing_key.startswith(hk_prefix):
                    _HIER_CACHE_STATS['hit'] += 1
                    log.info('HIERARCHICAL CACHE HINT key=%s session=%s | %s', existing_key, self._sessions[base].name, _cache_stats_str())
                    _RESP_CACHE.move_to_end(existing_key)
                    break
        # 检查语义缓存 (方案A+B融合)
        sem_result = None
        if _SEMANTIC_CACHE is not None:
            try:
                sem_result = _SEMANTIC_CACHE.lookup(msgs, sys_prompt, self.model)
            except Exception as e:
                log.warning('SEM CACHE lookup failed (safe fallback): %s', e)
        if sem_result is not None:
            cached_chunks, sim = sem_result
            # 检测卡住响应（工具不可用/放弃模式）— 跳过缓存，打破循环
            _stuck = False
            if cached_chunks:
                _flat = "".join(cached_chunks).lower()
                _stuck = bool(re.search(
                    r'(?:web_search|搜索|查找|search).{0,20}(?:不可用|不能用|无法|not available|cannot find)'
                    r'|(?:not available|cannot find|找不到|无法|没有).{0,20}(?:tool|工具|搜索|search)'
                    r'|(?:我无法|我不能|没有办法).{0,20}(?:搜索|查找|执行)'
                    r'|让我查找可用的\w+工具',
                    _flat
                ))
            if _stuck:
                log.info('SEM CACHE SKIP (stuck) sim=%.3f session=%s | %s', sim, self._sessions[base].name, _cache_stats_str())
                # 移除此条目的缓存避免循环
                try:
                    _SEMANTIC_CACHE.entries[:] = [e for e in _SEMANTIC_CACHE.entries if e[2] != cached_chunks]
                except Exception:
                    pass
            else:
                log.info('SEM CACHE HIT sim=%.3f session=%s | %s', sim, self._sessions[base].name, _cache_stats_str())
                for ch in cached_chunks:
                    yield ch
                return cached_chunks[-1] if cached_chunks else []
        for attempt in range(self._retries + 1):
            idx = (base + attempt) % n
            gen = self._orig_raw_asks[idx](*args, **kwargs)
            log.info('MixinSession using session (%s)', self._sessions[idx].name)
            last_chunk = None
            return_val = []
            yielded = False
            collected = []  # 收集流式chunks用于缓存
            try:
                while True:
                    chunk = next(gen)
                    last_chunk = chunk
                    collected.append(chunk)
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
                # 缓存成功响应 (exact key + hierarchical key 双写)
                if ck is not None and not is_err:
                    _RESP_CACHE[ck] = tuple(collected)
                    _RESP_CACHE_STATS['store'] += 1
                    if hk is not None and hk != ck:
                        _RESP_CACHE[hk] = tuple(collected)
                    while len(_RESP_CACHE) > _RESP_CACHE_MAX:
                        _RESP_CACHE.popitem(last=False)
                # 语义缓存存储 (即使exact miss也尝试存)
                if _SEMANTIC_CACHE is not None and not is_err and collected:
                    try:
                        msgs_for_sem = msgs  # use already extracted msgs
                        _SEMANTIC_CACHE.store(msgs_for_sem, sys_for_sem, model_for_sem, tuple(collected))
                    except Exception as e:
                        log.warning('SEM CACHE store failed (safe fallback): %s', e)
                        _RESP_CACHE_STATS['evict'] += 1
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
