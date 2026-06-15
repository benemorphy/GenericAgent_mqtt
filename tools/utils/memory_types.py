#!/usr/bin/env python
"""GA 记忆类型定义 (P3: Heartbeat 自动记忆提纯)

HeartbeatSummary / HeartbeatInsight / HeartbeatCombinedMemory
"""
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Any
from datetime import datetime


@dataclass
class HeartbeatSummary:
    """心跳摘要: 编码原始事件为结构化记忆"""
    timestamp: float  # unix时间戳
    session_id: str
    key_events: List[str] = field(default_factory=list)
    tool_usage: List[str] = field(default_factory=list)
    llm_model: str = ""
    turn_count: int = 0
    error_count: int = 0
    avg_reward: float = 0.0
    summary_text: str = ""

    def to_dict(self):
        return asdict(self)

    @classmethod
    def from_dict(cls, d):
        return cls(**d)


@dataclass
class HeartbeatInsight:
    """心跳洞察: 从多个摘要中提取的模式/趋势/反常"""
    timestamp: float
    category: str  # pattern | trend | anomaly | learning
    title: str
    description: str
    confidence: float = 0.0  # 0-1
    related_events: List[str] = field(default_factory=list)
    source_ids: List[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


@dataclass  
class HeartbeatCombinedMemory:
    """合并记忆: 写入L2的最终记忆单元"""
    level: str = "L2"  # L2 | insight
    content: str = ""
    source: str = "heartbeat"
    created_at: float = 0.0
    tags: List[str] = field(default_factory=list)
    importance: float = 0.5  # 0-1

    def to_global_mem_format(self) -> str:
        ts = datetime.fromtimestamp(self.created_at).strftime("%Y-%m-%d %H:%M")
        return f"\n## [{self.source.upper()}]\n# {self.tags_str()}\n{self.content}\n"

    def tags_str(self) -> str:
        return " | ".join(self.tags)
