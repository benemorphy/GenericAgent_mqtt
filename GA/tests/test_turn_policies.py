import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.turn_policy import (
    policy_danger_ask_user,
    policy_danger_retry,
    policy_inject_memory,
    policy_plan_limit,
    DEFAULT_TURN_POLICIES,
)

def assert_policy(name, condition, msg):
    if not condition:
        print(f"  [FAIL] {name}: {msg}")
        return False
    print(f"  [PASS] {name}")
    return True

def test_ask_user():
    ok = True
    ok &= assert_policy("turn=65触发", policy_danger_ask_user(65, None, "") != "", "")
    ok &= assert_policy("turn=130触发", policy_danger_ask_user(130, None, "") != "", "")
    ok &= assert_policy("turn=1不触发", policy_danger_ask_user(1, None, "") == "", "")
    ok &= assert_policy("plan模式跳过", policy_danger_ask_user(65, "plan.md", "") == "", "")
    if ok: print("  [OK] 危险轮ask_user触发")
    return ok

def test_retry():
    ok = True
    for t in [7, 14, 21]:
        ok &= assert_policy(f"turn={t}触发", policy_danger_retry(t, None, "") != "", "")
    for t in [1, 3, 5]:
        ok &= assert_policy(f"turn={t}不触发", policy_danger_retry(t, None, "") == "", "")
    ok &= assert_policy("plan模式也触发", policy_danger_retry(7, "plan.md", "") != "", "")
    if ok: print("  [OK] 重试警告阈值")
    return ok

def test_memory():
    ok = True
    for t in [10, 20, 30]:
        ok &= assert_policy(f"turn={t}触发", policy_inject_memory(t, None, "") != "", "")
    ok &= assert_policy("turn=5不触发", policy_inject_memory(5, None, "") == "", "")
    if ok: print("  [OK] 记忆注入阈值")
    return ok

def test_plan_limit():
    ok = True
    ok &= assert_policy("plan turn=10提示", "Plan Hint" in policy_plan_limit(10, "p.md", ""), "")
    ok &= assert_policy("plan turn=90上限", "DANGER" in policy_plan_limit(90, "p.md", ""), "")
    ok &= assert_policy("非plan跳过", policy_plan_limit(10, None, "") == "", "")
    if ok: print("  [OK] Plan提示+上限")
    return ok

def test_chain():
    # policy_constraint_dashboard takes (handler, turn, _plan, next_prompt)
    from tools.constraint_dashboard import policy_constraint_dashboard
    class FakeHandler:
        constraint_dashboard = None
    policies = [
        p for p in DEFAULT_TURN_POLICIES
        if p is not policy_constraint_dashboard
    ]
    n = ""
    for p in policies:
        n += p(65, None, n) or ""
    ok = assert_policy("非plan链", "DANGER" in n, "")
    n2 = ""
    for p in policies:
        n2 += p(65, "p.md", n2) or ""
    ok &= assert_policy("plan链跳过DANGER", "DANGER" not in n2, "")
    if ok: print("  [OK] 集成链")
    return ok

if __name__ == "__main__":
    ok = all([test_ask_user(), test_retry(), test_memory(), test_plan_limit(), test_chain()])
    print(f"\n{'全部通过!' if ok else '有失败'}")
