# -*- coding: utf-8 -*-
"""
安全沙盒执行器 - 带自愈能力的代码执行器
"""
import ast
import sqlparse
import re
from typing import Dict, Any, Tuple
from src.models.client import model_router


class SafeExecutor:
    """安全沙盒执行器"""

    def __init__(self):
        self.max_retries = 3
        self.fix_history = []

    # ========== 静态语法检查 ==========
    def check_sql_syntax(self, sql: str) -> Tuple[bool, str]:
        """检查SQL语法（基本检查）"""
        sql = sql.strip().upper()

        # 危险操作黑名单
        dangerous_keywords = ['DROP', 'DELETE', 'UPDATE', 'INSERT', 'ALTER', 'CREATE']
        for kw in dangerous_keywords:
            if kw in sql and 'SELECT' not in sql:
                return False, f"包含危险操作: {kw}"

        # 基本语法检查
        if not sql.startswith('SELECT'):
            return False, "只允许 SELECT 查询"

        return True, "OK"

    def check_python_syntax(self, code: str) -> Tuple[bool, str]:
        """检查Python语法（使用AST）"""
        try:
            ast.parse(code)

            # 危险函数黑名单
            dangerous_funcs = ['eval', 'exec', '__import__', 'open', 'file']
            for func in dangerous_funcs:
                if func in code:
                    return False, f"包含危险函数: {func}"

            return True, "OK"
        except SyntaxError as e:
            return False, f"语法错误: {e}"

    # ========== 修复器（Fixer Agent） ==========
    def fix_code(self, code: str, error: str, lang: str = "sql") -> str:
        """用LLM修复代码"""
        print(f"🔧 [Fixer] 尝试修复 {lang} 代码 (第 {len(self.fix_history) + 1} 次)")

        prompt = f"""你是一个代码修复专家。以下代码执行时出现错误，请修复它。

语言: {lang}
代码: 
{code}
错误信息:
{error}

请只输出修复后的完整代码，不要其他解释：
"""

        model = model_router.get("code")
        response = model.invoke(prompt)
        fixed_code = response.content.strip()

        # 提取代码块
        if '```' in fixed_code:
            match = re.search(r'```(?:\w+)?\n(.*?)\n```', fixed_code, re.DOTALL)
            if match:
                fixed_code = match.group(1)

        self.fix_history.append({
            "original": code,
            "fixed": fixed_code,
            "error": error,
            "attempt": len(self.fix_history) + 1
        })

        return fixed_code

    # ========== 安全执行（含自愈循环） ==========
    def execute_sql(self, sql: str, mock_data: list = None) -> Dict[str, Any]:
        """安全执行SQL（带自愈）"""
        current_sql = sql
        attempt = 0

        while attempt < self.max_retries:
            # 1. 静态检查
            ok, msg = self.check_sql_syntax(current_sql)
            if not ok:
                # 如果是第一次尝试或还有重试次数，尝试修复
                if attempt < self.max_retries - 1:
                    print(f"⚠️ 静态检查失败: {msg}")
                    current_sql = self.fix_code(current_sql, msg, "sql")
                    attempt += 1
                    continue
                else:
                    return {"success": False, "error": msg, "fixed": False}

            # 2. Mock模式执行
            if mock_data is not None:
                return self._execute_mock_sql(current_sql, mock_data)

            # 3. 真实执行
            from src.tools.sql_executor import sql_executor
            result = sql_executor.execute(current_sql)

            if result.get("success"):
                return {"success": True, "data": result.get("data"), "fixed": attempt > 0}

            # 执行失败，尝试修复
            error = result.get("error", "未知错误")
            if attempt < self.max_retries - 1:
                print(f"⚠️ SQL执行失败: {error}")
                current_sql = self.fix_code(current_sql, error, "sql")
                attempt += 1
            else:
                return {"success": False, "error": error, "fixed": False}

        return {"success": False, "error": "超过最大重试次数", "fixed": False}

    def _execute_mock_sql(self, sql: str, mock_data: list) -> Dict[str, Any]:
        """在Mock数据上试运行SQL"""
        import pandas as pd
        from io import StringIO

        try:
            df = pd.DataFrame(mock_data)
            # 使用 DuckDB 或 Pandas 模拟 SQL
            # 简化版：直接返回mock数据
            return {"success": True, "data": mock_data, "mock": True}
        except Exception as e:
            return {"success": False, "error": str(e), "mock": True}

    def get_fix_history(self) -> list:
        """获取修复历史"""
        return self.fix_history


safe_executor = SafeExecutor()
