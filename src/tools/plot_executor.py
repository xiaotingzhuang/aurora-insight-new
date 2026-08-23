# -*- coding: utf-8 -*-
"""
图表生成器 - 支持从数据自动提取
"""
import matplotlib.pyplot as plt
import os
import pandas as pd
import matplotlib

try:
    matplotlib.rcParams['font.sans-serif'] = ['Microsoft YaHei', 'SimHei', 'PingFang SC', 'Noto Sans CJK SC']
    matplotlib.rcParams['axes.unicode_minus'] = False
except:
    pass


class PlotExecutor:
    def __init__(self, output_dir="data/charts"):
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)
        self._chart_counter = 0

    def generate(self, chart_type: str, data: dict = None, title: str = "图表") -> dict:
        try:
            # 数据校验和转换
            if data and 'y' in data:
                # 确保 y 是数字列表
                data['y'] = [float(v) if isinstance(v, (int, float)) else 0 for v in data['y']]
            # 如果 data 为空，用模拟数据
            if not data:
                data = self._get_sample_data(chart_type)

            plt.figure(figsize=(10, 6))

            if chart_type == "bar":
                x = data.get('x', list(range(len(data.get('y', [])))))
                y = data.get('y', [])
                plt.bar(x, y, color='steelblue')
                for i, v in enumerate(y):
                    plt.text(i, v + max(y) * 0.02, str(v), ha='center', fontsize=9)

            elif chart_type == "line":
                x = data.get('x', list(range(len(data.get('y', [])))))
                y = data.get('y', [])
                plt.plot(x, y, marker='o', linewidth=2, markersize=8)

            elif chart_type == "pie":
                labels = data.get('labels', data.get('x', []))
                values = data.get('values', data.get('y', []))
                plt.pie(values, labels=labels, autopct='%1.1f%%', startangle=90)
                plt.axis('equal')

            else:
                x = data.get('x', list(range(len(data.get('y', [])))))
                y = data.get('y', [])
                plt.bar(x, y, color='steelblue')

            plt.title(title, fontsize=14, fontweight='bold')
            plt.xticks(rotation=45)
            plt.tight_layout()

            self._chart_counter += 1
            filename = f"{self.output_dir}/chart_{self._chart_counter}.png"
            plt.savefig(filename, dpi=150)
            plt.close()

            return {
                "success": True,
                "filename": filename,
                "message": f"图表已保存到 {filename}"
            }

        except Exception as e:
            return {"success": False, "error": str(e)}

    def _get_sample_data(self, chart_type: str) -> dict:
        """获取示例数据（当 data 为空时）"""
        if chart_type == "bar" or chart_type == "line":
            return {
                "x": ["iPhone 15", "MacBook Pro", "AirPods Pro", "iPad Pro"],
                "y": [285000, 690000, 165000, 110000]
            }
        elif chart_type == "pie":
            return {
                "labels": ["iPhone 15", "MacBook Pro", "AirPods Pro", "iPad Pro"],
                "values": [285000, 690000, 165000, 110000]
            }
        return {
            "x": ["A", "B", "C", "D"],
            "y": [100, 200, 150, 300]
        }


plot_executor = PlotExecutor()
