# -*- coding: utf-8 -*-
"""
Agent 状态定义 - 相当于智能体的"记忆"
"""
from typing import List, Dict, Any, Optional, TypedDict, Annotated
from langgraph.graph.message import add_messages


class PlanStep(TypedDict):
    """单个计划步骤"""
    step_id: int
    tool: str  # 工具名称：sql_query, pandas_execute, plot_chart
    args: Dict[str, Any]  # 参数
    status: str  # pending, running, done, failed


class AgentState(TypedDict):
    """
    Agent 的核心记忆结构
    所有节点共享这个状态
    """
    # ----- 基础字段 -----
    messages: List[Dict[str, Any]]
    # messages: Annotated[list, add_messages]  # 对话历史（自动追加）
    query: str  # 当前用户问题
    session_id: str  # 会话ID

    # ----- 规划相关 -----
    plan: List[PlanStep]  # 当前计划步骤列表
    current_step: int  # 当前执行到第几步
    max_steps: int  # 最大步骤数（防死循环）

    # ----- 执行相关 -----
    tool_results: List[Dict[str, Any]]  # 各步骤执行结果
    final_answer: Optional[str]  # 最终答案

    # ----- 反思相关 -----
    reflection_log: List[str]  # 反思日志
    is_on_track: bool  # 是否偏离目标
    replan_count: int  # 重规划次数

    # ----- 错误处理 -----
    retry_count: int  # 当前步骤重试次数
    error_log: List[str]  # 错误日志

    # ----- 执行日志（用于前端展示） -----
    execution_log: List[Dict[str, Any]]  # 执行日志
