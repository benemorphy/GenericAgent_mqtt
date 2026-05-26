"""GenericAgent 通用工具函数集 — 从 ga.py 提取的独立工具函数"""

import os, sys, json, re, traceback, itertools, collections, difflib
from datetime import datetime

_GA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def format_error(e):
    """格式化异常信息，包含文件名、行号、函数名和源代码行"""
    exc_type, exc_value, exc_traceback = sys.exc_info()
    tb = traceback.extract_tb(exc_traceback)
    if tb:
        f = tb[-1]
        fname = os.path.basename(f.filename)
        return f"{exc_type.__name__}: {str(e)} @ {fname}:{f.lineno}, {f.name} -> `{f.line}`"
    return f"{exc_type.__name__}: {str(e)}"


def log_memory_access(path):
    """记录 memory/ 下文件的访问统计"""
    if 'memory' not in path:
        return
    stats_file = os.path.join(_GA_ROOT, 'memory', 'file_access_stats.json')
    try:
        with open(stats_file, 'r', encoding='utf-8') as f:
            stats = json.load(f)
    except Exception:
        stats = {}
    fname = os.path.basename(path)
    stats[fname] = {
        'count': stats.get(fname, {}).get('count', 0) + 1,
        'last': datetime.now().strftime('%Y-%m-%d')
    }
    with open(stats_file, 'w', encoding='utf-8') as f:
        json.dump(stats, f, indent=2, ensure_ascii=False)


def expand_file_refs(text, base_dir=None):
    """展开文本中的 {{file:路径:起始行:结束行}} 引用为实际文件内容。
    可与普通文本混排。展开失败抛 ValueError。
    base_dir: 相对路径的基准目录，默认为进程 cwd"""
    pattern = r'\{\{file:(.+?):(\d+):(\d+)\}\}'

    def replacer(match):
        path, start, end = match.group(1), int(match.group(2)), int(match.group(3))
        path = os.path.abspath(os.path.join(base_dir or '.', path))
        if not os.path.isfile(path):
            raise ValueError(f"引用文件不存在: {path}")
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        if start < 1 or end > len(lines) or start > end:
            raise ValueError(f"行号越界: {path} 共{len(lines)}行, 请求{start}-{end}")
        return ''.join(lines[start - 1:end])

    return re.sub(pattern, replacer, text)


def smart_format(data, max_str_len=100, omit_str=' ... '):
    """智能截断字符串，保留头尾"""
    if not isinstance(data, str):
        data = str(data)
    if len(data) < max_str_len + len(omit_str) * 2:
        return data
    return f"{data[:max_str_len // 2]}{omit_str}{data[-max_str_len // 2:]}"


def consume_file(dr, file):
    """读取并删除指定文件（信号文件机制）"""
    if dr and os.path.exists(os.path.join(dr, file)):
        with open(os.path.join(dr, file), encoding='utf-8', errors='replace') as f:
            content = f.read()
        os.remove(os.path.join(dr, file))
        return content


def scan_files(base, depth=2):
    """递归扫描目录中的文件，返回 (name, path) 生成器"""
    try:
        for e in os.scandir(base):
            if e.is_file():
                yield (e.name, e.path)
            elif depth > 0 and e.is_dir(follow_symlinks=False):
                yield from scan_files(e.path, depth - 1)
    except (PermissionError, OSError):
        pass


def fold_earlier(lines):
    """折叠历史中连续的Agent轮次为简洁摘要格式
    
    将连续的 [Agent] 行压缩为 '[Agent]（N turns）' 格式，
    保留 [USER] 消息，保留最后100条。
    """
    FALLBACK = '直接回答了用户问题'
    parts, cnt, last = [], 0, ''
    def flush():
        if cnt:
            if FALLBACK in last: parts.append(f'[Agent]（{cnt} turns）')
            else: parts.append(f'{last}（{cnt} turns）')
    for line in lines:
        if line.startswith('[USER]'):
            flush(); parts.append(line); cnt = 0; last = ''
        else: cnt += 1; last = line
    flush()
    return "\n".join(parts[-100:])


def extract_robust_content(text):
    """从文本中提取<file_content>标签或最后一个代码块的内容"""
    tags = re.findall(r"<file_content[^>]*>(.*?)</file_content>", text, re.DOTALL)
    if tags: return tags[-1].strip()
    blocks = re.findall(r"```[^\n]*\n([\s\S]*?)```", text)
    if blocks: return blocks[-1].strip()
    return None
