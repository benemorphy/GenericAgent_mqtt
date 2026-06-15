#!/usr/bin/env python3
"""
skill_review — 间隔重复复习工具

功能:
  - 检查所有到期技能并执行复习
  - 管理 skills_learning/.review_tracker.json
  - 调用每个技能的 assess.py 进行验证

用法:
  python tools/skill_review.py                    # 检查+复习到期技能
  python tools/skill_review.py --list-due         # 仅列出到期
  python tools/skill_review.py --force skill1 skill2  # 强制复习指定技能
  python tools/skill_review.py --init             # 初始化: 扫描skills_learning注册所有技能
  python tools/skill_review.py --register skill rev  # 注册单个技能
  python tools/skill_review.py --stats            # 统计概览
"""
import json
import os
import sys
import subprocess
import datetime
from pathlib import Path

GA_ROOT = Path(__file__).resolve().parent.parent
SKILLS_DIR = GA_ROOT / "skills_learning"
TRACKER_FILE = SKILLS_DIR / ".review_tracker.json"

# 间隔重复等级 -> 天数
INTERVALS = [1, 3, 7, 14, 30, 90, 365]
MAX_LEVEL = len(INTERVALS) - 1  # L6

# 评分阈值
PASS_THRESHOLD = 80
PARTIAL_THRESHOLD = 50


def load_tracker():
    if TRACKER_FILE.exists():
        with open(TRACKER_FILE) as f:
            return json.load(f)
    return {"version": 1, "last_updated": "", "skills": {}}


def save_tracker(tracker):
    tracker["last_updated"] = datetime.date.today().isoformat()
    with open(TRACKER_FILE, "w") as f:
        json.dump(tracker, f, indent=2, ensure_ascii=False)
    print(f"[OK] Tracker saved: {TRACKER_FILE}")


def scan_all_skills():
    """扫描 skills_learning/ 下所有技能和最新 rev"""
    skills = {}
    if not SKILLS_DIR.exists():
        return skills
    for skill_name in sorted(os.listdir(SKILLS_DIR)):
        skill_path = SKILLS_DIR / skill_name
        if not skill_path.is_dir() or skill_name.startswith("."):
            continue
        revs = sorted(
            [d for d in os.listdir(skill_path)
             if d.startswith("rev") and (skill_path / d).is_dir()],
            key=lambda x: int(x.replace("rev", "") or 0)
        )
        if revs:
            # 取最新rev
            latest_rev = revs[-1]
            rev_num = int(latest_rev.replace("rev", ""))
            assess_path = skill_path / latest_rev / "tools" / "assess.py"
            skills[skill_name] = {
                "skill": skill_name,
                "rev": rev_num,
                "assess_path": str(assess_path),
                "has_assess": assess_path.exists()
            }
    return skills


def get_next_review_date(level, last_review_str=None):
    """根据等级计算下次复习日期"""
    if last_review_str:
        last = datetime.date.fromisoformat(last_review_str)
    else:
        last = datetime.date.today()
    interval = INTERVALS[min(level, MAX_LEVEL)]
    return (last + datetime.timedelta(days=interval)).isoformat()


def run_assess(skill_name, rev, assess_path):
    """运行 assess.py 并解析分数"""
    print(f"  [RUN] python {assess_path}")
    try:
        result = subprocess.run(
            [sys.executable, assess_path],
            capture_output=True, text=True, timeout=120,
            cwd=str(GA_ROOT)
        )
        stdout = result.stdout
        stderr = result.stderr

        # 尝试从 stdout 解析 JSON 评分
        score = None
        for line in stdout.split("\n"):
            line = line.strip()
            if not line:
                continue
            try:
                data = json.loads(line)
                if isinstance(data, dict) and "final_score" in data:
                    score = data["final_score"]
                    break
            except json.JSONDecodeError:
                continue

        # 也检查输出末尾是否有 JSON 块
        if score is None:
            import re
            json_blocks = re.findall(r'\{[^}]+\}', stdout, re.DOTALL)
            for block in json_blocks:
                try:
                    data = json.loads(block)
                    if isinstance(data, dict) and "final_score" in data:
                        score = data["final_score"]
                        break
                except json.JSONDecodeError:
                    pass

        # 也尝试直接读取 assessment.json
        if score is None:
            report_dir = Path(assess_path).parent.parent / "reports"
            assess_json = report_dir / "assessment.json"
            if assess_json.exists():
                try:
                    with open(assess_json) as f:
                        data = json.load(f)
                    score = data.get("final_score")
                except Exception:
                    pass

        if score is not None:
            return score, stdout[:500], None
        else:
            return None, stdout[:500], f"Could not parse score from output. stderr: {stderr[:300]}"

    except subprocess.TimeoutExpired:
        return None, "", "Timeout (120s)"
    except Exception as e:
        return None, "", str(e)


def review_skill(tracker, skill_name, skill_info, force=False):
    """执行单个技能的复习"""
    today = datetime.date.today().isoformat()
    key = f"{skill_name}-rev{skill_info['rev']}"

    entry = tracker["skills"].get(key, {
        "skill": skill_name,
        "rev": skill_info["rev"],
        "level": 0,
        "last_review": None,
        "next_review": None,
        "last_score": None,
        "consecutive_fails": 0,
        "history": []
    })

    # 检查是否今天已复习
    if not force and entry.get("last_review") == today:
        print(f"  [SKIP] {key} already reviewed today")
        return entry, False

    # 运行 assess.py
    if not skill_info["has_assess"]:
        print(f"  [SKIP] {key} has no assess.py — registering without review")
        entry["last_review"] = None
        entry["next_review"] = get_next_review_date(entry["level"], None)
        tracker["skills"][key] = entry
        return entry, False

    next_rev_str = entry.get('next_review', '?')
    print(f"  [REVIEW] {key} (level={entry['level']}, next={next_rev_str})")
    score, stdout, error = run_assess(skill_name, skill_info["rev"], skill_info["assess_path"])

    if score is None:
        print(f"  [ERROR] assess failed: {error[:100]}")
        print(f"  [SKIP] {key} — keeping level, will retry next cycle")
        # assess 故障时不改变等级
        return entry, False

    print(f"  [SCORE] {key} = {score}")

    # 更新history
    entry["history"].append({"date": today, "score": score})
    entry["last_review"] = today
    entry["last_score"] = score

    # 升降级
    old_level = entry["level"]
    if score >= PASS_THRESHOLD:
        entry["level"] = min(old_level + 1, MAX_LEVEL)
        entry["consecutive_fails"] = 0
        status = "PASS (level up)"
    elif score >= PARTIAL_THRESHOLD:
        entry["consecutive_fails"] = 0
        status = "PARTIAL (keep level)"
    else:
        entry["level"] = max(old_level - 1, 0)
        entry["consecutive_fails"] += 1
        status = "FAIL (level down)"

    # 连续失败警告
    if entry["consecutive_fails"] >= 2:
        print(f"  [WARN] {key} consecutive fails={entry['consecutive_fails']} — consider relearning!")

    # 计算下次复习日期
    entry["next_review"] = get_next_review_date(entry["level"], today)
    tracker["skills"][key] = entry

    print(f"  [STATUS] {status}: L{old_level}->L{entry['level']}, next={entry['next_review']}")
    return entry, True


def cmd_list_due(tracker):
    """列出到期技能"""
    today = datetime.date.today()
    due = []
    for key, entry in sorted(tracker["skills"].items()):
        next_rev = entry.get("next_review")
        if next_rev is None or datetime.date.fromisoformat(next_rev) <= today:
            due.append((key, entry))
    return due


def cmd_review(args):
    """执行复习"""
    tracker = load_tracker()
    today = datetime.date.today().isoformat()

    if args.get("--force"):
        force_skills = args["--force"]
        all_skills = scan_all_skills()
        reviewed = []
        skipped = []
        for sname in force_skills:
            if sname in all_skills:
                entry, did_review = review_skill(
                    tracker, sname, all_skills[sname], force=True
                )
                if did_review:
                    reviewed.append(sname)
                else:
                    skipped.append(sname)
            else:
                print(f"[WARN] Skill '{sname}' not found in skills_learning/")
        save_tracker(tracker)
        return reviewed, skipped

    # 正常: 检查到期技能
    due = cmd_list_due(tracker)
    if not due:
        print("[OK] No skills due for review today.")
        return [], []

    print(f"[DUE] {len(due)} skill(s) due for review:")
    for key, entry in due:
        lv = entry["level"]
        score = entry.get("last_score", "?")
        print(f"  - {key} (L{lv}, last={score})")

    all_skills = scan_all_skills()
    reviewed = []
    skipped = []
    for key, entry in due:
        skill_name = entry["skill"]
        if skill_name in all_skills:
            e, did_review = review_skill(tracker, skill_name, all_skills[skill_name])
            if did_review:
                reviewed.append(skill_name)
            else:
                skipped.append(skill_name)
        else:
            # 技能目录可能被删除
            print(f"  [WARN] {key} skill directory not found, skipping")
            skipped.append(skill_name)

    save_tracker(tracker)
    return reviewed, skipped


def cmd_init():
    """初始化: 扫描所有技能并注册到tracker"""
    tracker = load_tracker()
    all_skills = scan_all_skills()
    registered = 0
    for sname, info in all_skills.items():
        key = f"{sname}-rev{info['rev']}"
        if key not in tracker["skills"]:
            tracker["skills"][key] = {
                "skill": sname,
                "rev": info["rev"],
                "level": 0,
                "last_review": None,
                "next_review": get_next_review_date(0, None),
                "last_score": None,
                "consecutive_fails": 0,
                "history": []
            }
            registered += 1
            print(f"  [REG] {key}")
    save_tracker(tracker)
    print(f"\n[OK] Registered {registered} new skill(s). Total: {len(tracker['skills'])}")
    return registered


def cmd_register(skill_name, rev_str):
    """注册单个技能"""
    rev_num = int(rev_str.replace("rev", ""))
    tracker = load_tracker()
    key = f"{skill_name}-rev{rev_num}"

    if key in tracker["skills"]:
        existing = tracker["skills"][key]
        if existing["rev"] >= rev_num:
            print(f"[SKIP] {key} already registered at rev{existing['rev']}")
            return False

    tracker["skills"][key] = {
        "skill": skill_name,
        "rev": rev_num,
        "level": 0,
        "last_review": None,
        "next_review": get_next_review_date(0, None),
        "last_score": None,
        "consecutive_fails": 0,
        "history": []
    }
    save_tracker(tracker)
    print(f"[OK] Registered {key}")
    return True


def cmd_stats(tracker):
    """统计概览"""
    skills = tracker.get("skills", {})
    if not skills:
        print("[EMPTY] No skills in tracker. Run --init first.")
        return

    today = datetime.date.today()
    total = len(skills)
    by_level = {}
    due_count = 0
    mastered = 0
    struggling = 0

    for key, entry in skills.items():
        lv = entry.get("level", 0)
        by_level[lv] = by_level.get(lv, 0) + 1
        if lv >= 6:
            mastered += 1
        if entry.get("consecutive_fails", 0) >= 2:
            struggling += 1
        next_rev = entry.get("next_review")
        if next_rev and datetime.date.fromisoformat(next_rev) <= today:
            due_count += 1

    print("=== Spaced Repetition Stats ===")
    print(f"Total skills: {total}")
    print(f"Due today:    {due_count}")
    print(f"Mastered(L6): {mastered}")
    print(f"Struggling:   {struggling}")
    print("\nLevel distribution:")
    for lv in range(MAX_LEVEL + 1):
        label = f"L{lv} ({INTERVALS[lv]}d)"
        count = by_level.get(lv, 0)
        bar = "#" * count
        print(f"  {label:12s}: {count:3d}  {bar}")
    print("\nNext 7 days review load:")
    for i in range(7):
        d = (today + datetime.timedelta(days=i)).isoformat()
        load = sum(1 for e in skills.values() if e.get("next_review") == d)
        if load > 0:
            print(f"  {d}: {load} skill(s)")


def main():
    import argparse
    parser = argparse.ArgumentParser(description="Spaced Repetition Skill Review")
    parser.add_argument("--list-due", action="store_true", help="List due skills only")
    parser.add_argument("--force", nargs="+", help="Force review specific skills")
    parser.add_argument("--init", action="store_true", help="Initialize tracker with all skills")
    parser.add_argument("--register", nargs=2, metavar=("skill", "rev"), help="Register a skill")
    parser.add_argument("--stats", action="store_true", help="Show statistics")
    args = parser.parse_args()

    if args.init:
        cmd_init()
    elif args.register:
        cmd_register(args.register[0], args.register[1])
    elif args.stats:
        tracker = load_tracker()
        cmd_stats(tracker)
    elif args.list_due:
        tracker = load_tracker()
        due = cmd_list_due(tracker)
        if due:
            print(f"Skills due for review ({len(due)}):")
            for key, entry in due:
                lv = entry["level"]
                last = entry.get("last_score", "?")
                next_rev = entry.get("next_review", "?")
                print(f"  {key}  L{lv}  last={last}  next={next_rev}")
        else:
            print("No skills due for review today.")
    elif args.force:
        reviewed, skipped = cmd_review({"--force": args.force})
        print(f"\nReviewed: {reviewed}")
        print(f"Skipped: {skipped}")
    else:
        reviewed, skipped = cmd_review({})
        print(f"\nReviewed: {reviewed}")
        print(f"Skipped: {skipped}")


if __name__ == "__main__":
    main()
