#!/usr/bin/env python3
"""
文件名 lint 检查 — 检测文件名中的常见问题

检查项:
  1. 前导/尾随空格（如 " brainstorm.md"）
  2. 连续空格（如 "my  notes.md"）
  3. 特殊字符（如 ?, *, <, >, |, :, "）
  4. 路径过长（> 200 字符）
  5. Python 文件中的冒号命名

用法:
    python tools/lint_filenames.py              # 检查全部
    python tools/lint_filenames.py --dir docs   # 指定目录
    python tools/lint_filenames.py --fix        # 自动修复前导/尾随空格
"""

import os
import sys
import shutil

ISSUES = []

def check_dir(root, fix=False):
    for dirpath, dirnames, fnames in os.walk(root):
        # 跳过隐藏目录
        dirnames[:] = [d for d in dirnames if not d.startswith('.') and d != '__pycache__']
        for name in fnames + dirnames:
            _check_name(name, dirpath, fix)
            # 检查完整路径长度
            full = os.path.join(dirpath, name)
            if len(full) > 200:
                ISSUES.append(('PATH_TOO_LONG', full,
                              f"{len(full)} chars > 200"))

def _check_name(name, dirpath, fix):
    full = os.path.join(dirpath, name)
    # 1. 前导空格
    if name != name.lstrip():
        ISSUES.append(('LEADING_SPACE', full, f"前导空格: `{name}`"))
        if fix:
            new = name.lstrip()
            shutil.move(full, os.path.join(dirpath, new))
            print(f"  [FIX] {full} -> {new}")
    # 2. 尾随空格
    if name != name.rstrip():
        ISSUES.append(('TRAILING_SPACE', full, f"尾随空格: `{name}`"))
        if fix and not name.lstrip() != name:  # 如果已修前导
            pass  # rstrip handled separately
        if fix:
            new = name.rstrip()
            shutil.move(full, os.path.join(dirpath, new))
            print(f"  [FIX] {full} -> {new}")
    # 3. 连续空格
    if '  ' in name:
        ISSUES.append(('DOUBLE_SPACE', full, f"连续空格: `{name}`"))
    # 4. 特殊字符
    forbidden = set('?*<>|:"\\')
    found = [c for c in name if c in forbidden]
    if found:
        ISSUES.append(('FORBIDDEN_CHAR', full,
                      f"含特殊字符 {set(found)}: `{name}`"))

def main():
    import argparse
    parser = argparse.ArgumentParser(description="文件名 lint 检查")
    parser.add_argument('--dir', default=None, help="指定检查目录")
    parser.add_argument('--fix', action='store_true', help="自动修复前导/尾随空格")
    args = parser.parse_args()

    root = args.dir or os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    # 跳过 .git, __pycache__, .venv, node_modules
    check_dir(root, fix=args.fix)

    if not ISSUES:
        print("\n[PASS] 文件名检查通过，无问题")
        return

    print(f"\n[FAIL] 发现 {len(ISSUES)} 个文件名问题:")
    by_type = {}
    for typ, path, desc in ISSUES:
        by_type.setdefault(typ, []).append((path, desc))

    for typ, items in sorted(by_type.items()):
        print(f"\n  [{typ}] ({len(items)} 个)")
        for path, desc in items[:5]:
            print(f"    {desc}")
            print(f"      {path}")
        if len(items) > 5:
            print(f"    ... 还有 {len(items)-5} 个")

    sys.exit(1)

if __name__ == '__main__':
    main()
