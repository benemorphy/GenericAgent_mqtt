"""
Curiosity Hooks — 感知工具的好奇心信号检测器

为 file_read / web_scan / code_run(dir) 等感知工具提供
"好奇心信号检测"，在工具返回时自动注册 CuriositySignal。

用法:
    from tools.curiosity_hooks import check_file_read_curiosity, check_web_scan_curiosity, check_code_run_curiosity
    signal = check_file_read_curiosity(path, content, dashboard.last_scan_time)
    if signal: dashboard.register_curiosity(signal)
"""

import os
from typing import Optional
from tools.constraint_dashboard import CuriositySignal

# ── 文件读取好奇心检测 ──

def check_file_read_curiosity(
    path: str,
    content: str,
    last_scan_time: Optional[float] = None,
) -> Optional[CuriositySignal]:
    """检测 file_read 结果中的好奇心信号

    Args:
        path: 被读取的文件路径
        content: 读取到的内容（截断后）
        last_scan_time: 上次扫描时间戳, None表示首次

    Returns:
        如果检测到值得好奇的信号, 返回 CuriositySignal; 否则 None
    """
    if not os.path.isfile(path):
        return None

    # 1. 检测文件大小异常
    try:
        size = os.path.getsize(path)
    except OSError:
        size = 0

    # 大文件触发好奇心 (>500KB 有意义的大文件)
    if size > 500 * 1024:
        return CuriositySignal(
            type="anomaly",
            source="file_read",
            target=path,
            reason=f"文件 {os.path.basename(path)} 体积达 {size//1024}KB, 值得关注",
            severity=min(0.5 + (size / (10*1024*1024)) * 0.3, 0.8),
        )

    # 2. 检测内容中是否包含可疑关键词（如密钥文件、TODO等）
    if content and isinstance(content, str):
        triggers = [
            ("FIXME", "TODO", "HACK", "XXX"),  # 代码标记
            ("password", "secret", "api_key", "token"),  # 凭证风险
            ("deprecated", "obsolete"),  # 废弃标记
        ]
        matched = []
        for group in triggers:
            for kw in group:
                if kw.lower() in content.lower():
                    matched.append(kw)
                    break  # 每组只取一个
        if matched:
            return CuriositySignal(
                type="pattern",
                source="file_read",
                target=path,
                reason=f"文件 {os.path.basename(path)} 含标记: {', '.join(matched)}",
                severity=0.6,
            )

    return None


# ── Web扫描好奇心检测 ──

def check_web_scan_curiosity(
    tabs_only: bool,
    result_text: str,
) -> Optional[CuriositySignal]:
    """检测 web_scan 返回中的好奇心信号

    Args:
        tabs_only: 是否仅扫描了标签页
        result_text: web_scan 返回的文本（json + html）

    Returns:
        如果检测到值得好奇的信号, 返回 CuriositySignal; 否则 None
    """
    if not result_text:
        return None

    # 确保 result_text 是字符串
    if not isinstance(result_text, str):
        return None

    # 检测是否有新标签页
    if 'tabs_count' in result_text.lower() or '"tabs_count"' in result_text:
        import json
        try:
            # 尝试解析JSON中的tab信息
            data = json.loads(result_text.split('```')[0]) if '```' in result_text else json.loads(result_text)
            tabs = data.get('tabs', [])
            titles = [t.get('title', '') for t in tabs if isinstance(t, dict)]
            # 检查是否有看起来有趣的页面
            interesting_keywords = ['arxiv', 'paper', 'github', 'research', 'blog', 'doc']
            for title in titles:
                for kw in interesting_keywords:
                    if kw.lower() in title.lower():
                        return CuriositySignal(
                            type="connection",
                            source="web_scan",
                            target=title,
                            reason=f"浏览器中有含 '{kw}' 标签页: {title[:50]}",
                            severity=0.65,
                        )
        except (json.JSONDecodeError, KeyError, TypeError):
            pass

    return None


# ── 代码执行(dir命令)好奇心检测 ──

def check_code_run_curiosity(
    code_type: str,
    code: str,
    result_text: str,
) -> Optional[CuriositySignal]:
    """检测 code_run (特别是dir/ls) 结果中的好奇心信号

    Args:
        code_type: 代码类型 (python/powershell/bash)
        code: 执行的代码
        result_text: 执行结果

    Returns:
        如果检测到值得好奇的信号, 返回 CuriositySignal; 否则 None
    """
    if not result_text or not code:
        return None

    # 检测是否是目录列举命令
    is_dir_cmd = False
    code_lower = code.strip().lower()
    if code_type == 'powershell':
        is_dir_cmd = code_lower.startswith('dir ') or code_lower.startswith('ls ') or code_lower.startswith('get-childitem')
    elif code_type == 'python':
        is_dir_cmd = 'listdir' in code_lower or 'scandir' in code_lower or 'glob' in code_lower or 'walk' in code_lower
    elif code_type in ('bash', 'sh', 'shell'):
        is_dir_cmd = code_lower.startswith('ls ') or code_lower.startswith('find ')

    if not is_dir_cmd:
        return None

    # 分析结果中的文件
    lines = result_text.split('\n')
    py_files = [l for l in lines if l.strip().endswith('.py') and 'Mode' not in l and '---' not in l]
    other_scripts = [l for l in lines if any(l.strip().endswith(ext) for ext in ['.js', '.ts', '.rs', '.go', '.sh', '.ps1'])]

    signals = []

    # 新文件(未跟踪)检测 - 实际上无法从目录列表判断是否"新"
    # 但可以检测是否有大量Python文件
    if len(py_files) > 10:
        signals.append(CuriositySignal(
            type="pattern",
            source="code_run(dir)",
            target=os.path.basename(os.path.dirname(os.path.abspath('.'))),
            reason=f"目录下有 {len(py_files)} 个 Python 文件, 值得了解项目结构",
            severity=0.55,
        ))

    # 检测是否有混合语言项目
    if py_files and other_scripts:
        ext_types = set()
        for l in other_scripts:
            for ext in ['.js', '.ts', '.rs', '.go', '.sh', '.ps1']:
                if l.strip().endswith(ext):
                    ext_types.add(ext)
        if ext_types:
            signals.append(CuriositySignal(
                type="connection",
                source="code_run(dir)",
                target="project",
                reason=f"项目含多种语言: Python + {', '.join(ext_types)}, 可能有跨语言架构",
                severity=0.6,
            ))

    if signals:
        # 返回最高优先级信号
        return max(signals, key=lambda s: s.severity)

    return None


# ── 通用入口: 注册到仪表盘 ──

def try_register_curiosity(handler, signal: Optional[CuriositySignal]) -> bool:
    """尝试向 handler 的仪表盘注册好奇心信号（安全调用，不会抛异常）

    Args:
        handler: GenericAgentHandler 实例
        signal: 好奇心信号（可能为None）

    Returns:
        是否成功注册
    """
    if signal is None:
        return False
    dashboard = getattr(handler, '_constraint_dashboard', None)
    if dashboard is None:
        return False
    try:
        return dashboard.register_curiosity(signal)
    except Exception:
        return False
