#!/usr/bin/env python
"""GA Heartbeat 自动记忆提纯 (P3)

三层管道:
  原始事件 → HeartbeatSummary (压缩编码)
               ↓
         HeartbeatInsight (模式提取)
               ↓
         HeartbeatCombinedMemory (合并写入 L2 记忆)

集成:
  from tools.heartbeat_memory import hb
  await hb.heartbeat(session_state)
"""
import os, json, time, threading, asyncio
from pathlib import Path
from typing import Optional, List, Any
from datetime import datetime

from tools.memory_types import HeartbeatSummary, HeartbeatInsight, HeartbeatCombinedMemory

_MEMORY_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "memory")

class HeartbeatMemorySystem:
    """基于心跳的自动记忆管理"""

    def __init__(self, memory_dir: str = None):
        self.memory_dir = memory_dir or _MEMORY_DIR
        self.history: List[HeartbeatSummary] = []
        self.insights: List[HeartbeatInsight] = []
        self.last_summary: Optional[HeartbeatSummary] = None
        self._hb_count = 0
        self._lock = threading.Lock()
        os.makedirs(os.path.join(self.memory_dir, ".heartbeat"), exist_ok=True)

    async def heartbeat(self, session_state: dict = None) -> HeartbeatCombinedMemory:
        """完整心跳: 提取→摘要→洞察→合并"""
        events = self._extract_events(session_state or {})
        summary = await self._summarize(events)
        insights = await self._extract_insights(summary)
        combined = self._consolidate(summary, insights)
        self._sync_to_global_memory(combined)
        return combined

    def _extract_events(self, state: dict) -> list:
        """提取关键事件"""
        events = []
        for key in ["tool_calls", "results", "errors", "prompt"]:
            val = state.get(key)
            if val:
                if isinstance(val, list):
                    events.extend(str(v)[:200] for v in val)
                else:
                    events.append(str(val)[:200])
        return events

    async def _summarize(self, events: list) -> HeartbeatSummary:
        """生成摘要 (同步版: 从现有tracer数据构造)"""
        with self._lock:
            self._hb_count += 1
            summary = HeartbeatSummary(
                timestamp=time.time(),
                session_id=f"hb-{self._hb_count}",
                key_events=events[:20],
                turn_count=len(events),
                summary_text=f"HB#{self._hb_count}: {len(events)} events"
            )
            self.history.append(summary)
            self.last_summary = summary
        return summary

    async def _extract_insights(self, summary: HeartbeatSummary) -> List[HeartbeatInsight]:
        """从当前摘要+历史中提取洞察"""
        insights = []
        if len(self.history) >= 3:
            recent = self.history[-3:]
            errors = sum(1 for h in recent if h.error_count > 0)
            if errors >= 2:
                insights.append(HeartbeatInsight(
                    timestamp=time.time(), category="anomaly",
                    title="高频错误模式",
                    description=f"最近{len(recent)}次心跳中{errors}次含错误",
                    confidence=0.6
                ))
        return insights

    def _consolidate(self, summary: HeartbeatSummary, insights: List[HeartbeatInsight]) -> HeartbeatCombinedMemory:
        """合并摘要+洞察为L2记忆"""
        content_parts = [f"HB#{self._hb_count} @ {datetime.fromtimestamp(summary.timestamp).strftime('%Y-%m-%d %H:%M')}"]
        if summary.key_events:
            content_parts.append(f"事件: {summary.key_events[:5]}")
        for ins in insights:
            content_parts.append(f"[{ins.category}] {ins.title}: {ins.description}")
        return HeartbeatCombinedMemory(
            content="\n".join(content_parts),
            created_at=summary.timestamp,
            tags=["heartbeat", f"hb{self._hb_count}"],
            importance=min(1.0, 0.3 + len(insights) * 0.2)
        )

    def _sync_to_global_memory(self, combined: HeartbeatCombinedMemory):
        """写入L2记忆 (global_mem.txt)"""
        path = os.path.join(self.memory_dir, "global_mem.txt")
        entry = combined.to_global_mem_format()
        try:
            with open(path, "r+", encoding="utf-8") as f:
                old = f.read()
                f.seek(0)
                f.write(old + entry)
        except FileNotFoundError:
            with open(path, "w", encoding="utf-8") as f:
                f.write("# [Global Memory - L2]\n" + entry)

    def stats(self) -> dict:
        return {"total_heartbeats": self._hb_count, "insights": len(self.insights),
                "history_len": len(self.history)}

hb = HeartbeatMemorySystem()
