"""
LangGraph 多智能体编排模块 — 三层组合架构中的编排引擎层
======================================================
┌──────────────────────────────────────┐
│  Node UI (可视化编排层)               │
├──────────────────────────────────────┤
│  LangGraph (编排引擎层) ← 本模块     │
├──────────────────────────────────────┤
│  多智能体 (执行层)                    │
└──────────────────────────────────────┘

本模块实现:
1. 三个 Agent 节点: SearchAgent / AnalyzeAgent / SummaryAgent
2. StateGraph 串联，支持条件分支与循环
3. 可被 Node UI 导入并可视化
"""

from typing import TypedDict, Literal, List, Dict
from langgraph.graph import StateGraph, END
import os
import sys

# ===== 状态定义 =====

class AgentState(TypedDict):
    """多智能体协作的共享状态"""
    task: str                     # 原始任务描述
    data_input: str               # DataSource节点输入数据
    search_results: str           # 搜索结果
    analysis: str                 # 分析结果
    summary: str                  # 最终总结
    iteration: int                # 当前迭代次数
    max_iterations: int           # 最大迭代次数
    reflection: str               # 反省记录
    logs: List[Dict[str, str]]    # 执行日志


# ===== Agent 节点函数 =====

def search_agent(state: AgentState) -> dict:
    """Agent A: 搜索智能体 - 执行信息检索"""
    task = state["task"]
    print(f"[SearchAgent] 搜索任务: {task}")
    
    # 实际运行中会调用 Metaso / Bing 等搜索工具
    # 当前为演示，使用模拟数据
    try:
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
        from tools.utils.metaso_search import metaso_search_text
        results = metaso_search_text(task, size=3)
        search_results = results if results else f"搜索 '{task}' 未找到结果"
    except Exception:
        search_results = f"[搜索模拟] 针对'{task}'的检索结果:\n" + \
                         "1. 相关文档 A...\n2. 相关文档 B...\n3. 相关文档 C..."
    
    return {
        "search_results": search_results,
        "logs": state["logs"] + [{"agent": "SearchAgent", "output": search_results[:100]}]
    }


def analyze_agent(state: AgentState) -> dict:
    """Agent B: 分析智能体 - 对搜索结果进行分析"""
    search_results = state["search_results"]
    task = state["task"]
    data_input = state.get("data_input", "")
    print(f"[AnalyzeAgent] 分析搜索结果... (data_input长度={len(data_input)})")
    
    analysis = f"[分析结果]\n任务: {task}\n"
    if data_input:
        analysis += f"【用户输入数据】:\n{data_input[:500]}\n\n"
    analysis += f"基于以下搜索结果的分析:\n{search_results[:300]}...\n"
    analysis += "→ 核心发现: ...\n→ 关键数据: ...\n→ 建议方向: ..."
    
    return {
        "analysis": analysis,
        "logs": state["logs"] + [{"agent": "AnalyzeAgent", "output": analysis[:100]}]
    }


def summary_agent(state: AgentState) -> dict:
    """Agent C: 总结智能体 - 生成最终总结"""
    task = state["task"]
    analysis = state["analysis"]
    print("[SummaryAgent] 生成总结...")
    
    summary = f"# {task}\n\n"
    summary += "## 摘要\n基于多智能体协作分析结果...\n\n"
    summary += "## 关键发现\n- ...\n\n"
    summary += "## 结论\n..."
    
    return {
        "summary": summary,
        "logs": state["logs"] + [{"agent": "SummaryAgent", "output": "总结完成"}]
    }


def reflection_agent(state: AgentState) -> dict:
    """Agent R: 反省智能体 - 检查结果质量，决定是否重试"""
    iteration = state["iteration"]
    max_iterations = state["max_iterations"]
    
    reflection = f"第{iteration}轮反省: "
    
    if iteration < max_iterations:
        # 模拟质量检查
        quality_ok = iteration > 1  # 第二次迭代后认为质量达标
        if quality_ok:
            reflection += "质量达标，结束"
            return {"reflection": reflection, "summary": state["summary"] + "\n(已通过反省验证)"}
        else:
            reflection += "质量不足，继续迭代"
            return {"reflection": reflection, "iteration": iteration + 1}
    else:
        reflection += "已达最大迭代次数，结束"
        return {"reflection": reflection}


# ===== 条件路由函数 =====

def route_from_analysis(state: AgentState) -> Literal["summary", "search", "__end__"]:
    """根据分析结果决定下一步"""
    # 演示逻辑: 如果有严重问题则重搜，否则总结
    if "error" in state.get("analysis", "").lower():
        return "search"
    else:
        return "summary"


def route_from_reflection(state: AgentState) -> Literal["search", "__end__"]:
    """根据反省结果决定是否重来"""
    if state.get("iteration", 0) < state.get("max_iterations", 3):
        return "search"  # 继续迭代
    else:
        return "__end__"


# ===== 构建 LangGraph =====

def build_multi_agent_graph(max_iterations: int = 3) -> StateGraph:
    """
    构建多智能体编排图
    
    流程: search → analyze → (分支) → summary → reflection → (循环/结束)
    """
    workflow = StateGraph(AgentState)
    
    # 添加节点
    workflow.add_node("search", search_agent)
    workflow.add_node("analyze", analyze_agent)
    workflow.add_node("summary", summary_agent)
    workflow.add_node("reflect", reflection_agent)
    
    # 添加边 - 主流程
    workflow.set_entry_point("search")
    workflow.add_edge("search", "analyze")
    workflow.add_conditional_edges(
        "analyze",
        route_from_analysis,
        {
            "search": "search",
            "summary": "summary",
            "__end__": END
        }
    )
    workflow.add_edge("summary", "reflect")
    workflow.add_conditional_edges(
        "reflect",
        route_from_reflection,
        {
            "search": "search",
            "__end__": END
        }
    )
    
    return workflow.compile()


# ===== Node 元数据（供 Node UI 可视化使用） =====

NODE_DEFINITIONS = [
    {
        "type": "search",
        "label": "🔍 SearchAgent",
        "description": "搜索智能体 - 执行信息检索",
        "inputs": [{"name": "task", "type": "str"}],
        "outputs": [{"name": "search_results", "type": "str"}]
    },
    {
        "type": "analyze",
        "label": "📊 AnalyzeAgent",
        "description": "分析智能体 - 对搜索结果进行分析",
        "inputs": [{"name": "search_results", "type": "str"}],
        "outputs": [{"name": "analysis", "type": "str"}]
    },
    {
        "type": "summary",
        "label": "📝 SummaryAgent",
        "description": "总结智能体 - 生成最终总结",
        "inputs": [{"name": "analysis", "type": "str"}],
        "outputs": [{"name": "summary", "type": "str"}]
    },
    {
        "type": "reflect",
        "label": "🔄 ReflectionAgent",
        "description": "反省智能体 - 检查质量、决定重试或结束",
        "inputs": [{"name": "summary", "type": "str"}],
        "outputs": [{"name": "action", "type": "str"}]
    }
]


# ===== 便捷运行入口 =====

def run_pipeline(task: str, max_iterations: int = 2, data_input: str = "") -> AgentState:
    """运行完整的多智能体流水线"""
    app = build_multi_agent_graph(max_iterations)
    
    initial_state: AgentState = {
        "task": task,
        "data_input": data_input,
        "search_results": "",
        "analysis": "",
        "summary": "",
        "iteration": 1,
        "max_iterations": max_iterations,
        "reflection": "",
        "logs": []
    }
    
    final_state = app.invoke(initial_state)
    return final_state


if __name__ == "__main__":
    # 测试运行
    result = run_pipeline("多智能体系统协作规范研究")
    print("\n" + "="*50)
    print("最终输出:")
    print(result.get("summary", "无输出")[:500])
    print("\n迭代次数:", result.get("iteration", 0))
    print("执行日志:", len(result.get("logs", [])))