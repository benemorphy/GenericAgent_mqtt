"""
gbrain MCP 工具封装 (garrytan/gbrain)

通过 subprocess 调用 gbrain CLI，提供知识检索与图谱能力。
GA Agent 可通过此模块查询 gbrain 大脑。

前提: bun 已安装，gbrain 仓库已 clone 到 GBRAIN_REPO 路径。
"""

import subprocess
import json
import os
from pathlib import Path

# ── 配置 ──
GBRAIN_REPO = Path("D:/open_claw_agent/gbrain")
BUN = os.environ.get("BUN_PATH", "bun")

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
    cmd = [BUN, "run", str(GBRAIN_REPO / "src/cli.ts"), *args]
    return subprocess.run(
        cmd,
        capture_output=True, text=True,
        timeout=timeout, cwd=str(GBRAIN_REPO)
    )


def available_tools() -> list[str]:
    """返回支持的 gbrain 工具名列表"""
    return _TOOLS.copy()


def gbrain_query(question: str, sources: list[str] | None = None) -> dict:
    """向 gbrain 提问，返回带引用的合成答案

    参数:
        question: 问题字符串
        sources:  限定搜索源（可选）
    返回:
        {answer, citations, sources, gap_analysis}
    """
    args = ["query", question, "--json"]
    if sources:
        args.extend(["--sources", ",".join(sources)])
    r = _run_gbrain(*args)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain query failed: {r.stderr}")
    return json.loads(r.stdout)


def gbrain_search(query: str, limit: int = 10) -> dict:
    """搜索 gbrain 知识库

    参数:
        query: 搜索关键词
        limit: 最大结果数
    返回:
        {results, total}
    """
    args = ["search", query, "--json", "--limit", str(limit)]
    r = _run_gbrain(*args)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain search failed: {r.stderr}")
    return json.loads(r.stdout)


def gbrain_think(prompt: str) -> dict:
    """让 gbrain 进行链式思考分析

    参数:
        prompt: 分析提示
    返回:
        {reasoning, answer, confidence}
    """
    args = ["think", prompt, "--json"]
    r = _run_gbrain(*args, timeout=120)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain think failed: {r.stderr}")
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
    return json.loads(r.stdout)


def gbrain_get_page(slug: str) -> dict:
    """获取单个知识页面

    参数:
        slug: 页面标识
    返回:
        页面内容 dict
    """
    r = _run_gbrain("get", slug, "--json")
    if r.returncode != 0:
        raise RuntimeError(f"gbrain get failed: {r.stderr}")
    return json.loads(r.stdout)


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
        raise RuntimeError(f"gbrain put failed: {r.stderr}")
    return json.loads(r.stdout)


def gbrain_list_pages(prefix: str = "") -> list[dict]:
    """列出知识页面

    参数:
        prefix: 可选前缀过滤
    返回:
        页面列表
    """
    args = ["list", "--json"]
    if prefix:
        args.extend(["--prefix", prefix])
    r = _run_gbrain(*args)
    if r.returncode != 0:
        raise RuntimeError(f"gbrain list failed: {r.stderr}")
    return json.loads(r.stdout)


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
        {initialized, page_count, graph_size, uptime}
    """
    r = _run_gbrain("status", "--json")
    if r.returncode != 0:
        return {"initialized": False, "error": r.stderr.strip()}
    return json.loads(r.stdout)


def gbrain_init() -> dict:
    """初始化本地 gbrain 大脑 (PGLite)

    返回:
        初始化结果
    """
    r = _run_gbrain("init", "--yes", timeout=30)
    if r.returncode != 0:
        return {"ok": False, "error": r.stderr.strip()}
    return {"ok": True, "message": r.stdout.strip()}
