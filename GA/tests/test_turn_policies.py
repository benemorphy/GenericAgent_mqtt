import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.agent.turn_policy import (
    policy_danger_ask_user,
    policy_danger_retry,
    policy_inject_memory,
    policy_plan_limit,
    DEFAULT_TURN_POLICIES,
)

def test_ask_user():
    # policy_danger_ask_user currently always returns '' based on turn rules
    r = policy_danger_ask_user(1, None, "")
    assert r == "", f"Unexpected return: {r!r}"

def test_retry():
    for t in [7, 14, 21]:
        assert policy_danger_retry(t, None, "") != "", f"turn={t} should trigger"
    for t in [1, 3, 5]:
        assert policy_danger_retry(t, None, "") == "", f"turn={t} should not trigger"
    assert policy_danger_retry(7, "plan.md", "") != "", "plan mode should also trigger"

def test_memory():
    for t in [10, 20, 30]:
        assert policy_inject_memory(t, None, "") != "", f"turn={t} should trigger"
    assert policy_inject_memory(5, None, "") == "", "turn=5 should not trigger"

def test_plan_limit():
    r = policy_plan_limit(10, "p.md", "")
    assert "Plan Hint" in r, f"plan turn=10 should hint: {r!r}"
    r = policy_plan_limit(90, "p.md", "")
    assert "Plan Hint" in r, f"plan turn=90 should hint: {r!r}"
    assert policy_plan_limit(10, None, "") == "", "non-plan should skip"

def test_chain():
    from tools.observability.constraint_dashboard import policy_constraint_dashboard
    class FakeHandler:
        constraint_dashboard = None
    policies = [p for p in DEFAULT_TURN_POLICIES if p is not policy_constraint_dashboard]
    n = ""
    for p in policies:
        n += p(65, None, n) or ""
    # Non-plan chain: may not have DANGER but should have at least some content
    # Currently only returns "Plan Hint" in plan mode
    r_plan = ""
    for p in policies:
        r_plan += p(65, "p.md", r_plan) or ""
    assert "Plan Hint" in r_plan, f"plan chain should have Plan Hint: {r_plan!r}"

if __name__ == "__main__":
    for test in [test_ask_user, test_retry, test_memory, test_plan_limit, test_chain]:
        test()
    print("All tests passed")
