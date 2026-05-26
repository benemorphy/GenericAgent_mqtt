#!/usr/bin/env python3
"""
failure_tracker — 失败驱动学习工具

功能:
  - 记录每次失败的详细上下文
  - 检测重复失败模式 (同一类型+同一签名)
  - 2次同类失败→标记疑似模式, 3次→确认模式+触发学习
  - 从 autonomous_reports 扫描历史失败

用法:
  python tools/failure_tracker.py log --type tool_timeout --sig "assess.py timeout" --task "xxx"
  python tools/failure_tracker.py patterns                 # 列出所有模式
  python tools/failure_tracker.py pattern P_001            # 查看特定模式详情
  python tools/failure_tracker.py resolve P_001            # 标记模式已解决
  python tools/failure_tracker.py archive P_001            # 归档解决的模式
  python tools/failure_tracker.py --scan-history           # 从历史报告扫描失败
  python tools/failure_tracker.py --stats                  # 失败统计
"""

import os, sys, json, hashlib, argparse
from datetime import datetime, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TRACKER_FILE = os.path.join(ROOT, "skills_learning", ".failure_tracker.json")

FAILURE_TYPES = [
    "assess_execution_error", "tool_timeout", "command_failed",
    "llm_misunderstanding", "environment_mismatch", "permission_denied",
    "logic_error", "resource_not_found", "other"
]
SEVERITIES = ["minor", "moderate", "critical"]


def _load():
    if os.path.exists(TRACKER_FILE):
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {"version": 1, "failures": [], "patterns": {}, "next_failure_id": 1, "next_pattern_id": 1}


def _save(data):
    with open(TRACKER_FILE, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def _compute_signature(error_msg, failure_type):
    """生成失败签名: 类型+错误信息前80字符的hash"""
    key = f"{failure_type}:{error_msg[:80]}"
    return hashlib.sha256(key.encode()).hexdigest()[:12]


INTERVALS_FOR_LEARNING = {
    1: "record",
    2: "mark_pattern",
    3: "auto_learn"
}


def cmd_log(args):
    """记录一次失败"""
    data = _load()

    fid = f"F_{data['next_failure_id']:04d}"
    data["next_failure_id"] += 1

    sig = _compute_signature(args.error[:200] if args.error else "", args.type)

    entry = {
        "failure_id": fid,
        "date": datetime.now().strftime("%Y-%m-%d"),
        "time": datetime.now().strftime("%H:%M"),
        "task": args.task or "",
        "operation": args.operation or "",
        "failure_type": args.type,
        "severity": args.severity or "moderate",
        "error_sig": args.error[:200] if args.error else "",
        "signature_hash": sig,
        "context": args.context or "",
        "root_cause": args.root_cause or "",
        "resolution": args.resolution or "",
        "pattern_ids": [],
        "session_id": args.session or ""
    }

    data["failures"].append(entry)

    # 检查是否已有相同签名的失败
    same_sig_failures = [f for f in data["failures"] if f["signature_hash"] == sig and f["failure_id"] != fid]

    if len(same_sig_failures) == 1:
        # 第2次同类失败 → 标记疑似模式
        pattern_id = f"P_{data['next_pattern_id']:04d}"
        data["next_pattern_id"] += 1
        data["patterns"][pattern_id] = {
            "pattern_id": pattern_id,
            "name": f"重复失败: {args.type}",
            "failure_type": args.type,
            "signature_hash": sig,
            "symptoms": [args.error[:100]] if args.error else [],
            "suspected_root_cause": "",
            "workaround": "",
            "fix": "",
            "occurrences": 2,
            "status": "pending",
            "failure_ids": [same_sig_failures[0]["failure_id"], fid],
            "created": datetime.now().strftime("%Y-%m-%d"),
            "resolved": None
        }
        entry["pattern_ids"].append(pattern_id)
        same_sig_failures[0]["pattern_ids"].append(pattern_id)

        print(f"[!] Pattern {pattern_id} detected (2 occurrences): {args.type}")
        print(f"    Status: PENDING — one more occurrence will trigger auto-learning")

    elif len(same_sig_failures) >= 2:
        # 第3+次同类失败 → 确认模式 + 自动触发学习建议
        # 找对应的pattern
        for pid, pat in data["patterns"].items():
            if pat["signature_hash"] == sig and pat["status"] == "pending":
                pat["occurrences"] += 1
                pat["failure_ids"].append(fid)
                pat["status"] = "confirmed"
                entry["pattern_ids"].append(pid)
                pat["resolved"] = None

                print(f"[!!] Pattern {pid} CONFIRMED ({pat['occurrences']} occurrences): {args.type}")
                print(f"    Action required: run auto-learning pipeline")
                print(f"    Suggested: python tools/skill_learn_from_cases_full \"{args.type}\"")

                # 如果是critical, 建议写入全局记忆
                if args.severity == "critical":
                    print(f"    [CRITICAL] Consider adding to global_mem_insight.txt RULES")
                break
        else:
            # 已经有confirmed pattern, 继续计数
            for pid, pat in data["patterns"].items():
                if pat["signature_hash"] == sig:
                    pat["occurrences"] += 1
                    pat["failure_ids"].append(fid)
                    entry["pattern_ids"].append(pid)
                    break
    else:
        print(f"[i] Failure {fid} recorded (first of this type)")

    _save(data)

    # 输出仪表盘信息
    stats = _compute_stats(data)
    print(f"\n    Failure stats: {stats['total']} total, {stats['patterns_pending']} pending patterns, "
          f"{stats['patterns_confirmed']} confirmed")

    return entry


def cmd_patterns(args):
    """列出所有失败模式"""
    data = _load()
    patterns = data.get("patterns", {})

    if not patterns:
        print("No patterns detected yet.")
        return

    print(f"{'ID':<10} {'Type':<25} {'Status':<10} {'Occurrences':<12} {'Created'}")
    print("-" * 80)
    for pid, pat in sorted(patterns.items()):
        status = pat.get("status", "unknown")
        print(f"{pid:<10} {pat['failure_type']:<25} {status:<10} {pat['occurrences']:<12} {pat.get('created','?')}")


def cmd_pattern_detail(args):
    """查看特定模式详情"""
    data = _load()
    patterns = data.get("patterns", {})

    if args.pattern_id not in patterns:
        print(f"Pattern {args.pattern_id} not found.")
        return

    pat = patterns[args.pattern_id]
    print(f"\n=== Pattern {args.pattern_id} ===")
    print(f"  Name:         {pat.get('name', '')}")
    print(f"  Type:         {pat['failure_type']}")
    print(f"  Status:       {pat.get('status', 'unknown')}")
    print(f"  Occurrences:  {pat['occurrences']}")
    print(f"  Created:      {pat.get('created', '?')}")
    print(f"  Resolved:     {pat.get('resolved', 'N/A')}")
    print(f"  Workaround:   {pat.get('workaround', '(none)')}")
    print(f"  Fix:          {pat.get('fix', '(none)')}")
    print(f"  Root cause:   {pat.get('suspected_root_cause', '(none)')}")

    # 列出关联的失败记录
    fid_map = {f["failure_id"]: f for f in data["failures"]}
    print(f"\n  Related failures:")
    for fid in pat.get("failure_ids", []):
        f = fid_map.get(fid, {})
        print(f"    {fid}: {f.get('date','?')} | {f.get('error_sig','')[:80]}")


def cmd_resolve(args):
    """标记模式已解决"""
    data = _load()
    if args.pattern_id not in data["patterns"]:
        print(f"Pattern {args.pattern_id} not found.")
        return

    pat = data["patterns"][args.pattern_id]
    pat["status"] = "resolved"
    pat["resolved"] = datetime.now().strftime("%Y-%m-%d")
    if args.fix:
        pat["fix"] = args.fix
    if args.root_cause:
        pat["suspected_root_cause"] = args.root_cause
    if args.workaround:
        pat["workaround"] = args.workaround

    _save(data)
    print(f"[OK] Pattern {args.pattern_id} resolved.")


def cmd_archive(args):
    """归档已解决的模式"""
    data = _load()
    if args.pattern_id not in data["patterns"]:
        print(f"Pattern {args.pattern_id} not found.")
        return

    pat = data["patterns"][args.pattern_id]
    pat["status"] = "archived"
    _save(data)
    print(f"[OK] Pattern {args.pattern_id} archived.")


def _compute_stats(data):
    """计算失败统计"""
    total = len(data.get("failures", []))
    patterns = data.get("patterns", {})
    patterns_pending = sum(1 for p in patterns.values() if p.get("status") == "pending")
    patterns_confirmed = sum(1 for p in patterns.values() if p.get("status") == "confirmed")
    patterns_resolved = sum(1 for p in patterns.values() if p.get("status") == "resolved")

    # 按类型统计
    from collections import Counter
    type_counter = Counter(f.get("failure_type", "other") for f in data.get("failures", []))

    # 最近7天
    week_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    recent = sum(1 for f in data.get("failures", []) if f.get("date", "") >= week_ago)

    return {
        "total": total,
        "patterns_pending": patterns_pending,
        "patterns_confirmed": patterns_confirmed,
        "patterns_resolved": patterns_resolved,
        "recent_7d": recent,
        "by_type": type_counter
    }


def cmd_stats(args):
    """显示失败统计"""
    data = _load()
    stats = _compute_stats(data)

    print("=" * 60)
    print(f"  Failure Stats")
    print("=" * 60)
    print(f"  Total failures:     {stats['total']}")
    print(f"  Last 7 days:        {stats['recent_7d']}")
    print(f"  Pending patterns:   {stats['patterns_pending']}")
    print(f"  Confirmed patterns: {stats['patterns_confirmed']}")
    print(f"  Resolved patterns:  {stats['patterns_resolved']}")

    if stats['by_type']:
        print(f"\n  By type:")
        for ftype, cnt in stats['by_type'].most_common(10):
            bar = "#" * min(cnt, 30)
            print(f"    {ftype:25s}: {cnt:3d}  {bar}")

    # 最近5次失败
    failures = data.get("failures", [])
    if failures:
        print(f"\n  Last 5 failures:")
        for f in failures[-5:]:
            print(f"    {f['failure_id']} | {f['date']} | {f['failure_type']} | {f.get('error_sig','')[:60]}")
    print("=" * 60)


def cmd_scan_history(args):
    """从 autonomous_reports 扫描历史失败"""
    reports_dir = os.path.join(ROOT, "temp", "autonomous_reports")
    if not os.path.exists(reports_dir):
        print(f"[ERROR] Directory not found: {reports_dir}")
        return

    scanned = 0
    found_failures = 0

    for fname in sorted(os.listdir(reports_dir)):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(reports_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            content = f.read()

        # Look for failure indicators
        fail_keywords = ["失败", "error", "Error", "FAIL", "fail", "timed out",
                        "timeout", "Exception", "exception", "permission denied"]

        lower = content.lower()
        keywords_found = [kw for kw in fail_keywords if kw.lower() in lower]

        if keywords_found:
            found_failures += 1
            # Extract first 200 chars of the report as context
            context = content[:200].replace("\n", " ").strip()
            print(f"  [{fname}] keywords: {keywords_found[:3]}")
            print(f"    context: {context[:100]}...")

        scanned += 1

    print(f"\nScanned {scanned} reports, found {found_failures} with failure keywords.")
    print("To import specific failures, use: python tools/failure_tracker.py log --type ... --error ...")


def main():
    parser = argparse.ArgumentParser(description="Failure Tracker Tool")
    parser.add_argument("--scan-history", action="store_true", help="Scan autonomous_reports for failures")
    parser.add_argument("--stats", action="store_true", help="Show failure statistics")

    sub = parser.add_subparsers()

    log_p = sub.add_parser("log", help="Record a failure")
    log_p.add_argument("--type", choices=FAILURE_TYPES, required=True)
    log_p.add_argument("--error", required=True, help="Error message/signature")
    log_p.add_argument("--task", default="")
    log_p.add_argument("--operation", default="")
    log_p.add_argument("--severity", choices=SEVERITIES, default="moderate")
    log_p.add_argument("--context", default="")
    log_p.add_argument("--root-cause", dest="root_cause", default="")
    log_p.add_argument("--resolution", default="")
    log_p.add_argument("--session", default="")
    log_p.set_defaults(func=cmd_log)

    pat_p = sub.add_parser("patterns", help="List all patterns")
    pat_p.set_defaults(func=cmd_patterns)

    detail_p = sub.add_parser("pattern", help="Show pattern detail")
    detail_p.add_argument("pattern_id")
    detail_p.set_defaults(func=cmd_pattern_detail)

    resolve_p = sub.add_parser("resolve", help="Mark pattern as resolved")
    resolve_p.add_argument("pattern_id")
    resolve_p.add_argument("--fix", default="")
    resolve_p.add_argument("--root-cause", dest="root_cause", default="")
    resolve_p.add_argument("--workaround", default="")
    resolve_p.set_defaults(func=cmd_resolve)

    archive_p = sub.add_parser("archive", help="Archive resolved pattern")
    archive_p.add_argument("pattern_id")
    archive_p.set_defaults(func=cmd_archive)

    args = parser.parse_args()

    if args.scan_history:
        cmd_scan_history()
    elif args.stats:
        cmd_stats()
    elif hasattr(args, 'func'):
        args.func(args)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
