# -*- coding: utf-8 -*-
"""
LangGraph 状态图 - 使用 MemorySaver（开发环境）
"""
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver
from src.agent.state import AgentState
from src.agent.nodes import (
    planner_node, executor_node, reflector_node, replan_node, should_continue
)


def build_graph():
    workflow = StateGraph(AgentState)

    workflow.add_node("planner", planner_node)
    workflow.add_node("executor", executor_node)
    workflow.add_node("reflector", reflector_node)
    workflow.add_node("replan", replan_node)

    workflow.set_entry_point("planner")
    workflow.add_edge("planner", "executor")

    workflow.add_conditional_edges(
        "executor",
        should_continue,
        {
            "execute": "executor",
            "reflector": "reflector",
            "replan": "replan",
            "end": END
        }
    )

    workflow.add_conditional_edges(
        "reflector",
        should_continue,
        {
            "execute": "executor",
            "replan": "replan",
            "end": END
        }
    )

    workflow.add_edge("replan", "executor")

    # ===== 使用 MemorySaver =====
    checkpointer = MemorySaver()

    return workflow.compile(checkpointer=checkpointer)


_graph = None


def get_graph():
    global _graph
    if _graph is None:
        _graph = build_graph()
    return _graph
