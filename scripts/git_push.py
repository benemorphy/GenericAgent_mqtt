#!/usr/bin/env python3
"""
一键推送工具 — 绕过 branch protection 的 PR 要求

用法：
  python scripts/git_push.py "提交信息"
  python scripts/git_push.py "提交信息" --no-push   # 只创建PR不push（如果已手动push）
  python scripts/git_push.py "提交信息" --skip-audit # 跳过安全审计

流程：
  1. 安全审计 → 2. 创建临时分支 → commit → push
  3. 通过 GitHub API 创建 PR
  4. 自动 squash-merge PR
  5. 删除临时分支
  6. 切回 main 并 pull

前置条件：
  - 在 mykey.py 中配置 github_token = "github_pat_xxxx"
    （GitHub Settings → Developer settings → Personal access tokens → Fine-grained tokens
     仓库权限: Contents: write, Pull requests: write）
"""

import argparse, os, sys, time, subprocess, json, urllib.request
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
os.chdir(PROJECT_ROOT)
sys.path.insert(0, str(PROJECT_ROOT))

REPO = "benemorphy/GenericAgent_mqtt"
BRANCH_PREFIX = "auto-push"

def get_token():
    """从 mykey.py 读取 GitHub token"""
    try:
        from mykey import github_token
        return github_token
    except (ImportError, AttributeError):
        print("[ERROR] 请在 mykey.py 中添加: github_token = 'github_pat_xxx'")
        sys.exit(1)

def run(cmd, check=True, capture=False):
    """运行命令"""
    print(f"$ {cmd}")
    if capture:
        r = subprocess.run(cmd, shell=True, capture_output=True, text=True)
        if r.returncode != 0 and check:
            print(f"[ERROR] 命令失败: {cmd}")
            print(r.stderr)
            sys.exit(1)
        return r.stdout.strip()
    r = subprocess.run(cmd, shell=True)
    if r.returncode != 0 and check:
        print(f"[ERROR] 命令失败: {cmd}")
        sys.exit(1)
    return r

def get_current_commit_message():
    """获取当前最新 commit 的信息"""
    try:
        msg = run("git log -1 --format=%s", capture=True)
        return msg
    except:
        return "auto update"


# ═══════════════════════════════════════════════════════════════
# 推送前安全审计
# ═══════════════════════════════════════════════════════════════
SENSITIVE_PATTERNS = [
    "sk-", "ghp_", "gho_", "ghu_", "ghs_", "ghr_",
    "api_key", "apikey", "api_secret", "apisecret",
    "password", "passwd", "secret", "token",
    "-----BEGIN RSA PRIVATE KEY-----",
    "-----BEGIN OPENSSH PRIVATE KEY-----",
    "-----BEGIN PRIVATE KEY-----",
]

def audit():
    """推送前安全审计"""
    print(f"\n{'='*50}")
    print("[审计] 检查即将推送的内容...")
    print(f"{'='*50}")
    
    status = run("git status --porcelain", capture=True)
    if not status:
        print("  无待推送文件")
        return True
    
    files = []
    for line in status.split("\n"):
        line = line.strip()
        if not line: continue
        status_flag = line[:2].strip()
        fname = line[3:].strip()
        if status_flag in ("M", "A", "?", "AM", "MM"):
            files.append(fname)
    
    if not files:
        print("  无文件改动")
        return True
    
    print(f"\n  待推送文件 ({len(files)}):")
    for f in sorted(files):
        size = os.path.getsize(f) if os.path.exists(f) else 0
        print(f"    {f}  ({size/1024:.1f} KB)")
    
    sensitive_found = []
    for f in files:
        if not os.path.exists(f): continue
        ext = os.path.splitext(f)[1].lower()
        if ext in ('.png','.jpg','.jpeg','.gif','.ico','.woff','.woff2','.ttf','.eot'):
            continue
        if os.path.getsize(f) > 500 * 1024: continue
        
        try:
            with open(f, 'r', encoding='utf-8', errors='ignore') as fh:
                content = fh.read()
            for pattern in SENSITIVE_PATTERNS:
                if pattern in content:
                    for i, line in enumerate(content.split('\n'), 1):
                        if pattern in line:
                            masked = line.strip()[:60].replace(pattern, pattern[:3]+'***'+pattern[-3:])
                            sensitive_found.append(f"  [WARN] {f}:{i}  {masked}")
        except:
            pass
    
    if sensitive_found:
        print(f"\n  [FAIL] 发现可能的敏感信息泄露!")
        for s in sensitive_found:
            print(s)
        print(f"\n  请移除敏感信息后再推送。确认安全可用 --skip-audit")
        return False
    
    print(f"\n  [PASS] 审计通过，无安全风险")
    return True


def main():
    parser = argparse.ArgumentParser(description="一键推送（自动 PR + merge）")
    parser.add_argument("message", nargs="?", help="commit 信息")
    parser.add_argument("--no-push", action="store_true", help="跳过 push")
    parser.add_argument("--skip-audit", action="store_true", help="跳过安全审计")
    args = parser.parse_args()

    # 推送前安全审计
    if not args.skip_audit:
        if not audit():
            print("\n推送已取消。确认安全请加 --skip-audit")
            sys.exit(1)
    else:
        print("  已跳过安全审计")

    token = get_token()
    commit_msg = args.message or get_current_commit_message()
    branch_name = f"{BRANCH_PREFIX}-{int(time.time())}"
    
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }
    api_base = f"https://api.github.com/repos/{REPO}"

    if not args.no_push:
        print(f"\n{'='*50}")
        print(f"1/5  创建分支: {branch_name}")
        run(f"git checkout -b {branch_name}")
        
        status = run("git status --porcelain", capture=True)
        if status:
            print(f"2/5  Commit: {commit_msg}")
            run('git add -A')
            run(f'git commit -m "{commit_msg}"')
        else:
            print("2/5  无新改动，直接推送当前分支")
        
        print("3/5  推送到远程")
        run(f"git push origin {branch_name}")
    else:
        print(f"\n{'='*50}")
        print("跳过 push 步骤")
        branch_name = run("git rev-parse --abbrev-ref HEAD", capture=True)
        print(f"当前分支: {branch_name}")

    # 创建 PR
    print(f"\n{'='*50}")
    print("4/5  创建 PR 并自动合并")
    
    pr_data = json.dumps({
        "title": commit_msg[:72],
        "head": branch_name,
        "base": "main",
        "body": "Auto-generated PR by git_push.py"
    }).encode()
    
    req = urllib.request.Request(
        f"{api_base}/pulls", data=pr_data, headers=headers, method="POST"
    )
    
    try:
        resp = urllib.request.urlopen(req)
        pr_info = json.loads(resp.read())
        pr_number = pr_info["number"]
        print(f"  PR #{pr_number} 已创建: {pr_info['html_url']}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"[ERROR] 创建 PR 失败: {e.code}")
        print(f"  {error_body}")
        run(f"git checkout main", check=False)
        run(f"git branch -D {branch_name}", check=False)
        sys.exit(1)

    # Merge PR (squash)
    merge_data = json.dumps({
        "merge_method": "squash",
        "commit_title": commit_msg[:72]
    }).encode()
    
    req2 = urllib.request.Request(
        f"{api_base}/pulls/{pr_number}/merge", data=merge_data, headers=headers, method="PUT"
    )
    
    try:
        resp2 = urllib.request.urlopen(req2)
        merge_info = json.loads(resp2.read())
        print(f"  PR #{pr_number} 已合并: {merge_info.get('sha', '')[:8]}")
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"[ERROR] 合并 PR 失败: {e.code}")
        print(f"  {error_body}")
        print(f"  请手动合并: https://github.com/benemorphy/GenericAgent_mqtt/pulls")

    # 删除远程分支
    print(f"\n{'='*50}")
    print("5/5  清理临时分支")
    
    req3 = urllib.request.Request(
        f"{api_base}/git/refs/heads/{branch_name}", headers=headers, method="DELETE"
    )
    try:
        urllib.request.urlopen(req3)
        print(f"  远程分支 {branch_name} 已删除")
    except urllib.error.HTTPError as e:
        print(f"  [WARN] 删除远程分支失败: {e.code}")

    # 切回 main 并更新
    run(f"git checkout main", check=False)
    run(f"git branch -D {branch_name}", check=False)
    run(f"git pull", check=False)
    
    print(f"\n{'='*50}")
    print(f"推送完成！已通过 PR #{pr_number} squash-merge 到 main")
    print(f"{'='*50}")


if __name__ == "__main__":
    main()
