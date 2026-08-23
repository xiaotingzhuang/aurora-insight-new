# -*- coding: utf-8 -*-
"""
SQL 执行器 - 真实数据库查询
"""
import sqlalchemy
from sqlalchemy import create_engine, text
import os
from dotenv import load_dotenv

load_dotenv()


class SQLExecutor:
    def __init__(self):
        # 从环境变量读取数据库配置
        self.engine = create_engine(
            f"postgresql://{os.getenv('POSTGRES_USER')}:{os.getenv('POSTGRES_PASSWORD')}"
            f"@{os.getenv('POSTGRES_HOST')}:{os.getenv('POSTGRES_PORT')}/{os.getenv('POSTGRES_DB')}"
        )

    def execute(self, sql: str) -> dict:
        """执行SQL查询并返回结果"""
        try:
            with self.engine.connect() as conn:
                result = conn.execute(text(sql))
                rows = result.fetchall()
                columns = result.keys()

                # 转换为字典列表
                data = [dict(zip(columns, row)) for row in rows]

                return {
                    "success": True,
                    "data": data,
                    "row_count": len(data)
                }
        except Exception as e:
            return {
                "success": False,
                "error": str(e)
            }


# 全局实例
sql_executor = SQLExecutor()
