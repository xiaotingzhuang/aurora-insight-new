# -*- coding: utf-8 -*-
"""
Pandas 数据分析执行器 - 完整版
支持：数据加载、数据预览、统计分析、数据清洗、数据转换、分组聚合、合并连接、时间序列、自定义计算
"""
import pandas as pd
import io
import sys
import json
import numpy as np
from typing import Dict, Any, List, Optional, Union


class PandasExecutor:
    """Pandas 数据分析执行器 - 完整功能版"""

    def __init__(self):
        self.last_result = None
        self.execution_history = []

    def execute(self, code: str, data: Optional[List[Dict]] = None, **kwargs) -> Dict[str, Any]:
        """
        执行 Pandas 代码

        Args:
            code: 要执行的 Python/Pandas 代码
            data: 输入数据（列表格式，会自动转为 DataFrame）
            **kwargs: 额外参数

        Returns:
            dict: 执行结果
        """
        try:
            # 创建执行环境
            local_vars = self._prepare_environment(data)

            # 捕获输出
            old_stdout = sys.stdout
            sys.stdout = io.StringIO()

            # 执行代码
            exec(code, {}, local_vars)

            # 获取输出
            output = sys.stdout.getvalue()
            sys.stdout = old_stdout

            # 提取结果
            result = self._extract_result(local_vars, output)

            # 保存执行历史
            self.last_result = result
            self.execution_history.append({
                "code": code[:200],
                "result": result.get("result", "")[:200],
                "output": output[:200]
            })

            return {
                "success": True,
                "result": result.get("result", "执行完成"),
                "output": output,
                "data": result.get("data", None),
                "dataframe": result.get("dataframe", None),
                "shape": result.get("shape", None),
                "columns": result.get("columns", None),
                "execution_id": len(self.execution_history)
            }

        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "code": code[:200]
            }

    def _prepare_environment(self, data: Optional[List[Dict]] = None) -> Dict[str, Any]:
        """准备执行环境"""
        local_vars = {}

        # 导入常用库
        local_vars['pd'] = pd
        local_vars['np'] = np
        local_vars['json'] = json

        # 如果有数据，创建 DataFrame
        if data:
            try:
                df = pd.DataFrame(data)
                # 同时定义所有可能用到的变量名
                local_vars['_1'] = df
                local_vars['_'] = df
                local_vars['df'] = df
                local_vars['data'] = df
                local_vars['input_df'] = df
                local_vars['input_data'] = data
            except Exception as e:
                print(f"⚠️ 创建 DataFrame 失败: {e}")
                # 创建空 DataFrame
                local_vars['_1'] = pd.DataFrame()
                local_vars['_'] = pd.DataFrame()
                local_vars['df'] = pd.DataFrame()
        else:
            # 空 DataFrame
            local_vars['_1'] = pd.DataFrame()
            local_vars['_'] = pd.DataFrame()
            local_vars['df'] = pd.DataFrame()

        return local_vars

    def _extract_result(self, local_vars: Dict[str, Any], output: str) -> Dict[str, Any]:
        """从执行环境中提取结果"""
        result = {
            "result": output.strip() or "执行完成",
            "data": None,
            "dataframe": None,
            "shape": None,
            "columns": None
        }

        # 检查常见的变量名
        var_names = ['result', 'res', 'output', 'out', 'ans', 'answer']
        for name in var_names:
            if name in local_vars:
                val = local_vars[name]
                if isinstance(val, pd.DataFrame):
                    result["data"] = val.to_dict('records')
                    result["dataframe"] = True
                    result["shape"] = val.shape
                    result["columns"] = val.columns.tolist()
                    result["result"] = f"DataFrame: {val.shape[0]} 行 × {val.shape[1]} 列"
                elif isinstance(val, dict):
                    result["data"] = val
                    result["result"] = str(val)[:200]
                elif isinstance(val, list):
                    result["data"] = val
                    result["result"] = f"列表: {len(val)} 项"
                elif val is not None:
                    result["result"] = str(val)[:200]
                break

        # 如果 output 有内容但没找到结果变量
        if output.strip() and not result["data"]:
            result["result"] = output.strip()

        return result

    def get_history(self, limit: int = 10) -> List[Dict]:
        """获取执行历史"""
        return self.execution_history[-limit:] if self.execution_history else []

    def clear_history(self):
        """清除执行历史"""
        self.execution_history = []
        self.last_result = None


# 全局单例
pandas_executor = PandasExecutor()
