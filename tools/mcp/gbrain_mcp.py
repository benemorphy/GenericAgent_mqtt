"""
gbrain MCP 工具封装 (garrytan/gbrain)

通过 subprocess 调用 gbrain CLI，提供知识检索与图谱能力。
GA Agent 可通过此模块查询 gbrain 大脑。

前提: bun 已安装，gbrain 仓库已 clone 到 GBRAIN_REPO 路径。
"""

import subprocess
import json
import os
import re
from pathlib import Path

try:
    from memory.keychain import keys
    _API_KEY = keys.deepseek_api_key.use()
except Exception:
    _API_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

# ── 配置 ──
GBRAIN_REPO = Path("D:/open_claw_agent/gbrain")
BUN = os.environ.get("BUN_PATH", r"C:\Users\user\AppData\Roaming\npm\bun.CMD")


def _get_env() -> dict:
    """返回包含 DEEPSEEK_API_KEY 的环境变量"""
    env = os.environ.copy()
    if _API_KEY:
        env["DEEPSEEK_API_KEY"] = _API_KEY
    return env


# ── 可用工具清单 ──
_TOOLS = [
    "gbrain_query",
    "gbrain_search",
    "gbrain_think",
    "gbrain_graph_query",
    "gbrain_get_page",
    "gbrain_put_page",
    "gbrain_list_pages",
    "gbrain_list_skills",
    "gbrain_init",
    "gbrain_status",
]


def _run_gbrain(*args: str, timeout: int = 60) -> subprocess.CompletedProcess:
    """运行 gbrain CLI 命令"""
    if not GBRAIN_REPO.exists():
        raise FileNotFoundError(f"gbrain repository not found at {GBRAIN_REPO}")
    cmd = [str(BUN), "run", str(GBRAIN_REPO / "src/cli.ts"), *args]
    return subprocess.run(
        cmd,
        capture_output=True, text=True,
        timeout=timeout, cwd=str(GBRAIN_REPO),
        env=_get_env()
    )


def available_tools() -> list[str]:
    """返回支持的 gbrain 工具名列表"""
    return _TOOLS.copy()


# ── 自定义格式解析器 ──

def _parse_search_query_output(text: str) -> list[dict]:
    """解析 gbrain search/query 输出格式: [score] slug -- title\\nsnippet\\n...

    返回: [{score, slug, title, snippet}, ...]
    """
    results = []
    # 每条结果以 [score] 开头
    entries = re.split(r'\n(?=\[)', text.strip())
    for entry in entries:
        entry = entry.strip()
        if not entry:
            continue
        # 第一行: [score] slug -- title
        m = re.match(r'\[([^\]]+)\]\s+(\S+)\s+--\s+(.*)', entry)
        if not m:
            continue
        score_str = m.group(1)
        slug = m.group(2)
        title = m.group(3)
        # 剩余行为 snippet
        snippet = entry[m.end():].strip()
        results.append({
            "score": score_str,
            "slug": slug,
            "title": title,
            "snippet": snippet,
        })
    return results


def _parse_get_output(text: str) -> dict:
    """解析 gbrain get 输出: YAML frontmatter ---\\n...\\n---\\n\\ncontent

    返回: {type, title, content, ...}
    """
    result = {}
    # 提取 YAML frontmatter
    m = re.match(r'^---\s*\n(.*?)\n---\s*\n(.*)', text, re.DOTALL)
    if m:
        yaml_block = m.group(1)
        result["content"] = m.group(2).strip()
        for line in yaml_block.strip().split('\n'):
            if ':' in line:
                key, val = line.split(':', 1)
                result[key.strip()] = val.strip()
    else:
        result["content"] = text.strip()
    return result


def _parse_list_output(text: str) -> list[dict]:
    """解析 gbrain list 输出: TSV slug\\ttype\\tdate\\ttitle\\n

    返回: [{slug, type, date, title}, ...]
    """
    results = []
    for line in text.strip().split('\n'):
        line = line.strip()
        if not line:
            continue
        parts = line.split('\t')
        if len(parts) >= 4:
            results.append({
                "slug": parts[0],
                "type": parts[1],
                "date": parts[2],
                "title": parts[3],
            })
        elif len(parts) >= 1:
            results.append({"slug": parts[0]})
    return results


# ── 公共 API ──

def gbrain_query(question: str, sources: list[str] | None = None) -> list[dict]:
    """向 gbrain 提问，返回搜索结果列表

    参数:
        question: 问题字符串
        sources:  限定搜索源（可选）
    返回:
        [{score, slug, title, snippet}, ...]
    """
    args = ["query", question, "--json"]
    if sources:
        args.extend(["--sources", ",".join(sources)])
    r = _run_gbrain(*args)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain query failed: {r.stderr}")
    return _parse_search_query_output(r.stdout)


def gbrain_search(query: str, limit: int = 10) -> list[dict]:
    """搜索 gbrain 知识库

    参数:
        query: 搜索关键词
        limit: 最大结果数
    返回:
        [{score, slug, title, snippet}, ...]
    """
    args = ["search", query, "--json", "--limit", str(limit)]
    r = _run_gbrain(*args)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain search failed: {r.stderr}")
    return _parse_search_query_output(r.stdout)


def gbrain_think(prompt: str) -> dict:
    """让 gbrain 进行链式思考分析

    参数:
        prompt: 分析提示
    返回:
        {question, answer, citations, gaps, ...}
    """
    args = ["think", prompt, "--json"]
    r = _run_gbrain(*args, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain think failed: {r.stderr}")
    # think 输出是标准 JSON
    return json.loads(r.stdout)


def gbrain_graph_query(slug: str, depth: int = 2) -> dict:
    """知识图谱遍历查询

    参数:
        slug: 实体节点标识
        depth: 遍历深度（默认2层）
    返回:
        {nodes, edges}
    """
    args = ["graph-query", slug, "--depth", str(depth), "--json"]
    r = _run_gbrain(*args)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain graph-query failed: {r.stderr}")
    # 尝试解析 JSON，失败则返回文本
    try:
        return json.loads(r.stdout)
    except json.JSONDecodeError:
        return {"text": r.stdout.strip(), "nodes": [], "edges": []}


def gbrain_get_page(slug: str) -> dict:
    """获取单个知识页面

    参数:
        slug: 页面标识
    返回:
        {type, title, content, ...}
    """
    r = _run_gbrain("get", slug, "--json")
    if r.returncode != 0:
        raise RuntimeError(f"gbrain get failed: {r.stderr}")
    return _parse_get_output(r.stdout)


def gbrain_put_page(slug: str, content: str) -> dict:
    """写入知识页面

    参数:
        slug:    页面标识
        content: Markdown 内容
    返回:
        操作结果
    """
    r = _run_gbrain("put", slug, content, "--json")
    if r.returncode != 0:
        return {"success": False, "error": r.stderr.strip() or r.stdout.strip()}
    return {"success": True, "slug": slug}


def gbrain_list_pages(prefix: str = "") -> list[dict]:
    """列出知识页面

    参数:
        prefix: 可选前缀过滤
    返回:
        [{slug, type, date, title}, ...]
    """
    args = ["list", "--json"]
    if prefix:
        args.extend(["--prefix", prefix])
    r = _run_gbrain(*args)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain list failed: {r.stderr}")
    return _parse_list_output(r.stdout)


def gbrain_list_skills() -> list[dict]:
    """列出可用技能

    返回:
        技能列表
    """
    r = _run_gbrain("skillpack", "list", "--json")
    if r.returncode != 0:
        raise RuntimeError(f"gbrain skillpack list failed: {r.stderr}")
    return json.loads(r.stdout)


def gbrain_status() -> dict:
    """检查 gbrain 大脑状态

    返回:
        {schema_version, generated_at, mode, sync, cycle, locks, workers, queue, autopilot}
    """
    r = _run_gbrain("status", "--json")
    if r.returncode != 0:
        return {"initialized": False, "error": r.stderr.strip()}
    return json.loads(r.stdout)


def gbrain_init() -> dict:
    """初始化 gbrain 大脑（首次使用）

    返回:
        初始化结果
    """
    r = _run_gbrain("init", "--json")
    return {"success": r.returncode == 0, "output": r.stdout.strip(), "error": r.stderr.strip() or None}
