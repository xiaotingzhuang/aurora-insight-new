# -*- coding: utf-8 -*-
"""
自定义评估体系 - 替代 Ragas（更稳定）
"""
import json
import asyncio
import re
from typing import List, Dict, Any
from datetime import datetime
import os
from src.agent.agent import agent

# ===== 测试数据集（30个典型业务问句） =====
TEST_QUERIES = [
    # 使用更准确的关键词（匹配实际表字段）
    {"query": "帮我分析一下销售数据", "expected_keywords": ["销售", "数据", "查询", "SQL"]},
    {"query": "哪个产品销售最好", "expected_keywords": ["产品", "销售", "最高", "好"]},
    {"query": "哪个产品销售最差", "expected_keywords": ["产品", "销售", "最低", "差"]},
    {"query": "Q3销售额是多少", "expected_keywords": ["Q3", "销售", "额", "3"]},
    {"query": "华东地区卖了多少", "expected_keywords": ["华东", "销售", "数据", "额"]},
    {"query": "华南地区卖了多少", "expected_keywords": ["华南", "销售", "数据", "额"]},
    {"query": "华北地区卖了多少", "expected_keywords": ["华北", "销售", "数据", "额"]},
    # ... 继续完善
]


class CustomEvaluator:
    """自定义评估器"""

    def __init__(self, output_dir="tests/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []

    def evaluate_keyword_match(self, answer: str, keywords: List[str]) -> float:
        """计算关键词匹配率"""
        if not answer or not keywords:
            return 0.0

        answer_lower = answer.lower()
        matched = 0
        for kw in keywords:
            if kw.lower() in answer_lower:
                matched += 1

        return matched / len(keywords)

    def evaluate_answer_quality(self, answer: str) -> Dict[str, Any]:
        """评估答案质量"""
        scores = {}

        # 1. 长度得分（答案不能太短也不能太长）
        length = len(answer)
        if 10 <= length <= 200:
            scores["length_score"] = 1.0
        elif length < 10:
            scores["length_score"] = 0.3
        else:
            scores["length_score"] = 0.8

        # 2. 中文占比（应该以中文为主）
        chinese_chars = len(re.findall(r'[\u4e00-\u9fa5]', answer))
        total_chars = len(answer) or 1
        scores["chinese_ratio"] = chinese_chars / total_chars

        # 3. 是否有数字（数据分析应该包含数字）
        has_number = bool(re.search(r'\d+', answer))
        scores["has_number"] = 1.0 if has_number else 0.0

        return scores

    async def run_agent_async(self, query: str) -> Dict:
        """异步执行 Agent"""
        try:
            result = await agent.invoke(query)
            return {
                "query": query,
                "answer": result.get("answer", ""),
                "success": True,
                "metadata": result.get("metadata", {})
            }
        except Exception as e:
            return {
                "query": query,
                "answer": f"执行失败: {str(e)}",
                "success": False,
                "error": str(e)
            }

    def run_sync(self, query: str) -> Dict:
        """同步执行 Agent"""
        return asyncio.run(self.run_agent_async(query))

    def collect_results(self) -> List[Dict]:
        """收集所有测试结果"""
        print(f"📊 开始评估 {len(TEST_QUERIES)} 个测试用例...")
        print("=" * 50)

        results = []
        for i, test_case in enumerate(TEST_QUERIES, 1):
            query = test_case["query"]
            keywords = test_case["expected_keywords"]

            print(f"  [{i}/{len(TEST_QUERIES)}] 测试: {query[:40]}...", end=" ")

            result = self.run_sync(query)
            result["expected_keywords"] = keywords

            # 计算关键词匹配率
            if result.get("success"):
                match_rate = self.evaluate_keyword_match(
                    result.get("answer", ""),
                    keywords
                )
                result["keyword_match_rate"] = match_rate
                print(f"✅ 匹配率: {match_rate * 100:.0f}%")
            else:
                result["keyword_match_rate"] = 0.0
                print(f"❌ 失败")

            # 答案质量
            if result.get("success"):
                quality = self.evaluate_answer_quality(result.get("answer", ""))
                result["quality"] = quality

            results.append(result)

        self.results = results
        return results

    def print_summary(self):
        """打印评估摘要"""
        if not self.results:
            print("⚠️ 没有评估结果")
            return

        print("\n" + "=" * 50)
        print("📊 评估摘要")
        print("=" * 50)

        # 统计基本信息
        total = len(self.results)
        success_count = sum(1 for r in self.results if r.get("success", False))
        failed_count = total - success_count

        print(f"总用例: {total}")
        print(f"成功: {success_count} ({success_count / total * 100:.1f}%)")
        print(f"失败: {failed_count} ({failed_count / total * 100:.1f}%)")

        # FastPath 统计
        fastpath_count = sum(1 for r in self.results
                             if r.get("metadata", {}).get("fastpath", False))
        print(f"FastPath 命中: {fastpath_count} ({fastpath_count / total * 100:.1f}%)")

        # 关键词匹配率统计
        match_rates = [r.get("keyword_match_rate", 0) for r in self.results if r.get("success")]
        if match_rates:
            avg_match = sum(match_rates) / len(match_rates)
            print(f"\n📈 关键词平均匹配率: {avg_match * 100:.1f}%")

            # 分级统计
            high = sum(1 for m in match_rates if m >= 0.8)
            mid = sum(1 for m in match_rates if 0.5 <= m < 0.8)
            low = sum(1 for m in match_rates if m < 0.5)
            print(f"  高匹配率 (>80%): {high} 个")
            print(f"  中匹配率 (50-80%): {mid} 个")
            print(f"  低匹配率 (<50%): {low} 个")

        # 答案质量统计
        if self.results and "quality" in self.results[0]:
            avg_length_score = 0
            avg_chinese_ratio = 0
            avg_has_number = 0
            count = 0

            for r in self.results:
                if "quality" in r and r.get("success"):
                    q = r["quality"]
                    avg_length_score += q.get("length_score", 0)
                    avg_chinese_ratio += q.get("chinese_ratio", 0)
                    avg_has_number += q.get("has_number", 0)
                    count += 1

            if count > 0:
                print(f"\n📊 答案质量:")
                print(f"  长度得分: {avg_length_score / count:.2f}")
                print(f"  中文占比: {avg_chinese_ratio / count:.2f}")
                print(f"  包含数字: {avg_has_number / count * 100:.0f}%")

        # 保存结果
        self.save_results()
        print("=" * 50)

    def save_results(self):
        """保存评估结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        detail_file = f"{self.output_dir}/eval_results_{timestamp}.json"

        with open(detail_file, "w", encoding="utf-8") as f:
            json.dump(self.results, f, ensure_ascii=False, indent=2)

        print(f"\n💾 结果已保存到: {detail_file}")


def main():
    """主函数"""
    print("🚀 启动自定义评估")
    print("=" * 50)

    evaluator = CustomEvaluator()

    # 1. 收集结果
    evaluator.collect_results()

    # 2. 打印摘要
    evaluator.print_summary()


if __name__ == "__main__":
    main()