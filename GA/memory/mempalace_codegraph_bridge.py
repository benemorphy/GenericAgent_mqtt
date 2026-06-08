"""
MemPalace ↔ CodeGraph 混合检索桥梁

并行查询 MemPalace 语义搜索 + CodeGraph 代码分析，
按 cosine/匹配度融合结果。

Usage:
    from memory.mempalace_codegraph_bridge import hybrid_search
    results = hybrid_search("BoardService 心跳超时", n_mem=3, n_code=5)
"""

import sys, os
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from typing import List, Optional

_GA_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if _GA_ROOT not in sys.path:
    sys.path.insert(0, _GA_ROOT)


@dataclass
class SearchResult:
    """单个搜索结果"""
    source: str          # 'memory' | 'code'
    title: str           # 文件名或符号名
    content: str         # 摘要内容
    score: float         # cosine (memory) 或 估算匹配度 (code)
    file_path: str = ""  # 文件路径
    detail: dict = field(default_factory=dict)


def _search_mem(query: str, n_results: int = 3) -> List[SearchResult]:
    """语义搜索 MemPalace"""
    try:
        from memory.mempalace_bridge import semantic_search
        raw = semantic_search(query, n_results=n_results)
        results = []
        for item in raw:
            results.append(SearchResult(
                source="memory",
                title=item.get("source", "?"),
                content=item.get("content", ""),
                score=item.get("cosine", 0.0),
                detail=item,
            ))
        return results
    except Exception as e:
        return [SearchResult(source="memory", title="[错误]", content=str(e), score=0.0)]


def _search_code(query: str, n_results: int = 5) -> List[SearchResult]:
    """代码搜索 CodeGraph"""
    try:
        from tools.codegraph_mcp import codegraph_call
        
        results = []
        
        # 1. 通用符号搜索
        try:
            raw = codegraph_call("codegraph_search", {"query": query}, workspace=_GA_ROOT)
            if isinstance(raw, dict) and raw.get("status") == "success":
                data = raw.get("data", [])
                if isinstance(data, list):
                    for item in data[:n_results]:
                        node = item.get("node", item)
                        name = node.get("name", "?") or node.get("qualifiedName", "?")
                        fpath = node.get("filePath", "") or node.get("file", "")
                        kind = node.get("kind", "")
                        results.append(SearchResult(
                            source="code",
                            title=name,
                            content=f"{kind}: {fpath}",
                            score=0.5 + (item.get("score", 0) / 100),
                            file_path=fpath,
                            detail=item,
                        ))
        except Exception:
            pass
        
        # 2. 文件名搜索 (降级)
        if len(results) < n_results:
            try:
                raw2 = codegraph_call("codegraph_files", {}, workspace=_GA_ROOT)
                if isinstance(raw2, dict) and raw2.get("status") == "success":
                    files = raw2.get("data", [])
                    if isinstance(files, list):
                        q_lower = query.lower()
                        matched = [f for f in files if q_lower in str(f).lower()]
                        for f in matched[:n_results - len(results)]:
                            results.append(SearchResult(
                                source="code",
                                title=os.path.basename(str(f)) if isinstance(f, str) else str(f),
                                content=str(f),
                                score=0.3,
                                file_path=str(f),
                            ))
            except Exception:
                pass
        
        return results[:n_results]
    except Exception as e:
        return [SearchResult(source="code", title="[错误]", content=str(e), score=0.0)]


def hybrid_search(query: str, n_mem: int = 3, n_code: int = 5,
                  mem_weight: float = 1.0, code_weight: float = 0.7) -> List[SearchResult]:
    """
    混合检索入口：并行查 MemPalace + CodeGraph

    Args:
        query: 查询关键词
        n_mem: MemPalace 返回数量
        n_code: CodeGraph 返回数量
        mem_weight: MemPalace 结果的权重乘数
        code_weight: CodeGraph 结果的权重乘数

    Returns:
        按 score 降序排列的合并结果列表
    """
    mem_results = []
    code_results = []

    with ThreadPoolExecutor(max_workers=2) as pool:
        mem_future = pool.submit(_search_mem, query, n_mem)
        code_future = pool.submit(_search_code, query, n_code)

        for future in as_completed([mem_future, code_future]):
            try:
                result = future.result()
                if future == mem_future:
                    mem_results = result
                else:
                    code_results = result
            except Exception as e:
                pass  # 单路失败不影响另一路

    # 合并 + 加权排序
    merged = []
    for r in mem_results:
        r.score *= mem_weight
        merged.append(r)
    for r in code_results:
        r.score *= code_weight
        merged.append(r)

    merged.sort(key=lambda x: x.score, reverse=True)
    return merged


def format_results(results: List[SearchResult], top_n: int = 8) -> str:
    """格式化结果供显示"""
    if not results:
        return "[hybrid_search] 无结果"
    
    lines = [f"[hybrid_search] 共 {len(results)} 条结果:"]
    for i, r in enumerate(results[:top_n]):
        tag = "mem" if r.source == "memory" else "cod"
        lines.append(f"  #{i+1} [{tag}] score={r.score:.3f} {r.title}")
        if r.content:
            lines.append(f"       {r.content[:120]}")
        if r.file_path:
            lines.append(f"       {r.file_path}")
    return "\n".join(lines)
