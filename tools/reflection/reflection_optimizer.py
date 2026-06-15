#!/usr/bin/env python
"""GA 反思优化器 (P2 Phase2: ReflectionOptimizer)

基于执行轨迹的反思式优化 - 分析得失 → 提取模式 → 生成改进建议。

用法:
    from tools.reflection.reflection_optimizer import optimizer
    reflection = optimizer.reflect_on_turn(turn)
    patterns = optimizer.extract_patterns(history)
    suggestion = optimizer.generate_improvement(pattern)
"""
import json
import os
import re
import sys
import time
from typing import Optional
from dataclasses import dataclass, field
from collections import Counter, defaultdict

# LLM调用封装 (使用ga或直接LLM)
_LLM_AVAILABLE = False
try:
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    os.environ.setdefault("GA_ROOT", os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from app.engine.ai.ga_provider import ga as _ga
    _LLM_AVAILABLE = True
except ImportError:
    _ga = None


@dataclass
class Reflection:
    """单次执行的反思分析"""
    turn_id: str
    score: float = 0.0  # 0-1, 整体评价
    strengths: list = field(default_factory=list)
    weaknesses: list = field(default_factory=list)
    suggestions: list = field(default_factory=list)
    raw_analysis: str = ""


@dataclass
class Pattern:
    """从历史中提取的执行模式"""
    pattern_id: str
    description: str
    occurrences: int = 1
    success_rate: float = 0.5
    examples: list = field(default_factory=list)
    category: str = "unknown"  # tool_usage | prompt_strategy | error_recovery


@dataclass
class Suggestion:
    """改进建议"""
    target: str  # prompt | tool | workflow
    description: str
    priority: int = 1  # 1-5
    impact: str = "medium"


_REFLECTION_PROMPT = """分析以下 Agent 执行轨迹, 给出反思评价:

Tool Calls: {tool_calls}
Results (前3个): {results[:3]}
Error: {error}
Duration: {duration_ms}ms
Reward: {reward}/1.0

请按以下格式输出:
评分: [0-1]
优势: [列举1-3个]
劣势: [列举1-3个]
建议: [列举1-3个改进建议]"""

_PATTERN_PROMPT = """分析以下 {n} 条执行轨迹, 提取通用的成功/失败模式:

轨迹摘要:
{summaries}

请找出:
1. 最常见的成功模式 (什么做法总是有效)
2. 最常见的失败模式 (什么做法经常出错)
3. 改进策略 (如何绕过失败模式)

格式:
成功模式: [描述] (出现 {n} 次)
失败模式: [描述] (出现 {n} 次)
改进策略: [具体建议]"""


class ReflectionOptimizer:
    """反射式优化器"""
    
    def reflect_on_turn(self, turn) -> Reflection:
        """分析单次执行得失"""
        tool_calls = getattr(turn, 'tool_calls', [])
        results = getattr(turn, 'results', [])
        error = getattr(turn, 'error', None)
        prompt = getattr(turn, 'prompt', '')[:200]
        duration = getattr(turn, 'duration_ms', 0)
        reward = getattr(turn, 'reward', 0)
        
        # 启发式分析 (无LLM)
        ref = Reflection(turn_id=getattr(turn, 'turn_id', 'unknown'))
        ref.score = reward
        
        if error:
            ref.weaknesses.append(f"错误: {error[:100]}")
            ref.score = max(0, ref.score - 0.3)
        
        if duration > 30000:  # >30s
            ref.weaknesses.append(f"执行耗时 {duration/1000:.1f}s")
            ref.score = max(0, ref.score - 0.1)
        
        if tool_calls:
            tool_names = [t.get('name', str(t)) for t in tool_calls[:5]]
            ref.strengths.append(f"调用了 {len(tool_calls)} 个工具: {', '.join(tool_names[:3])}")
        
        # LLM深度分析
        if _LLM_AVAILABLE and _ga:
            try:
                tc_str = json.dumps(tool_calls[:5], ensure_ascii=False)[:1000]
                res_str = json.dumps([str(r)[:100] for r in (results or [])[:3]], ensure_ascii=False)[:500]
                llm_prompt = _REFLECTION_PROMPT.format(
                    tool_calls=tc_str, results=res_str,
                    error=error or "无", duration_ms=duration, reward=reward
                )
                result = _ga.generate_plan(llm_prompt, "反思分析", "agent")
                raw = str(result) if result else ""
                ref.raw_analysis = raw[:500]
                
                # 从LLM返回中提取评分
                score_match = re.search(r'评分[：:]\s*([0-9.]+)', raw)
                if score_match:
                    ref.score = float(score_match.group(1))
                
                # 提取建议
                for match in re.finditer(r'建议[：:]\s*(.+?)(?:\n|$)', raw):
                    ref.suggestions.append(match.group(1).strip())
                    
            except Exception as e:
                ref.raw_analysis = f"[LLM分析跳过] {e}"
        
        return ref
    
    def extract_patterns(self, history: list, min_occurrences: int = 2) -> list[Pattern]:
        """从历史中提取成功/失败模式"""
        if not history:
            return []
        
        # 基于启发式的模式提取
        patterns = []
        error_counter = Counter()
        tool_counter = Counter()
        
        for turn in history:
            if getattr(turn, 'error', None):
                error_key = getattr(turn, 'error', '')[:50]
                error_counter[error_key] += 1
            for tc in getattr(turn, 'tool_calls', []) or []:
                name = tc.get('name', '') if isinstance(tc, dict) else str(tc)
                if name:
                    tool_counter[name] += 1
        
        for err, count in error_counter.most_common(5):
            if count >= min_occurrences:
                patterns.append(Pattern(
                    pattern_id=f"err_{len(patterns)}",
                    description=f"重复错误: {err[:60]}",
                    occurrences=count,
                    success_rate=0.0,
                    category="error_recovery"
                ))
        
        for tool, count in tool_counter.most_common(3):
            patterns.append(Pattern(
                pattern_id=f"tool_{len(patterns)}",
                description=f"高频工具: {tool}",
                occurrences=count,
                success_rate=0.8,
                category="tool_usage"
            ))
        
        # LLM深度模式提取 (如有足够历史)
        if _LLM_AVAILABLE and _ga and len(history) >= 3:
            try:
                summaries = []
                for h in history[:10]:
                    err = getattr(h, 'error', None) or "成功"
                    calls = len(getattr(h, 'tool_calls', []) or [])
                    summaries.append(f"[{getattr(h,'turn_id','?')}] {calls}工具调用, 结果:{err[:60]}")
                
                llm_prompt = _PATTERN_PROMPT.format(n=len(history), summaries="\n".join(summaries))
                result = _ga.generate_plan(llm_prompt, "模式提取", "agent")
                raw = str(result) if result else ""
                
                for match in re.finditer(r'(成功模式|失败模式)[：:]\s*(.+?)(?:\(出现|\n|$)', raw):
                    cat = "success" if "成功" in match.group(1) else "failure"
                    patterns.append(Pattern(
                        pattern_id=f"llm_{len(patterns)}",
                        description=match.group(2).strip()[:80],
                        occurrences=1,
                        success_rate=0.9 if cat == "success" else 0.1,
                        category=f"pattern_{cat}"
                    ))
            except Exception as e:
                pass
        
        return patterns
    
    def generate_improvement(self, pattern: Pattern) -> Optional[Suggestion]:
        """生成具体的改进建议"""
        if pattern.category == "error_recovery" and pattern.success_rate < 0.3:
            return Suggestion(
                target="workflow",
                description=f"添加{pattern.description[:40]}的自动重试/错误处理",
                priority=4,
                impact="high"
            )
        elif pattern.category == "tool_usage" and pattern.occurrences > 5:
            return Suggestion(
                target="prompt",
                description=f"将高频工具 {pattern.description[6:30]} 的用法固化到 system prompt",
                priority=3,
                impact="medium"
            )
        elif pattern.category.startswith("pattern_"):
            return Suggestion(
                target="workflow" if "failure" in pattern.category else "prompt",
                description=pattern.description[:60],
                priority=2,
                impact="medium"
            )
        return None


# 全局单例
optimizer = ReflectionOptimizer()


if __name__ == "__main__":
    # 测试
    from tools.observability.tracer import tracer
    hist = tracer.recent(10)
    print(f"取到 {len(hist)} 条历史轨迹")
    
    if hist:
        ref = optimizer.reflect_on_turn(hist[0])
        print(f"\n反思: score={ref.score}")
        print(f"  优势: {ref.strengths[:2]}")
        print(f"  劣势: {ref.weaknesses[:2]}")
    
    patterns = optimizer.extract_patterns(hist)
    print(f"\n模式提取: {len(patterns)} 个模式")
    for p in patterns:
        sug = optimizer.generate_improvement(p)
        print(f"  [{p.category}] {p.description[:40]}")
        if sug:
            print(f"    → 建议: {sug.description[:50]}")
