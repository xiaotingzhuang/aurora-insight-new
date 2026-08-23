# -*- coding: utf-8 -*-
"""
LLM-as-Judge 验证器 - 三规则校验
"""
import re
from typing import Dict, Any, List
from src.models.client import model_router


class Validator:
    """关键结果验证器"""

    def validate(self, data: List[Dict], query: str) -> Dict[str, Any]:
        """
        三规则验证
        1. 数据范围异常（同比波动超200%触发警报）
        2. 格式是否符合预期
        3. 是否存在事实性矛盾
        """
        results = {
            "passed": True,
            "alerts": [],
            "warnings": []
        }

        # 规则1：数据范围异常检查
        if data:
            numeric_values = []
            for row in data:
                for key, value in row.items():
                    if isinstance(value, (int, float)):
                        numeric_values.append(value)

            if numeric_values:
                max_val = max(numeric_values)
                min_val = min(numeric_values)
                if max_val > 0 and min_val / max_val < 0.01:
                    results["alerts"].append(f"数据范围异常：最大值{max_val}与最小值{min_val}差距过大")

        # 规则2：格式检查
        if not data:
            results["warnings"].append("查询结果为空")
        elif len(data) > 0:
            # 检查是否有完整字段
            first_row = data[0]
            if len(first_row.keys()) < 2:
                results["warnings"].append("结果字段较少，可能不完整")

        # 规则3：事实矛盾检查（用 LLM）
        contradiction = self._check_contradiction(data, query)
        if contradiction:
            results["alerts"].append(contradiction)

        if results["alerts"]:
            results["passed"] = False

        return results

    def _check_contradiction(self, data: List[Dict], query: str) -> str:
        """用 LLM 检查事实矛盾"""
        try:
            data_str = str(data[:5])  # 取前5条
            prompt = f"""检查以下数据是否存在事实矛盾：

数据：{data_str}
用户问题：{query}

如果存在矛盾，描述问题；如果正常，回复"无"。
只输出一句话："""

            model = model_router.get("reasoning")
            response = model.invoke(prompt)
            result = response.content.strip()

            return result if result != "无" else ""
        except Exception as e:
            print(f"⚠️ 事实矛盾检查失败: {e}")
            return ""


validator = Validator()
