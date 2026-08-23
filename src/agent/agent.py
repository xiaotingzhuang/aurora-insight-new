# -*- coding: utf-8 -*-
"""
Agent 入口 - 支持 Checkpointer 会话持久化
"""
import uuid
from typing import Dict, Any, Optional
from src.agent.graph import get_graph
from src.agent.state import AgentState
from src.tools.fastpath import fastpath_router


class Agent:
    def __init__(self):
        self.graph = get_graph()

    async def invoke(
            self,
            query: str,
            session_id: Optional[str] = None,
            resume: bool = False
    ) -> Dict[str, Any]:
        """
        执行 Agent

        Args:
            query: 用户问题
            session_id: 会话ID（用于多轮对话）
            resume: 是否从检查点恢复
        """

        # ===========  FastPath：先判断是否走快速通道 ===========
        if not resume:  # resume 时不走 fastpath，直接从检查点恢复
            fast_result = fastpath_router.fast_answer(query)
            if fast_result:
                # FastPath 命中，直接返回，不走 LangGraph
                return {
                    "answer": fast_result["answer"],
                    "metadata": fast_result.get("metadata", {}),
                    "execution_log": [{"step": "⚡ FastPath 快速回答"}]
                }

        if not session_id:
            session_id = str(uuid.uuid4())

        # 配置 thread_id 用于 Checkpointer
        config = {"configurable": {"thread_id": session_id}}

        history_state = None
        if not resume:
            try:
                checkpoint_result = await self.graph.aget_state(config)
                if checkpoint_result and checkpoint_result.values:
                    history_state = checkpoint_result.values
                    msg_count = len(history_state.get("messages", []))
                    print(f"📂 恢复历史状态，已有 {msg_count} 条历史消息")
            except Exception as e:
                # 新会话或检查点不存在，忽略
                print(f"📂 新会话，无历史状态")

        if resume:
            # 从检查点恢复（不需要初始状态）
            result = await self.graph.ainvoke(None, config=config)
        else:
            # 新会话：创建初始状态
            initial_state: AgentState = {
                "messages": history_state.get("messages", []) if history_state else [],
                "query": query,
                "session_id": session_id,
                "plan": [],
                "current_step": 0,
                "max_steps": 0,
                "tool_results": [],
                "final_answer": None,
                "reflection_log": [],
                "is_on_track": True,
                "replan_count": 0,
                "retry_count": 0,
                "error_log": [],
                "execution_log": []
            }
            result = await self.graph.ainvoke(initial_state, config=config)

        return {
            "answer": result.get("final_answer") or "处理完成",
            "metadata": {
                "session_id": session_id,
                "steps": len(result.get("tool_results", [])),
                "replans": result.get("replan_count", 0),
                "reflections": len(result.get("reflection_log", []))
            },
            "execution_log": result.get("execution_log", [])  # 确保返回
        }


agent = Agent()
