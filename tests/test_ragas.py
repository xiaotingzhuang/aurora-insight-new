# -*- coding: utf-8 -*-
"""
Ragas 评估体系 - 自动化评估 Agent 性能
"""
import json
import asyncio
import pandas as pd
from typing import List, Dict
from datasets import Dataset
from ragas import evaluate
from ragas.metrics import (
    faithfulness,
    answer_relevancy,
    context_recall,
    context_precision,
)
from src.agent.agent import agent
from datetime import datetime
import os

# ===== 测试数据集 =====
TEST_QUERIES = [
    # 基础查询
    {"query": "帮我分析一下销售数据", "expected": "销售数据分析"},
    {"query": "哪个产品销售最好", "expected": "iPhone 15"},
    {"query": "哪个产品销售最差", "expected": "AirPods Pro"},
    {"query": "Q3销售额是多少", "expected": "销售额"},
    {"query": "华东地区卖了多少", "expected": "华东"},
    {"query": "华南地区卖了多少", "expected": "华南"},
    {"query": "华北地区卖了多少", "expected": "华北"},

    # 分类查询
    {"query": "电子产品的销售情况", "expected": "电子产品"},
    {"query": "配件的销售情况", "expected": "配件"},
    {"query": "iPhone 15的销售额", "expected": "iPhone 15"},
    {"query": "MacBook Pro的销售额", "expected": "MacBook Pro"},
    {"query": "AirPods Pro的销售额", "expected": "AirPods Pro"},

    # 时间查询
    {"query": "7月份的销售数据", "expected": "7月"},
    {"query": "8月份的销售数据", "expected": "8月"},
    {"query": "9月份的销售数据", "expected": "9月"},

    # 分析查询
    {"query": "销售额最高的产品", "expected": "最高"},
    {"query": "销售额最低的产品", "expected": "最低"},
    {"query": "各品类销售额对比", "expected": "品类"},
    {"query": "各区域销售额对比", "expected": "区域"},
    {"query": "销量趋势分析", "expected": "趋势"},

    # 综合查询
    {"query": "帮我分析一下各产品的销售表现", "expected": "销售表现"},
    {"query": "哪个区域销售最好", "expected": "区域"},
    {"query": "哪个品类销售最好", "expected": "品类"},
    {"query": "Q3整体销售情况", "expected": "Q3"},
    {"query": "是否有销售异常", "expected": "异常"},

    # 简单问题（FastPath）
    {"query": "你好", "expected": "你好"},
    {"query": "什么是数据分析", "expected": "数据分析"},
    {"query": "介绍一下自己", "expected": "Aurora-Insight"},
]


class RagasEvaluator:
    """Ragas 评估器"""

    def __init__(self, output_dir="tests/results"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self.results = []

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

        results = []
        for i, test_case in enumerate(TEST_QUERIES, 1):
            query = test_case["query"]
            expected = test_case["expected"]

            print(f"  [{i}/{len(TEST_QUERIES)}] 测试: {query[:30]}...")

            result = self.run_sync(query)
            result["expected"] = expected
            results.append(result)

        self.results = results
        return results

    def run_ragas_evaluation(self, results: List[Dict] = None):
        """运行 Ragas 评估"""
        if results is None:
            results = self.results

        # 准备数据
        questions = []
        answers = []

        for r in results:
            questions.append(r["query"])
            answers.append(r.get("answer", ""))

        # 创建数据集
        data = {
            "question": questions,
            "answer": answers,
            "contexts": [[] for _ in range(len(questions))]  # 暂空
        }

        dataset = Dataset.from_dict(data)

        # 运行评估
        print("📈 运行 Ragas 评估...")
        try:
            result = evaluate(
                dataset,
                metrics=[
                    faithfulness,  # 忠实度
                    answer_relevancy,  # 答案相关性
                ],
            )

            # 保存结果
            self.save_results(result, results)
            return result

        except Exception as e:
            print(f"⚠️ Ragas 评估失败: {e}")
            return None

    def save_results(self, ragas_result, raw_results: List[Dict]):
        """保存评估结果"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")

        # 保存详细结果
        detail_file = f"{self.output_dir}/raw_results_{timestamp}.json"
        with open(detail_file, "w", encoding="utf-8") as f:
            json.dump(raw_results, f, ensure_ascii=False, indent=2)

        # 保存汇总结果
        if ragas_result:
            summary_file = f"{self.output_dir}/ragas_summary_{timestamp}.txt"
            with open(summary_file, "w", encoding="utf-8") as f:
                f.write(f"Ragas 评估结果\n")
                f.write(f"{'=' * 50}\n")
                f.write(f"评估时间: {timestamp}\n")
                f.write(f"测试用例数: {len(raw_results)}\n")
                f.write(f"\n评分:\n")
                for key, value in ragas_result.items():
                    if key not in ["contexts"]:
                        f.write(f"  {key}: {value}\n")

            print(f"\n📊 评估结果已保存到:")
            print(f"  详情: {detail_file}")
            print(f"  汇总: {summary_file}")

    def print_summary(self, ragas_result):
        """打印评估摘要"""
        if not ragas_result:
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
        fastpath_count = sum(1 for r in self.results if r.get("metadata", {}).get("fastpath", False))
        print(f"FastPath 命中: {fastpath_count} ({fastpath_count / total * 100:.1f}%)")

        # Ragas 评分
        print("\nRagas 评分:")
        for key, value in ragas_result.items():
            if key not in ["contexts"]:
                if isinstance(value, float):
                    print(f"  {key}: {value:.3f}")
                else:
                    print(f"  {key}: {value}")

        print("=" * 50)


def main():
    """主函数"""
    print("🚀 启动 Ragas 评估")
    print("=" * 50)

    evaluator = RagasEvaluator()

    # 1. 收集结果
    results = evaluator.collect_results()

    # 2. 运行 Ragas 评估
    ragas_result = evaluator.run_ragas_evaluation(results)

    # 3. 打印摘要
    evaluator.print_summary(ragas_result)


if __name__ == "__main__":
    main()