"""
Constraint Dashboard — 约束状态感知系统。

让Agent在执行中感知自己的"预算状态"：
  失败次数、工具调用量、时间消耗 → 行为自我调节

基于 CoStrict / INTENT 研究的 "budget awareness" 理念。
用法:
    from tools.constraint_dashboard import ConstraintDashboard, policy_constraint_dashboard
    # 在 handler 上初始化
    handler._constraint_dashboard = ConstraintDashboard()
    # 在 turn_end_callback 中更新
    handler._constraint_dashboard.update(tool_calls, exit_reason)
    # policy_constraint_dashboard 会自动从 handler 读取并注入仪表盘文本
"""

import time
from dataclasses import dataclass, field


@dataclass
class ConstraintDashboard:
    """约束仪表盘 — 跟踪任务级资源消耗

    属性:
        start_time: 任务开始时间戳 (首次update时设置)
        tool_calls_total: 累计工具调用次数
        tool_calls_this_turn: 本轮工具调用次数
        fail_count: 累计失败/错误次数
        max_fails: 最大允许失败次数 (默认3，与3-failure规则一致)
        max_tool_calls_per_task: 单任务工具调用上限 (默认20)
        timeout: 任务超时秒数 (默认300s)
        last_turn_time: 上一轮结束时间
    """
    start_time: float = 0.0
    tool_calls_total: int = 0
    tool_calls_this_turn: int = 0
    fail_count: int = 0
    max_fails: int = 3
    max_tool_calls_per_task: int = 20
    timeout: float = 300.0
    last_turn_time: float = 0.0

    def __post_init__(self):
        if not self.start_time:
            self.start_time = time.time()
            self.last_turn_time = self.start_time

    def update(self, tool_calls: list, exit_reason: str = ""):
        """在每轮结束时更新计数器

        Args:
            tool_calls: 本轮调用的工具列表
            exit_reason: 退出原因 ('tool_use', 'end_turn', 'error' 等)
        """
        now = time.time()
        if not self.start_time:
            self.start_time = now

        # 工具调用计数
        self.tool_calls_this_turn = len(tool_calls) if tool_calls else 0
        self.tool_calls_total += self.tool_calls_this_turn

        # 失败检测: 空响应/错误退出
        if exit_reason in ('error', 'max_tokens', 'empty_response'):
            self.fail_count += 1

        self.last_turn_time = now

    @property
    def elapsed(self) -> float:
        """已用时间 (秒)"""
        return time.time() - self.start_time

    @property
    def remaining_time(self) -> float:
        """剩余时间 (秒)"""
        return max(0.0, self.timeout - self.elapsed)

    @property
    def fail_budget_remaining(self) -> int:
        """剩余失败预算"""
        return self.max_fails - self.fail_count

    @property
    def is_budget_exhausted(self) -> bool:
        """是否已耗尽预算"""
        return self.fail_budget_remaining <= 0

    def format_report(self, turn: int, is_plan_mode: bool = False) -> str:
        """生成可读的仪表盘报告，注入到下一轮 prompt"""
        elapsed_s = int(self.elapsed)
        elapsed_str = f"{elapsed_s // 60}m{elapsed_s % 60}s"
        remaining_s = int(self.remaining_time)
        remaining_str = f"{remaining_s // 60}m{remaining_s % 60}s"

        # 阈值警告
        warnings = []
        if self.fail_budget_remaining <= 1:
            warnings.append("失败预算即将耗尽！")
        if self.tool_calls_total >= self.max_tool_calls_per_task * 0.8:
            warnings.append(f"工具调用接近上限 ({self.tool_calls_total}/{self.max_tool_calls_per_task})")
        if self.remaining_time < 60:
            warnings.append("时间预算即将耗尽！")

        warn_str = f" ⚠ {' | '.join(warnings)}" if warnings else ""

        return (
            f"\n[CONSTRAINT DASHBOARD]{warn_str}"
            f"\n  ├─ 轮次: #{turn}"
            f"\n  ├─ 失败预算: {self.fail_count}/{self.max_fails}"
            f"\n  ├─ 工具调用: {self.tool_calls_total}次 (本轮: {self.tool_calls_this_turn})"
            f"\n  ├─ 时间: {elapsed_str} / {remaining_str}"
            f"\n  └─ 模式: {'Plan' if is_plan_mode else 'Normal'}"
        )


def policy_constraint_dashboard(handler, turn, _plan, next_prompt):
    """Turn policy: 从handler读取约束仪表盘并注入

    签名兼容 tools.turn_policy 的 _needs_handler 检测。
    """
    cs = getattr(handler, '_constraint_dashboard', None)
    if cs is None:
        return ""
    # 每3轮注入一次，避免过度刷屏
    if turn > 0 and turn % 3 != 0:
        return ""
    return cs.format_report(turn, bool(_plan))
