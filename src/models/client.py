# -*- coding: utf-8 -*-
"""
模型客户端 - 纯DeepSeek方案
"""
from langchain_deepseek import ChatDeepSeek
import os
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()


class ModelRouter:
    """DeepSeek模型路由器"""

    def __init__(self):
        api_key = os.getenv("DEEPSEEK_API_KEY")
        if not api_key:
            raise ValueError("❌ 请在.env中配置DEEPSEEK_API_KEY")

        print(f"✅ DeepSeek API已配置")

        # 默认模型（参数保持不变）
        self.default_model = ChatDeepSeek(
            model="deepseek-chat",
            api_key=api_key,
            temperature=0.1,
            max_tokens=4096,
            timeout=60
        )

        # 不同任务使用不同参数
        self.task_configs = {
            "reasoning": {"temperature": 0.1},  # 推理任务
            "code": {"temperature": 0.0},  # 代码生成（更确定性）
            "fast": {"temperature": 0.1, "max_tokens": 512},  # 快速响应
            "creative": {"temperature": 0.7}  # 创意任务
        }

    def get(self, task_type: str = "reasoning"):
        """根据任务类型获取模型"""
        config = self.task_configs.get(task_type, self.task_configs["reasoning"])

        return ChatDeepSeek(
            model="deepseek-chat",
            api_key=os.getenv("DEEPSEEK_API_KEY"),
            temperature=config.get("temperature", 0.1),
            max_tokens=config.get("max_tokens", 4096),
            timeout=60
        )

    def get_default(self):
        """获取默认模型"""
        return self.default_model


# 创建全局实例
model_router = ModelRouter()

# 测试代码（直接运行此文件可测试）
if __name__ == "__main__":
    print("🧪 测试模型连接...")
    try:
        model = model_router.get_default()
        response = model.invoke("请用一句话介绍数据分析")
        print(f"✅ 模型响应: {response.content}")
    except Exception as e:
        print(f"❌ 连接失败: {e}")
