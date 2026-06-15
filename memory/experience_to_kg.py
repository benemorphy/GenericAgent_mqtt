"""
experience_to_kg — 自进化知识图谱 (E3方向)

Agent完成任务后自动将经验注入KG，形成自生长的"操作图谱"。

Usage:
    from memory.experience_to_kg import record_experience, record_task_experience
    
    # 简单记录一次经验
    record_experience("MQTT故障诊断", "hybrid_query", "发现MQTT_BBS与GATEWAY关联")
    
    # 完整记录带结果
    result = record_task_experience("GATEWAY", "hybrid_query",
        detail="使用了MemPalace+KG双通道, 召回2候选+8关系",
        success=True, tags=["diagnosis", "mqtt"])

Key Concepts:
    - Entity = Agent完成任务时涉及的主题实体
    - Relation类型: performed(task→tool), produced(tool→outcome), tagged(task→tag)
    - 每个经验自动生成 EXPERIENCE_xxx 实体作为任务节点
"""

from typing import Optional, List
from datetime import datetime
from memory.knowledge_graph import KnowledgeGraph

_EXPERIENCE_COUNTER = 0

def _next_id() -> str:
    """生成自增经验ID。"""
    global _EXPERIENCE_COUNTER
    _EXPERIENCE_COUNTER += 1
    return f"EXP_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{_EXPERIENCE_COUNTER}"


def record_experience(
    task: str,
    tool: str,
    outcome: str,
    kg: Optional[KnowledgeGraph] = None,
    verbose: bool = True,
) -> dict:
    """
    记录一次Agent执行经验到KG。

    Args:
        task: 任务名称 (e.g. "MQTT故障诊断")
        tool: 使用工具名 (e.g. "hybrid_query")
        outcome: 结果描述 (e.g. "发现MQTT_BBS与GATEWAY关联")
        kg: 可复用的KG实例
        verbose: 是否打印日志
    
    Returns:
        dict: {"exp_id": str, "entities_added": int, "relations_added": int}
    """
    own_kg = False
    if kg is None:
        kg = KnowledgeGraph()
        own_kg = True
    
    exp_id = _next_id()
    task_upper = task.upper().replace(" ", "_")[:30]
    tool_upper = tool.upper().replace(" ", "_")[:30]
    
    added = {"entities": 0, "relations": 0}
    
    # 1. 确保任务实体存在
    if kg.add_entity(exp_id, "EXPERIENCE", f"Task: {task}, Tool: {tool}, Outcome: {outcome[:100]}"):
        added["entities"] += 1
    if kg.add_entity(task_upper, "TASK", task):
        added["entities"] += 1
    if kg.add_entity(tool_upper, "TOOL", tool):
        added["entities"] += 1
    if kg.add_entity("OUTCOME_RECORD", "META", "经验记录汇总节点"):
        added["entities"] += 1
    
    # 2. 注入关系
    if kg.add_relation(exp_id, task_upper, "performed", 1.0, f"执行任务: {task}"):
        added["relations"] += 1
    if kg.add_relation(exp_id, tool_upper, "used_tool", 1.0, f"使用工具: {tool}"):
        added["relations"] += 1
    if kg.add_relation(tool_upper, "OUTCOME_RECORD", "produced", 0.8, outcome[:100]):
        added["relations"] += 1
    if kg.add_relation(exp_id, "OUTCOME_RECORD", "resulted_in", 0.9, outcome[:100]):
        added["relations"] += 1
    
    if own_kg:
        kg._get_conn().close()
    
    if verbose:
        print(f"[E3] 经验已注入KG: {exp_id}")
        print(f"      任务={task}, 工具={tool}")
        print(f"      新增 {added['entities']} 实体, {added['relations']} 关系")
    
    return {"exp_id": exp_id, "entities_added": added["entities"], "relations_added": added["relations"]}


def record_task_experience(
    entity: str,
    action: str,
    detail: str = "",
    success: bool = True,
    tags: Optional[List[str]] = None,
    kg: Optional[KnowledgeGraph] = None,
) -> dict:
    """
    记录Agent对某实体的操作经验(增强版)。

    Args:
        entity: 操作涉及的KG实体名 (e.g. "GATEWAY")
        action: 执行的操作 (e.g. "hybrid_query", "diagnose", "restart")
        detail: 操作详情
        success: 是否成功
        tags: 标签列表
    
    Returns:
        dict: 注入统计
    """
    if tags is None:
        tags = []
    
    status = "SUCCESS" if success else "FAILURE"
    outcome = f"{action} {entity}: {detail[:80]} ({status})"
    result = record_experience(
        task=f"{action}_{entity}",
        tool=action,
        outcome=outcome,
        kg=kg,
        verbose=False,
    )
    
    if kg is None:
        kg = KnowledgeGraph()
    
    # 额外: 确认目标实体存在, 加上acted_on关系
    if kg.add_entity(entity.upper(), "TARGET", f"操作目标: {entity}"):
        pass  # 已存在则跳过
    
    rel_added = kg.add_relation(
        result["exp_id"], entity.upper(), "acted_on",
        0.9 if success else 0.5,
        f"{action} -> {entity}: {detail[:80]}"
    )
    if rel_added:
        result["relations_added"] += 1
    
    # 标签关系
    for tag in tags:
        tag_upper = tag.upper().replace(" ", "_")[:20]
        kg.add_entity(tag_upper, "TAG", tag)
        if kg.add_relation(result["exp_id"], tag_upper, "tagged", 0.7, tag):
            result["relations_added"] += 1
    
    print(f"[E3] 任务经验注入完成: {action}->{entity}")
    print(f"      累计 {result['entities_added']} 实体, {result['relations_added']} 关系")
    
    return result


def count_experiences(kg: Optional[KnowledgeGraph] = None) -> int:
    """统计已注入的经验数量。"""
    own_kg = False
    if kg is None:
        kg = KnowledgeGraph()
        own_kg = True
    
    ents = kg.list_entities()
    exp_count = sum(1 for e in ents if e.startswith("EXP_"))
    
    if own_kg:
        kg._get_conn().close()
    
    return exp_count


# ---- 自测 ----
if __name__ == "__main__":
    print("=== experience_to_kg 自测 ===")
    
    kg = KnowledgeGraph()
    before = count_experiences(kg)
    print(f"已有经验数: {before}")
    
    # 测试1: 简单记录
    print("\n--- 测试1: 简单记录 ---")
    r1 = record_experience("KG语义研究", "hybrid_query", "混合推理原型验证通过", kg=kg)
    
    # 测试2: 任务记录
    print("\n--- 测试2: 任务记录 ---")
    r2 = record_task_experience("GATEWAY", "hybrid_query", 
                                "查询GATEWAY得到8条KG关系", 
                                success=True,
                                tags=["diagnosis", "gateway"],
                                kg=kg)
    
    after = count_experiences(kg)
    print(f"\n注入后经验数: {after} (新增 {after - before})")
    
    # 查询验证
    print("\n--- 验证: 列出所有EXPERIENCE实体 ---")
    ents = kg.list_entities()
    exps = [e for e in ents if e.startswith("EXP_")]
    for e in exps:
        rels = kg.query_relations(e)
        print(f"  {e}: {len(rels)} 关系")
        for r in rels[:3]:
            print(f"    {r['source']} --[{r['relation']}]--> {r['target']}")
    
    print("\n所有测试通过!")
