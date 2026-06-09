"""gbrain 技能 — 注册到 GA Agent 工具链

通过 @TOOL.register() 向 GA Agent 暴露 gbrain 的核心能力。
Agent 可调用 gbrain_query/think/search/graph-query 获取知识。

用法:
    from tools.skills.gbrain_skill import gbrain_query_agent
"""

from tools.agent.registry import TOOL
from tools.mcp.gbrain_mcp import (
    gbrain_query,
    gbrain_search,
    gbrain_think,
    gbrain_graph_query,
)


@TOOL.register()
def gbrain_query_agent(query: str) -> str:
    """向 gbrain 知识库提问，返回带引用的合成答案。

    gbrain 是本地知识库，能对已有信息做合成问答并标注来源。
    适用于: 询问项目知识、查阅历史记录、获取综合结论。

    Args:
        query: 问句 (如 "MQTT BoardService 的工作原理是什么")
    Returns:
        合成答案文本，含引用来源 [source-name]
    """
    try:
        result = gbrain_query(query)
        answer = result.get("answer", "") or ""
        citations = result.get("citations", [])
        if citations:
            answer += "\n\n引用来源:\n" + "\n".join(f"  - {c}" for c in citations)
        if not answer:
            answer = result.get("message", "(gbrain 无结果)")
        return answer
    except Exception as e:
        return f"gbrain 查询失败: {e}"


@TOOL.register()
def gbrain_search_agent(query: str, limit: int = 5) -> str:
    """搜索 gbrain 知识库，返回相关结果列表。

    用于在 gbrain 中查找关键词相关的页面和内容。

    Args:
        query: 搜索关键词
        limit: 返回结果数 (默认 5)
    Returns:
        搜索结果的文本摘要
    """
    try:
        results = gbrain_search(query, limit=limit)
        if not results:
            return "(gbrain 搜索无结果)"
        lines = []
        for i, r in enumerate(results[:limit], 1):
            score = r.get("score", 0)
            title = r.get("title", r.get("slug", "?"))
            content = r.get("content", "")[:100]
            lines.append(f"#{i} [{score:.3f}] {title}")
            if content:
                lines.append(f"    {content}")
        return "\n".join(lines)
    except Exception as e:
        return f"gbrain 搜索失败: {e}"


@TOOL.register()
def gbrain_think_agent(prompt: str) -> str:
    """使用 gbrain 做深度链式推理分析。

    适用于需要多步推理的问题、因果关系分析、假设推演。

    Args:
        prompt: 需要推理的问题或场景描述
    Returns:
        推理结论文本
    """
    try:
        result = gbrain_think(prompt)
        return result.get("answer", "(gbrain 推理无结果)")
    except Exception as e:
        return f"gbrain 推理失败: {e}"


@TOOL.register()
def gbrain_graph_agent(slug: str, depth: int = 2) -> str:
    """查询 gbrain 知识图谱，返回实体关系。

    gbrain 的图谱存储实体之间的命名边关系。

    Args:
        slug: 实体标识
        depth: 遍历深度 (默认 2)
    Returns:
        图谱节点和边的描述
    """
    try:
        result = gbrain_graph_query(slug, depth=depth)
        nodes = result.get("nodes", [])
        edges = result.get("edges", [])
        lines = [f"图谱: {len(nodes)} 节点, {len(edges)} 条边"]
        for n in nodes[:10]:
            lines.append(f"  - {n}")
        for e in edges[:10]:
            lines.append(f"  -- {e}")
        return "\n".join(lines)
    except Exception as e:
        return f"gbrain 图谱查询失败: {e}"
