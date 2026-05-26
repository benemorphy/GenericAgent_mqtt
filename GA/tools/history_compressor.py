"""历史消息压缩器 — 可插拔策略（Phase 1: 提取为类）"""

import json, re
from typing import List, Dict, Any, Optional

try:
    from typing import Protocol
except ImportError:
    Protocol = object


class CompressorBase:
    """压缩器基类接口"""
    name: str = "base"
    
    def compress(self, messages: list, sess=None, **kwargs) -> list:
        """压缩消息历史，返回压缩后的列表
        
        Args:
            messages: 消息列表
            sess: session对象（可提供cut_msg_interval等配置）
            **kwargs: 覆盖默认参数（keep_recent, max_len, force, interval）
        """
        raise NotImplementedError


class DefaultCompressor(CompressorBase):
    """默认压缩器 — 行为完全等价于当前 compress_history_tags"""
    name = "default"
    
    def __init__(self):
        self._call_counter = 0
    
    def compress(self, messages, sess=None, keep_recent=None, max_len=None, 
                 force=False, interval=None):
        """等价于 compress_history_tags(messages, ...)"""
        self._call_counter += 1
        if force:
            self._call_counter = 0
        
        # 从sess或参数中读取配置
        if interval is None:
            interval = getattr(sess, 'cut_msg_interval', 5) if sess else 5
        if keep_recent is None:
            keep_recent = 10
        if max_len is None:
            max_len = 800
        
        if self._call_counter % interval != 0:
            return messages
        
        _before = sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)
        _pats = {tag: re.compile(rf'(<{tag}>)([\s\S]*?)(</{tag}>)') 
                 for tag in ('thinking', 'think', 'tool_use', 'tool_result')}
        _hist_pat = re.compile(r'<(history|key_info|earlier_context)>[\s\S]*?</\1>')
        
        def _trunc_str(s):
            return s[:max_len//2] + '\n...[Truncated]...\n' + s[-max_len//2:] \
                if isinstance(s, str) and len(s) > max_len else s
        
        def _trunc(text):
            text = _hist_pat.sub(lambda m: f'<{m.group(1)}>[...]</{m.group(1)}>', text)
            for pat in _pats.values():
                text = pat.sub(lambda m: m.group(1) + _trunc_str(m.group(2)) + m.group(3), text)
            return text
        
        for i, msg in enumerate(messages):
            if i >= len(messages) - keep_recent:
                break
            c = msg['content']
            if isinstance(c, str):
                msg['content'] = _trunc(c)
            elif isinstance(c, list):
                for b in c:
                    if not isinstance(b, dict):
                        continue
                    t = b.get('type')
                    if t == 'text' and isinstance(b.get('text'), str):
                        b['text'] = _trunc(b['text'])
                    elif t == 'tool_result':
                        tc = b.get('content')
                        if isinstance(tc, str):
                            b['content'] = _trunc_str(tc)
                        elif isinstance(tc, list):
                            for sub in tc:
                                if isinstance(sub, dict) and sub.get('type') == 'text':
                                    sub['text'] = _trunc_str(sub.get('text'))
                    elif t == 'tool_use' and isinstance(b.get('input'), dict):
                        for k, v in b['input'].items():
                            b['input'][k] = _trunc_str(v)
        
        print(f"[Cut] {_before} -> {sum(len(json.dumps(m, ensure_ascii=False)) for m in messages)}")
        return messages
