#!/usr/bin/env python3
"""L3.5 Daily Decision Log 辅助工具

用法:
    from tools.l35_log import write_log, search_logs, log_template

    # 写日志
    write_log("主题", "结论", decisions=["决策1", "决策2"])
    
    # 搜索历史日志
    results = search_logs("关键词")
    
    # 获取日志模板
    print(log_template("主题"))
"""

import os, json, datetime
from pathlib import Path

_GA_ROOT = Path(__file__).resolve().parent.parent
_LOGS_DIR = _GA_ROOT / "memory" / "daily_logs"

def _today_path() -> Path:
    """今日日志文件路径"""
    _LOGS_DIR.mkdir(parents=True, exist_ok=True)
    return _LOGS_DIR / f"{datetime.date.today().isoformat()}.md"

def log_template(topic: str) -> str:
    """生成单条日志模板"""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    return f"""## {now} | {topic}

meta:
  type: daily_decision_log
  date: {datetime.date.today().isoformat()}
  topic: {topic}
  tags: []
  status: decided
  upgrade: none

### 结论
(一句话)

### 关键决策
- 

### 后续行动
- 

### 候选升级
- none
"""

def write_log(topic: str, conclusion: str, 
              decisions: list = None, 
              actions: list = None,
              tags: list = None,
              upgrade: str = "none"):
    """追加一条日志到今日文件"""
    now = datetime.datetime.now().strftime("%H:%M:%S")
    today = datetime.date.today().isoformat()
    
    tag_str = ", ".join(tags) if tags else ""
    dec_str = "\n".join(f"- {d}" for d in (decisions or []))
    act_str = "\n".join(f"- {a}" for a in (actions or []))
    
    entry = f"""
## {now} | {topic}

meta:
  type: daily_decision_log
  date: {today}
  topic: {topic}
  tags: [{tag_str}]
  status: decided
  upgrade: {upgrade}

### 结论
{conclusion}

### 关键决策
{dec_str or "- (无)"}

### 后续行动
{act_str or "- (无)"}

### 候选升级
- {upgrade}

---
"""
    fp = _today_path()
    with open(fp, 'a', encoding='utf-8') as f:
        f.write(entry)
    return fp

def search_logs(keyword: str, max_results: int = 10) -> list:
    """搜索历史日志"""
    results = []
    if not _LOGS_DIR.exists():
        return results
    
    for fpath in sorted(_LOGS_DIR.glob("*.md"), reverse=True):
        if fpath.name == "README.md":
            continue
        try:
            content = fpath.read_text(encoding='utf-8')
            if keyword.lower() in content.lower():
                # 提取匹配条目标题
                for line in content.split('\n'):
                    if line.startswith('## ') and keyword.lower() in line.lower():
                        results.append({
                            "date": fpath.stem,
                            "title": line.replace('## ', '').strip(),
                            "file": str(fpath)
                        })
        except:
            continue
        if len(results) >= max_results:
            break
    return results

def list_logs(days: int = 7) -> list:
    """列出最近N天的日志概览"""
    results = []
    if not _LOGS_DIR.exists():
        return results
    
    today = datetime.date.today()
    for i in range(days):
        target = today - datetime.timedelta(days=i)
        fp = _LOGS_DIR / f"{target.isoformat()}.md"
        if fp.exists():
            content = fp.read_text(encoding='utf-8')
            entries = [l.replace('## ', '').strip() 
                      for l in content.split('\n') 
                      if l.startswith('## ')]
            results.append({
                "date": target.isoformat(),
                "entries": len(entries),
                "titles": entries
            })
    return results


if __name__ == "__main__":
    import sys
    if len(sys.argv) > 1:
        cmd = sys.argv[1]
        if cmd == "write" and len(sys.argv) >= 3:
            fp = write_log(sys.argv[2], sys.argv[3] if len(sys.argv) > 3 else "")
            print(f"已写入: {fp}")
        elif cmd == "search" and len(sys.argv) >= 3:
            for r in search_logs(sys.argv[2]):
                print(f"  {r['date']} | {r['title']}")
        elif cmd == "list":
            for d in list_logs():
                print(f"  {d['date']}: {d['entries']} 条目")
        elif cmd == "template" and len(sys.argv) >= 3:
            print(log_template(sys.argv[2]))
        else:
            print("用法: python tools/l35_log.py <write|search|list|template> [args]")
    else:
        print(f"日志目录: {_LOGS_DIR}")
        print(f"今日文件: {_today_path()}")
