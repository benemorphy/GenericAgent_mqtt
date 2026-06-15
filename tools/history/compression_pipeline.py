"""上下文压缩管线 — CompressorPipeline 4阶段实现

Stage1: DynamicTrigger   — 按token/轮数动态触发
Stage2: LevelSummary     — 3层摘要树（L0/L1/L2）
Stage3: SemanticTrim     — 保留关键数据，裁剪冗余
Stage4: CompressTag      — 插入压缩标记

用法:
    pipeline = CompressionPipeline()
    compressed = pipeline.compress(messages, sess=sess)
"""

import json, time, logging
from typing import Optional

logger = logging.getLogger(__name__)

# ── 工具函数 ──────────────────────────────────────
def _estimate_tokens(text: str) -> int:
    """粗略估测token数（中英文混合）"""
    if not text:
        return 0
    # 中文约1.5 chars/token，英文约4 chars/token
    cn = sum(1 for c in text if '\u4e00' <= c <= '\u9fff')
    en = len(text) - cn
    return int(cn * 1.5 + en / 4)

def _trunc_str(s, max_len=200):
    if not s or len(s) <= max_len:
        return s
    return s[:max_len] + f" ...({len(s)-max_len} chars truncated)"

def _format_tokens(n: int) -> str:
    if n > 1000:
        return f"{n/1000:.1f}K"
    return str(n)

# ── Stage 1: DynamicTrigger ──────────────────────
class DynamicTrigger:
    """动态触发判定器，取代固定interval"""
    
    def __init__(self, 
                 token_threshold: int = 8000,
                 turn_threshold: int = 30,
                 growth_threshold: int = 20):
        self.token_threshold = token_threshold
        self.turn_threshold = turn_threshold
        self.growth_threshold = growth_threshold
        self._last_compress_turn = 0
    
    def should_compress(self, messages: list, turn: int) -> tuple[bool, str]:
        """返回 (是否压缩, 原因)"""
        if not messages:
            return False, "empty"
        
        # 1. token估测
        total_tokens = sum(_estimate_tokens(json.dumps(m, ensure_ascii=False)) 
                          for m in messages)
        if total_tokens > self.token_threshold:
            return True, f"token>{_format_tokens(self.token_threshold)}"
        
        # 2. 轮数
        if turn > self.turn_threshold:
            return True, f"turn>{self.turn_threshold}"
        
        # 3. 增长量
        growth = turn - self._last_compress_turn
        if self._last_compress_turn > 0 and growth > self.growth_threshold:
            return True, f"growth>{self.growth_threshold}"
        
        return False, "under threshold"
    
    def mark_compressed(self, turn: int):
        self._last_compress_turn = turn

# ── Stage 2: LevelSummary ────────────────────────
class LevelSummary:
    """层级摘要器 — 3层压缩级别"""
    
    LEVELS = {
        0: "L0_full",    # 不压缩
        1: "L1_mixed",   # 最近N轮保留，旧轮摘要
        2: "L2_all",     # 全部摘要化
    }
    
    def __init__(self, keep_recent: int = 10, summary_max_len: int = 500):
        self.keep_recent = keep_recent
        self.summary_max_len = summary_max_len
    
    def select_level(self, total_tokens: int, turn: int) -> int:
        """根据token水位选择压缩级别"""
        if total_tokens < 5000 or turn < 15:
            return 0  # L0
        elif total_tokens < 15000 or turn < 40:
            return 1  # L1
        else:
            return 2  # L2
    
    def compress(self, messages: list, level: int) -> list:
        if level == 0:
            return messages
        
        if len(messages) <= self.keep_recent:
            return messages
        
        # 分离system msg
        system_msgs = [m for m in messages if m.get('role') == 'system']
        other_msgs = [m for m in messages if m.get('role') != 'system']
        
        if level == 1:
            # L1: 保留最近N轮，旧轮摘要
            recent = other_msgs[-self.keep_recent:] if self.keep_recent > 0 else []
            old = other_msgs[:-self.keep_recent] if self.keep_recent > 0 else other_msgs
            
            if old:
                # 提取关键信息
                summary_parts = []
                for m in old:
                    role = m.get('role', '?')
                    content = m.get('content', '')
                    if isinstance(content, str) and content:
                        summary_parts.append(f"[{role}]: {_trunc_str(content, 100)}")
                    elif isinstance(content, list):
                        for item in content[:3]:
                            if isinstance(item, dict) and item.get('type') == 'text':
                                summary_parts.append(f"[{role}]: {_trunc_str(item.get('text',''), 100)}")
                
                summary_text = "; ".join(summary_parts)
                if len(summary_text) > self.summary_max_len:
                    summary_text = summary_text[:self.summary_max_len] + "..."
                
                summary_msg = {
                    "role": "system",
                    "content": f"[Context Summary - {len(old)} historical turns]: {summary_text}"
                }
                return system_msgs + [summary_msg] + recent
            
            return system_msgs + recent
        
        else:  # level 2
            # L2: 全部摘要化
            summary_parts = []
            for m in other_msgs:
                role = m.get('role', '?')
                content = m.get('content', '')
                if isinstance(content, str) and content:
                    summary_parts.append(f"[{role}]: {_trunc_str(content, 60)}")
            
            summary_text = "; ".join(summary_parts)
            if len(summary_text) > self.summary_max_len:
                summary_text = summary_text[:self.summary_max_len] + "..."
            
            summary_msg = {
                "role": "system",
                "content": f"[Full Context Summary - {len(other_msgs)} turns]: {summary_text}"
            }
            return system_msgs + [summary_msg]

# ── Stage 3: SemanticTrim ─────────────────────────
class SemanticTrim:
    """语义裁剪 — 保留关键数据，裁剪冗余"""
    
    KEY_PATTERNS = [
        'path', 'file', 'dir', 'line', 'error', 'exception',
        'return', 'result', 'status', 'code', 'pid', 'port',
        'token', 'tier', 'model', 'url', 'endpoint',
    ]
    
    def __init__(self, max_tool_result: int = 300):
        self.max_tool_result = max_tool_result
    
    def trim(self, messages: list) -> list:
        result = []
        for m in messages:
            role = m.get('role')
            content = m.get('content', '')
            
            if role == 'tool' and isinstance(content, str):
                # 工具结果：保留关键行
                lines = content.split('\n')
                key_lines = []
                for line in lines:
                    if any(kw in line.lower() for kw in self.KEY_PATTERNS):
                        key_lines.append(line)
                
                if key_lines:
                    trimmed = '\n'.join(key_lines)
                    if len(trimmed) > self.max_tool_result:
                        trimmed = trimmed[:self.max_tool_result] + f"\n...({len(lines)-len(key_lines)} lines omitted)"
                    result.append({"role": role, "content": trimmed, **{k:v for k,v in m.items() if k not in ('role','content')}})
                else:
                    # 无关键行，截断头部
                    trimmed = '\n'.join(lines[:5])
                    if len(lines) > 5:
                        trimmed += f"\n...({len(lines)-5} lines omitted)"
                    result.append({"role": role, "content": trimmed, **{k:v for k,v in m.items() if k not in ('role','content')}})
            else:
                result.append(m)
        
        return result

# ── Stage 4: CompressTag ──────────────────────────
class CompressTag:
    """压缩标记 — 插入标记让Agent感知"""
    
    def tag(self, messages: list, before_tokens: int, after_tokens: int, 
            reason: str, level: int) -> list:
        reduction = int((1 - after_tokens/max(before_tokens, 1)) * 100)
        tag_msg = {
            "role": "system",
            "content": (
                f"[Context compressed: L{level} | {reason} | "
                f"{_format_tokens(before_tokens)}→{_format_tokens(after_tokens)} "
                f"({reduction}% reduction)]"
            )
        }
        # 插入到第一个非system消息前
        insert_idx = 0
        for i, m in enumerate(messages):
            if m.get('role') != 'system':
                insert_idx = i
                break
        else:
            insert_idx = len(messages)
        
        result = messages[:insert_idx] + [tag_msg] + messages[insert_idx:]
        return result

# ── Pipeline ──────────────────────────────────────
class CompressionPipeline:
    """上下文压缩管线 — 4 stage串联"""
    
    def __init__(self, config: Optional[dict] = None):
        cfg = config or {}
        self.dynamic = DynamicTrigger(
            token_threshold=cfg.get('token_threshold', 8000),
            turn_threshold=cfg.get('turn_threshold', 30),
            growth_threshold=cfg.get('growth_threshold', 20),
        )
        self.summarizer = LevelSummary(
            keep_recent=cfg.get('keep_recent', 10),
            summary_max_len=cfg.get('summary_max_len', 500),
        )
        self.trimmer = SemanticTrim(
            max_tool_result=cfg.get('max_tool_result', 300),
        )
        self.tagger = CompressTag()
        self._call_count = 0
    
    def compress(self, messages: list, sess=None, **kwargs) -> list:
        """执行完整压缩管线"""
        if not messages:
            return messages
        
        self._call_count += 1
        turn = kwargs.get('turn', self._call_count)
        
        # Stage1: 动态判定
        should, reason = self.dynamic.should_compress(messages, turn)
        if not should:
            return messages
        
        before_tokens = sum(_estimate_tokens(json.dumps(m, ensure_ascii=False)) for m in messages)
        before_len = len(messages)
        
        # Stage2: 层级摘要
        total_tokens_est = before_tokens
        level = self.summarizer.select_level(total_tokens_est, turn)
        messages = self.summarizer.compress(messages, level)
        
        # Stage3: 语义裁剪
        messages = self.trimmer.trim(messages)
        
        after_tokens = sum(_estimate_tokens(json.dumps(m, ensure_ascii=False)) for m in messages)
        
        # Stage4: 压缩标记
        messages = self.tagger.tag(messages, before_tokens, after_tokens, reason, level)
        
        self.dynamic.mark_compressed(turn)
        
        logger.info(
            f"[Compression] L{level} | {reason} | "
            f"{before_len}→{len(messages)} msgs | "
            f"{_format_tokens(before_tokens)}→{_format_tokens(after_tokens)}"
        )
        
        return messages
