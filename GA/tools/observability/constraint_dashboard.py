"""
Constraint Dashboard — 约束状态感知系统。

让Agent在执行中感知自己的"预算状态"：
  失败次数、工具调用量、时间消耗 → 行为自我调节

基于 CoStrict / INTENT 研究的 "budget awareness" 理念。
用法:
    from tools.observability.constraint_dashboard import ConstraintDashboard, policy_constraint_dashboard
    # 在 handler 上初始化
    handler._constraint_dashboard = ConstraintDashboard()
    # 在 turn_end_callback 中更新
    handler._constraint_dashboard.update(tool_calls, exit_reason)
    # policy_constraint_dashboard 会自动从 handler 读取并注入仪表盘文本
"""

import time
from dataclasses import dataclass, field


@dataclass
class CuriositySignal:
    """好奇心信号 — 感知中触发的"想知道什么"

    type:
        anomaly:    预期vs实际不符 (如文件大小突变)
        pattern:    发现重复/模式 (如文件名相似)
        new:        发现新事物 (如从未见过的文件)
        missing:    发现缺失 (如之前存在的文件消失了)
        change:     发现变化 (如文件内容被修改过)
        connection: 发现跨域关联 (如两个不同领域的信息相似)
    """
    type: str = "anomaly"
    source: str = ""        # 哪个感知工具产生的
    target: str = ""        # 触发好奇的对象
    reason: str = ""        # 为什么好奇
    severity: float = 0.5   # 0-1, 好奇强度
    context: dict = field(default_factory=dict)  # 额外上下文


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
    # 好奇心追踪
    curiosity_signals: list = field(default_factory=list)  # 待探索的好奇信号
    curiosity_budget: int = 3                               # 每任务最多3个活跃好奇标记
    # CDE 好奇心预算管理 (动态衰减)
    max_curiosity_budget: int = 3         # 初始好奇心预算上限 (CDE: max_budget)
    curiosity_decay_rate: float = 0.85    # 每轮衰减系数 (CDE: decay_rate, 越接近1衰减越慢)
    task_turn_count: int = 0              # 任务已执行轮次 (CDE: task_count)

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
            # CDE: 失败时重置好奇心预算 (新探索机会)
            self.reset_curiosity_budget()

        # CDE: 每轮递增轮次 (用于好奇心预算衰减)
        self.task_turn_count += 1

        self.last_turn_time = now

    def register_curiosity(self, signal: 'CuriositySignal'):
        """注册一个好奇心信号 (受CDE预算约束)

        预算 = max_budget * decay_rate ^ task_turn_count (动态衰减)
        超过预算的低优先级信号会被自动丢弃。
        失败时预算重置 (reset_curiosity_budget)。

        Returns:
            bool: 是否成功注册
        """
        budget = self.curiosity_budget_remaining
        # 重复检查: 相同target和reason不重复注册
        for existing in self.curiosity_signals:
            if existing.target == signal.target and existing.reason == signal.reason:
                return False
        # CDE预算检查: 使用动态衰减后的预算
        if len(self.curiosity_signals) >= budget:
            # 替换最低优先级的信号
            min_sig = min(self.curiosity_signals, key=lambda s: s.severity)
            if signal.severity > min_sig.severity:
                self.curiosity_signals.remove(min_sig)
                self.curiosity_signals.append(signal)
                return True
            return False
        self.curiosity_signals.append(signal)
        return True

    @property
    def pending_curiosities(self) -> int:
        """待探索的好奇信号数量"""
        return len(self.curiosity_signals)

    @property
    def high_priority_curiosities(self) -> list:
        """高优先级(severity>=0.7)的好奇信号"""
        return [s for s in self.curiosity_signals if s.severity >= 0.7]

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

    @property
    def curiosity_budget_remaining(self) -> int:
        """CDE动态好奇心预算: max_budget * decay_rate ^ task_turn_count
        
        随轮次增加而递减，鼓励Agent在任务初期探索、后期利用。
        最低为1 (至少保留一个好奇心标记)。
        """
        raw = self.max_curiosity_budget * (self.curiosity_decay_rate ** self.task_turn_count)
        return max(1, round(raw))

    def reset_curiosity_budget(self):
        """CDE: 失败时重置好奇心预算 (新探索机会)
        
        通常由 update() 在检测到失败时自动调用。
        """
        self.task_turn_count = 0

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

        # 好奇心状态 (含CDE预算信息)
        pending = self.pending_curiosities
        high_pri = self.high_priority_curiosities
        cde_budget = self.curiosity_budget_remaining
        curiosity_str = ""
        if pending > 0:
            curiosity_str = f"\n  ├─ 感知好奇: {pending}个待探索 (CDE预算:{cde_budget})"
            if high_pri:
                curiosity_str += f" ({len(high_pri)}个高优先级)"
        else:
            curiosity_str = f"\n  ├─ 好奇心预算: {cde_budget}/{self.max_curiosity_budget} (CDE衰减)"
        if self.curiosity_signals:
            # 显示最新的高优好奇心原因
            top_signals = sorted(self.curiosity_signals, key=lambda s: s.severity, reverse=True)[:2]
            for sig in top_signals:
                short_reason = sig.reason[:60] if len(sig.reason) > 60 else sig.reason
                curiosity_str += f"\n  │   - [{sig.type}] {short_reason}"

        return (
            f"\n[CONSTRAINT DASHBOARD]{warn_str}"
            f"\n  ├─ 轮次: #{turn}"
            f"\n  ├─ 失败预算: {self.fail_count}/{self.max_fails}"
            f"\n  ├─ 工具调用: {self.tool_calls_total}次 (本轮: {self.tool_calls_this_turn})"
            f"\n  ├─ 时间: {elapsed_str} / {remaining_str}"
            f"{curiosity_str}"
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
