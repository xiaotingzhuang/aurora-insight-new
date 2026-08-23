# -*- coding: utf-8 -*-
"""
HyDE 检索增强 - 生成假想SQL，检索相关字段
"""
import json
import os
from typing import List, Dict, Any
from src.models.client import model_router


class HyDERetriever:
    def __init__(self, dict_path="data/dictionary.json"):
        self.dict_path = dict_path
        self.dictionary = self._load_dictionary()

    def _load_dictionary(self) -> Dict[str, Any]:
        """加载数据字典"""
        if os.path.exists(self.dict_path):
            with open(self.dict_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {}

    def generate_hypothetical_sql(self, query: str) -> str:
        """生成假想 SQL"""
        prompt = f"""根据用户问题，生成一个假想的 SQL 查询草稿。

用户问题：{query}

可用表：{list(self.dictionary.keys())}

只输出 SQL 语句，不要其他内容：
"""
        model = model_router.get("code")
        response = model.invoke(prompt)
        return response.content.strip()

    def retrieve_fields(self, query: str, top_k: int = 3) -> List[Dict]:
        """检索相关字段"""
        # 1. 生成假想 SQL
        hypothetical_sql = self.generate_hypothetical_sql(query)
        print(f"🔍 [HyDE] 生成假想SQL: {hypothetical_sql[:100]}...")

        # 2. 从假想 SQL 中提取表名和字段名
        import re
        tables = re.findall(r'FROM\s+(\w+)', hypothetical_sql, re.IGNORECASE)
        fields = re.findall(r'SELECT\s+(.*?)\s+FROM', hypothetical_sql, re.IGNORECASE)

        # 3. 返回匹配的表结构
        results = []
        for table in tables:
            if table in self.dictionary:
                results.append(self.dictionary[table])

        # 如果没匹配到，返回全部
        if not results:
            results = list(self.dictionary.values())

        return results[:top_k]

    def get_context(self, query: str) -> str:
        """获取检索上下文（供规划器使用）"""
        results = self.retrieve_fields(query)
        context = ""
        for table in results:
            context += f"表名: {table.get('table_name')}\n"
            context += f"描述: {table.get('description')}\n"
            context += "字段:\n"
            for field in table.get('fields', []):
                context += f"  - {field['name']} ({field['type']}): {field['description']}\n"
            context += "\n"
        return context


hyde_retriever = HyDERetriever()
