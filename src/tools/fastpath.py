# -*- coding: utf-8 -*-
"""
FastPath 成本控制 - 简单问题快速路由
"""
import re
from typing import Tuple, Optional
from src.models.client import model_router


class FastPathRouter:
    """快速路由器 - 判断是否走 FastPath"""

    # 简单问候词
    GREETING_KEYWORDS = ['你好', '您好', 'hi', 'hello', 'hey', '嗨', '大家好']
    SIMPLE_QA_KEYWORDS = ['什么是', '是什么', '介绍一下', '介绍下', '怎么理解']

    def should_use_fastpath(self, query: str) -> Tuple[bool, Optional[str]]:
        """
        判断是否使用 FastPath
        返回: (是否使用, 直接回答内容)
        """
        query_lower = query.lower()

        # 规则1：问候语 → 直接返回
        for kw in self.GREETING_KEYWORDS:
            if kw in query_lower:
                return True, self._handle_greeting(query)

        # 规则2：超短问题（长度 < 2）→ 直接返回
        if len(query) < 2:
            return True, "请说得更具体一些，我才能更好地帮助你。"

        # 规则3：简单问答 → 用快速模型
        for kw in self.SIMPLE_QA_KEYWORDS:
            if kw in query_lower:
                return True, self._handle_simple_qa(query)

        # 其他情况 → 走主链路
        return False, None

    def _handle_greeting(self, query: str) -> str:
        """处理问候"""
        return "你好！我是 Aurora-Insight，一个企业级数据分析智能体。请问有什么可以帮你的？"

    def _handle_simple_qa(self, query: str) -> str:
        """处理简单问答（用快速模型）"""
        try:
            model = model_router.get("fast")
            response = model.invoke(f"请用简洁的一句话回答：{query}")
            return response.content
        except Exception as e:
            return f"暂时无法回答这个问题（错误: {str(e)}）"

    def fast_answer(self, query: str) -> dict:
        """执行 FastPath 回答"""
        should_use, answer = self.should_use_fastpath(query)
        if should_use and answer:
            return {
                "answer": answer,
                "metadata": {
                    "fastpath": True,
                    "model": "fast" if answer != self._handle_greeting(query) else "none"
                }
            }
        return None


fastpath_router = FastPathRouter()
