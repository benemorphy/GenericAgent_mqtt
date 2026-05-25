#!/usr/bin/env python3
"""
量化评估基准工具 — 反刍效率基准

衡量GA的自我改进闭环效率，5个核心指标：
  1. CI首次通过率     — GitHub Actions workflow 首次运行通过率
  2. 反刍循环次数     — 失败→修复→验证的平均循环次数
  3. SOP存活率        — SOP文件创建后未经修改的存活比例
  4. 技能复习通过率   — spaced_repetition 中评分>=70的技能比例
  5. 失败模式覆盖率   — 已识别失败模式 / 已定义失败类型

用法:
  python tools/benchmark_metrics.py              # 输出全量报告
  python tools/benchmark_metrics.py --format md  # Markdown 格式
  python tools/benchmark_metrics.py --metric ci  # 单个指标
"""

import subprocess, json, os, sys
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

ROOT = Path(__file__).resolve().parent.parent


def metric_ci_first_pass_rate():
    """CI首次通过率 — 查询GitHub Actions运行历史"""
    results = {}
    try:
        r = subprocess.run(
            ['gh', 'run', 'list', '--workflow=ci.yml', '--limit=20', '--json=conclusion,displayTitle,createdAt,headBranch'],
            capture_output=True, text=True, timeout=15
        )
        if r.returncode != 0:
            return {"status": "unavailable", "detail": "gh CLI not available or not authenticated", "value": None}
        runs = json.loads(r.stdout)
        total = len(runs)
        passed = sum(1 for run in runs if run.get('conclusion') == 'success')
        failed = sum(1 for run in runs if run.get('conclusion') == 'failure')
        first_pass = sum(1 for run in runs if run.get('conclusion') in ('success', None))
        results["status"] = "ok"
        results["total_runs"] = total
        results["passed"] = passed
        results["failed"] = failed
        results["first_pass_rate"] = round(passed / total * 100, 1) if total > 0 else 0
    except (FileNotFoundError, subprocess.TimeoutExpired, json.JSONDecodeError) as e:
        # fallback: 从git log估算(哪些提交是fix后的重新尝试)
        results["status"] = "estimated_from_git"
        results["detail"] = f"gh CLI unavailable ({e}), using git log estimate"
        r = subprocess.run(['git', 'log', '--format=%s', '--since=2026-05-01'], capture_output=True, text=True, encoding='utf-8', errors='replace')
        commits = [l for l in r.stdout.strip().split('\n') if l]
        fix_patterns = ['fix', '修复', 'hotfix', 'bug', 'correct', '修复']
        retry_patterns = ['retry', 're-try', 'try again', 'attempt', '重试']
        fix_count = sum(1 for c in commits if any(p in c.lower() for p in fix_patterns))
        retry_count = sum(1 for c in commits if any(p in c.lower() for p in retry_patterns))
        total_non_merge = sum(1 for c in commits if 'merge' not in c.lower() and 'pr #' not in c.lower())
        estimated_pass = total_non_merge - fix_count - retry_count
        results["total_normal_commits"] = total_non_merge
        results["fix_commits"] = fix_count
        results["retry_commits"] = retry_count
        results["first_pass_rate"] = round(estimated_pass / total_non_merge * 100, 1) if total_non_merge > 0 else 0
        results["note"] = "估计值: 非fix/retry提交占总非merge提交的比例"
    return results


def metric_rumination_cycles():
    """反刍循环次数 — git提交中 fix→commit 的密集度分析"""
    r = subprocess.run(['git', 'log', '--format=%H %ai %s', '--all', '--since=2026-05-17'], capture_output=True, text=True, encoding='utf-8', errors='replace')
    lines = [l.strip() for l in r.stdout.strip().split('\n') if l]
    
    cycles = defaultdict(list)
    current_day = None
    day_commits = []
    
    for line in lines:
        parts = line.split(' ', 2)
        if len(parts) < 3:
            continue
        sha, date_str = parts[0], parts[1]
        msg = parts[2] if len(parts) > 2 else ''
        day = date_str[:10]
        
        if day != current_day:
            if current_day and day_commits:
                cycles[current_day] = day_commits
            current_day = day
            day_commits = []
        day_commits.append({"sha": sha, "msg": msg[:80]})
    
    if current_day and day_commits:
        cycles[current_day] = day_commits
    
    # 分析反刍: 同一天内 fix→后续非fix提交 的模式
    total_rumination = 0
    total_days = len(cycles)
    rumination_days = 0
    
    for day, commits in sorted(cycles.items()):
        has_fix = any('fix' in c['msg'].lower() or '修复' in c['msg'] or 'retry' in c['msg'].lower() for c in commits)
        has_after_fix = False
        if has_fix:
            fix_indices = [i for i, c in enumerate(commits) if 'fix' in c['msg'].lower() or '修复' in c['msg']]
            for fi in fix_indices:
                if fi < len(commits) - 1:
                    has_after_fix = True
                    break
        if has_fix and has_after_fix:
            rumination_days += 1
            total_rumination += 1
    
    # 反刍密度: 每10个提交中反刍相关提交数
    fix_related = sum(1 for l in lines if any(kw in l.lower() for kw in ['fix', '修复', '清理', 'clean', '整理']))
    total_commits = len(lines)
    
    return {
        "total_commits": total_commits,
        "total_days": total_days,
        "rumination_days": rumination_days,
        "fix_related_ratio": round(fix_related / total_commits * 100, 1) if total_commits > 0 else 0,
        "rumination_cycles_per_day": round(total_rumination / total_days, 2) if total_days > 0 else 0,
        "avg_daily_commits": round(total_commits / total_days, 1) if total_days > 0 else 0,
    }


def metric_sop_survival():
    """SOP存活率 — SOP创建后未经大修的稳定比例"""
    sop_dir = ROOT / 'memory'
    sops = list(sop_dir.glob('*.md'))
    sops = [s for s in sops if s.name != 'memory_management_sop.md']
    
    sop_stats = []
    for sop in sorted(sops):
        r = subprocess.run(
            ['git', 'log', '--format=%ci', '--follow', str(sop.relative_to(ROOT))],
            capture_output=True, text=True
        )
        dates = [l.strip()[:10] for l in r.stdout.strip().split('\n') if l]
        if not dates:
            continue
        created = dates[0]
        last_modified = dates[-1]
        total_mods = len(dates)
        age_days = (datetime.now() - datetime.strptime(created, '%Y-%m-%d')).days
        
        # 存活标准: 创建后只有1次修改 = 初始创建, 或超过7天未修改 = 稳定
        survived = (total_mods <= 1 and age_days >= 1) or (age_days - (datetime.now() - datetime.strptime(last_modified, '%Y-%m-%d')).days >= 3)
        
        sop_stats.append({
            "name": sop.name.replace('.md', ''),
            "created": created,
            "last_modified": last_modified,
            "modifications": total_mods,
            "age_days": age_days,
            "survived": survived,
        })
    
    survived_count = sum(1 for s in sop_stats if s['survived'])
    unstable = [s for s in sop_stats if not s['survived']]
    
    return {
        "total_sops": len(sop_stats),
        "survived": survived_count,
        "survival_rate": round(survived_count / len(sop_stats) * 100, 1) if sop_stats else 0,
        "unstable_sops": [s['name'] for s in unstable],
        "details": sop_stats,
    }


def metric_skill_review_pass():
    """技能复习通过率 — last_score >= 70的技能比例"""
    tracker_path = ROOT / 'skills_learning' / '.review_tracker.json'
    if not tracker_path.exists():
        return {"status": "unavailable", "detail": ".review_tracker.json not found", "value": None}
    
    with open(tracker_path) as f:
        rt = json.load(f)
    
    skills = rt.get('skills', {})
    total = len(skills)
    reviewed = sum(1 for s in skills.values() if isinstance(s, dict) and s.get('history', []))
    passed = sum(1 for s in skills.values() if isinstance(s, dict) and (s.get('last_score') or 0) >= 70)
    failed = sum(1 for s in skills.values() if isinstance(s, dict) and (s.get('last_score') or 0) > 0 and (s.get('last_score') or 0) < 70)
    
    avg_score = 0
    scores = [(s.get('last_score') or 0) for s in skills.values() if isinstance(s, dict) and s.get('last_score')]
    if scores:
        avg_score = round(sum(scores) / len(scores), 1)
    
    # 按等级分布
    level_dist = defaultdict(int)
    for s in skills.values():
        if isinstance(s, dict):
            level_dist[s.get('level', 0)] += 1
    
    return {
        "total_skills": total,
        "reviewed": reviewed,
        "passed": passed,
        "failed": failed,
        "pass_rate": round(passed / total * 100, 1) if total > 0 else 0,
        "avg_score": avg_score,
        "level_distribution": dict(level_dist),
    }


def metric_failure_coverage():
    """失败模式覆盖率 — failures vs known patterns"""
    tracker_path = ROOT / 'skills_learning' / '.failure_tracker.json'
    if not tracker_path.exists():
        return {"status": "unavailable", "detail": ".failure_tracker.json not found"}
    
    with open(tracker_path) as f:
        ft = json.load(f)
    
    # 已定义的失败类型 (from failure_driven_learning_sop)
    known_patterns = {
        'command_failed': 'shell命令错误',
        'llm_misunderstanding': 'LLM理解偏差',
        'environment_mismatch': '环境配置不对',
        'permission_denied': '权限不足',
        'logic_error': '逻辑错误/算法缺陷',
        'resource_not_found': '文件/资源找不到',
        'timeout': '超时',
        'network_error': '网络错误',
        'type_error': '类型错误',
        'value_error': '值错误',
    }
    
    tracked_failures = ft.get('failures', [])
    tracked_patterns = ft.get('patterns', {})
    
    # 统计哪些失败类型已被追踪
    covered = []
    uncovered = []
    if isinstance(tracked_patterns, dict):
        tracked_type_names = [p.get('type', '') for p in tracked_patterns.values()] if tracked_patterns else []
        for pname in known_patterns:
            if pname in tracked_type_names:
                covered.append(pname)
            else:
                uncovered.append(pname)
    else:
        uncovered = list(known_patterns.keys())
    
    return {
        "known_pattern_types": len(known_patterns),
        "tracked_failures": len(tracked_failures) if isinstance(tracked_failures, list) else 0,
        "tracked_patterns": len(tracked_patterns) if isinstance(tracked_patterns, dict) else 0,
        "covered_types": covered,
        "uncovered_types": uncovered,
        "coverage_rate": round(len(covered) / len(known_patterns) * 100, 1) if known_patterns else 0,
        "all_known_patterns": {k: v for k, v in known_patterns.items()},
    }


def run_all():
    """运行全部指标"""
    return {
        "report_generated": datetime.now().strftime('%Y-%m-%d %H:%M'),
        "git_commit": subprocess.run(['git', 'rev-parse', '--short', 'HEAD'], capture_output=True, text=True, encoding='utf-8', errors='replace').stdout.strip(),
        "metrics": {
            "ci_first_pass_rate": metric_ci_first_pass_rate(),
            "rumination_cycles": metric_rumination_cycles(),
            "sop_survival": metric_sop_survival(),
            "skill_review_pass": metric_skill_review_pass(),
            "failure_coverage": metric_failure_coverage(),
        }
    }


def format_text(report):
    """文本格式输出"""
    m = report['metrics']
    lines = [
        "=" * 60,
        f"  反刍效率基准报告",
        f"  生成: {report['report_generated']} | commit: {report['git_commit']}",
        "=" * 60,
        "",
        "--- 指标 ---",
        "",
    ]
    
    # CI通过率
    ci = m['ci_first_pass_rate']
    lines.append(f"1. CI首次通过率: {ci.get('first_pass_rate', 'N/A')}%")
    if ci.get('status') == 'unavailable':
        lines.append(f"   状态: {ci['detail']}")
    elif ci.get('status') == 'estimated_from_git':
        lines.append(f"   估计值 (gh CLI不可用): fix提交{ci.get('fix_commits','?')}/{ci.get('total_normal_commits','?')} 正常提交")
    
    # 反刍循环
    rum = m['rumination_cycles']
    lines.append(f"2. 反刍循环: 日均{rum.get('avg_daily_commits', 'N/A')}提交, 反刍密度{rum.get('fix_related_ratio', 'N/A')}%")
    lines.append(f"   反刍天数: {rum.get('rumination_days', 'N/A')}/{rum.get('total_days', 'N/A')}天")
    
    # SOP存活
    sop = m['sop_survival']
    lines.append(f"3. SOP存活率: {sop.get('survival_rate', 'N/A')}% ({sop.get('survived', 'N/A')}/{sop.get('total_sops', 'N/A')})")
    if sop.get('unstable_sops'):
        lines.append(f"   不稳定SOP: {', '.join(sop['unstable_sops'][:5])}")
    
    # 技能复习
    sk = m['skill_review_pass']
    lines.append(f"4. 技能复习通过率: {sk.get('pass_rate', 'N/A')}%")
    lines.append(f"   总数: {sk.get('total_skills', 0)}技能, 平均分: {sk.get('avg_score', 'N/A')}")
    
    # 失败覆盖率
    fc = m['failure_coverage']
    lines.append(f"5. 失败模式覆盖率: {fc.get('coverage_rate', 'N/A')}%")
    if fc.get('uncovered_types'):
        lines.append(f"   未覆盖: {', '.join(fc['uncovered_types'][:5])}")
    
    lines.append("")
    lines.append(f"--- 总体健康度: {_overall_health(report)} ---")
    lines.append("")
    return '\n'.join(lines)


def format_md(report):
    """Markdown格式输出"""
    m = report['metrics']
    ci = m['ci_first_pass_rate']
    rum = m['rumination_cycles']
    sop = m['sop_survival']
    sk = m['skill_review_pass']
    fc = m['failure_coverage']
    
    lines = []
    lines.append("# 反刍效率基准报告")
    lines.append("")
    lines.append(f"> 生成: {report['report_generated']} | commit: `{report['git_commit']}`")
    lines.append("")
    lines.append("## 指标一览")
    lines.append("")
    lines.append("| # | 指标 | 当前值 | 状态 |")
    lines.append("|:--|:-----|:-------|:-----|")
    
    ci_status = 'unavailable' if ci.get('status') == 'unavailable' else ('estimated' if ci.get('status') == 'estimated_from_git' else 'ok')
    lines.append(f"| 1 | CI首次通过率 | {ci.get('first_pass_rate', 'N/A')}% | {ci_status} |")
    
    rum_status = '稳定' if rum.get('fix_related_ratio', 100) < 60 else '频繁反刍'
    lines.append(f"| 2 | 反刍循环 | 日均{rum.get('avg_daily_commits', 'N/A')}提交, 反刍密度{rum.get('fix_related_ratio', 'N/A')}% | {rum_status} |")
    
    sop_status = '稳定' if sop.get('survival_rate', 0) > 70 else '波动大'
    lines.append(f"| 3 | SOP存活率 | {sop.get('survival_rate', 'N/A')}% ({sop.get('survived', 'N/A')}/{sop.get('total_sops', 'N/A')}) | {sop_status} |")
    
    sk_status = '良好' if sk.get('avg_score', 0) >= 70 else '待提高'
    lines.append(f"| 4 | 技能复习通过率 | {sk.get('pass_rate', 'N/A')}% (平均分 {sk.get('avg_score', 'N/A')}) | {sk_status} |")
    
    fc_status = '完善' if fc.get('coverage_rate', 0) > 80 else '有缺口'
    lines.append(f"| 5 | 失败模式覆盖率 | {fc.get('coverage_rate', 'N/A')}% ({len(fc.get('covered_types', []))}/{fc.get('known_pattern_types', 0)}) | {fc_status} |")
    
    lines.append("")
    lines.append(f"## 总体健康度")
    lines.append("")
    lines.append(f"**{_overall_health(report)}**")
    lines.append("")
    lines.append("## 详情")
    lines.append("")
    lines.append("### 1. CI首次通过率")
    lines.append("```json")
    lines.append(json.dumps(ci, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("### 2. 反刍循环")
    lines.append("```json")
    lines.append(json.dumps(rum, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("### 3. SOP存活率")
    lines.append("```json")
    lines.append(json.dumps(sop | {"details": "见下方表格"}, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("| SOP | 创建 | 最后修改 | 修改次数 | 存活 |")
    lines.append("|:----|:-----|:---------|:---------|:----|")
    for s in sop.get('details', []):
        survived = 'Y' if s.get('survived') else '--'
        lines.append(f"| {s['name']} | {s['created']} | {s['last_modified']} | {s['modifications']} | {survived} |")
    lines.append("")
    lines.append("### 4. 技能复习通过率")
    lines.append("```json")
    lines.append(json.dumps(sk, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    lines.append("### 5. 失败模式覆盖率")
    lines.append("```json")
    lines.append(json.dumps(fc, ensure_ascii=False, indent=2))
    lines.append("```")
    lines.append("")
    
    return '\n'.join(lines)


def _overall_health(report):
    """综合健康度评估"""
    m = report['metrics']
    score = 0
    max_score = 0
    
    ci = m['ci_first_pass_rate']
    if ci.get('first_pass_rate') is not None:
        score += min(ci['first_pass_rate'] / 20, 5)
        max_score += 5
    
    rum = m['rumination_cycles']
    if rum.get('fix_related_ratio') is not None:
        # 反刍密度越低越好: <30% → 5分, >70% → 0分
        fix_ratio = rum['fix_related_ratio']
        rum_score = max(0, 5 - (fix_ratio - 20) / 10)
        score += min(rum_score, 5)
        max_score += 5
    
    sop = m['sop_survival']
    if sop.get('survival_rate') is not None:
        score += min(sop['survival_rate'] / 20, 5)
        max_score += 5
    
    sk = m['skill_review_pass']
    if sk.get('avg_score') is not None and sk['avg_score'] > 0:
        score += min(sk['avg_score'] / 20, 5)
        max_score += 5
    
    fc = m['failure_coverage']
    if fc.get('coverage_rate') is not None:
        score += min(fc['coverage_rate'] / 20, 5)
        max_score += 5
    
    if max_score == 0:
        return "数据不足"
    
    pct = score / max_score * 100
    if pct >= 80:
        return f"健康 ({pct:.0f}%)"
    elif pct >= 60:
        return f"一般 ({pct:.0f}%)"
    elif pct >= 40:
        return f"待改善 ({pct:.0f}%)"
    else:
        return f"需关注 ({pct:.0f}%)"


if __name__ == '__main__':
    fmt = 'text'
    single_metric = None
    for arg in sys.argv[1:]:
        if arg.startswith('--format='):
            fmt = arg.split('=', 1)[1]
        elif arg.startswith('--metric='):
            single_metric = arg.split('=', 1)[1]
        elif arg == '--md':
            fmt = 'md'
    
    report = run_all()
    
    if single_metric:
        if single_metric in report['metrics']:
            print(json.dumps(report['metrics'][single_metric], ensure_ascii=False, indent=2))
        else:
            print(f"Unknown metric: {single_metric}")
            print(f"Available: {list(report['metrics'].keys())}")
    elif fmt == 'md':
        print(format_md(report))
    else:
        print(format_text(report))
