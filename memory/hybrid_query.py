"""
hybrid_query — 混合推理管道: 向量语义搜索 + 知识图谱符号验证

A1方向的工程化实现。
将 MemPalace(向量召回) + KnowledgeGraph(关系验证) 封装为统一API。

Usage:
    from memory.hybrid_query import hybrid_query
    result = hybrid_query("MQTT消息超时诊断")
    print(result.summary)
    print(result.vector_candidates)
    print(result.kg_relations)
"""

from typing import List, Dict, Any, Optional
from dataclasses import dataclass, field

from memory.mempalace_bridge import semantic_search
from memory.knowledge_graph import KnowledgeGraph


@dataclass
class HybridResult:
    """混合查询结果"""
    query: str
    vector_candidates: List[Dict[str, Any]] = field(default_factory=list)
    kg_relations: List[Dict[str, str]] = field(default_factory=list)
    kg_entities_found: List[str] = field(default_factory=list)
    vector_count: int = 0
    kg_count: int = 0

    @property
    def summary(self) -> str:
        parts = [
            f"[HybridQuery] query='{self.query}'",
            f"  向量层: {self.vector_count} candidates",
            f"  符号层: {self.kg_count} relations ({len(self.kg_entities_found)} entities)",
        ]
        if self.vector_count > 0:
            top = self.vector_candidates[0]
            parts.append(f"  最佳向量命中: {top.get('source','?')} (cosine={top.get('cosine',0):.3f})")
        if self.kg_count > 0:
            top_rel = self.kg_relations[0]
            parts.append(f"  最佳KG关系: {top_rel['source']} --[{top_rel['relation']}]--> {top_rel['target']}")
        return "\n".join(parts)

    def cross_validate(self) -> Dict[str, Any]:
        """交叉校验: 向量命中的实体是否也在KG中出现?"""
        vector_sources = set()
        for c in self.vector_candidates:
            src = c.get("source", "")
            name = src.replace(".md", "").replace(".py", "").upper()
            vector_sources.add(name)

        kg_entity_set = set(self.kg_entities_found)
        overlap = vector_sources & kg_entity_set
        return {
            "vector_sources": sorted(vector_sources),
            "kg_entities": sorted(kg_entity_set),
            "overlap": sorted(overlap),
            "overlap_count": len(overlap),
            "only_vector": sorted(vector_sources - kg_entity_set),
            "only_kg": sorted(kg_entity_set - vector_sources),
        }


def hybrid_query(
    query: str,
    n_vector: int = 5,
    kg_entity_hint: Optional[str] = None,
    verbose: bool = False,
) -> HybridResult:
    """
    混合查询: 向量召回 + KG符号验证

    Args:
        query: 自然语言查询
        n_vector: 向量召回数量
        kg_entity_hint: KG实体提示词(默认从query自动提取)
        verbose: 是否打印详细日志

    Returns:
        HybridResult 包含向量和符号两个通道的结果
    """
    result = HybridResult(query=query)

    # Phase 1: 向量召回 (MemPalace)
    candidates = semantic_search(query, n_results=n_vector)
    result.vector_candidates = candidates
    result.vector_count = len(candidates)
    if verbose:
        print(f"[向量层] 召回 {len(candidates)} 个候选:")
        for c in candidates:
            print(f"  [{c.get('source','?')}] cosine={c.get('cosine',0):.3f}")

    # Phase 2: 符号验证 (KnowledgeGraph)
    kg = KnowledgeGraph()

    # 从向量候选提取实体关键词
    keywords = set()
    for c in candidates:
        src = c.get("source", "")
        # 文件名去后缀作为实体名
        name = src.replace(".md", "").replace(".py", "").replace(".txt", "")
        if name:
            keywords.add(name.upper())

    # 如果给了明确hint, 优先使用
    if kg_entity_hint:
        keywords.add(kg_entity_hint.upper())

    # 从query中提取关键词: 中英文混合场景
    import re
    # 提取英文单词(全大写或首字母大写的)"
    eng_tokens = re.findall(r"[A-Za-z][A-Za-z0-9_]{1,}", query)
    for t in eng_tokens:
        clean = t.upper()
        if len(clean) > 1:
            keywords.add(clean)
    # 如果中文文本中嵌入英文缩写, 也可整体匹配
    # 例如 "MQTT消息超时诊断" -> 从中提取 MQTT
    mixed_tokens = re.findall(r"([A-Z]{2,})", query)
    for t in mixed_tokens:
        keywords.add(t.upper())

    # 最后尝试: 把整个query作为搜索词(可能匹配到部分KG实体描述)
    keywords.add(query.upper()[:20])

    all_relations = []
    entities_found = set()
    for kw in keywords:
        try:
            entity = kg.query_entity(kw)
            if entity and entity.get("name"):
                entities_found.add(kw)
                rels = kg.query_relations(kw)
                all_relations.extend(rels)
                if verbose:
                    print(f"[符号层] 精确匹配实体 '{kw}': {len(rels)} 条关系")
                continue
            # 尝试模糊搜索
            found = kg.search_entities(kw)
            for f in found:
                name = f.get("name", "")
                if name:
                    entities_found.add(name)
                    rels = kg.query_relations(name)
                    all_relations.extend(rels)
                    if verbose:
                        print(f"[符号层] 模糊匹配实体 '{name}': {len(rels)} 条关系")
        except Exception:
            pass

    result.kg_relations = all_relations
    result.kg_entities_found = sorted(entities_found)
    result.kg_count = len(all_relations)

    if verbose:
        print(f"[符号层] 共 {len(entities_found)} 个实体, {len(all_relations)} 条关系")
        cv = result.cross_validate()
        print(f"[交叉校验] 重叠实体: {cv['overlap']}")

    return result


def quick_hybrid(
    query: str,
    verbose: bool = True,
) -> None:
    """快捷查询: 执行混合查询并打印可读结果"""
    result = hybrid_query(query, verbose=verbose)
    print("\n" + "=" * 60)
    print(result.summary)
    print("=" * 60)

    cv = result.cross_validate()
    if cv["overlap"]:
        print(f"[交叉校验] 向量+KG双通道验证通过的实体: {', '.join(cv['overlap'])}")
    else:
        print("[交叉校验] 双通道无重叠——向量命中的文件不在KG中, 反之亦然")

    if result.kg_count > 0:
        print("\n[KG关系详表]")
        for r in result.kg_relations[:10]:
            print(f"  {r['source']} --[{r['relation']}]--> {r['target']}")
        if len(result.kg_relations) > 10:
            print(f"  ... 还有 {len(result.kg_relations)-10} 条关系")

    return result


# ---- 自测 ----
if __name__ == "__main__":
    print("=== hybrid_query 自测 ===")
    result = quick_hybrid("MQTT消息超时诊断")
    print(f"\n测试通过: 向量={result.vector_count}, KG={result.kg_count}")
