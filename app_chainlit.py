# -*- coding: utf-8 -*-
"""
Chainlit 前端 - Aurora-Insight（干净版）
"""
import chainlit as cl
import httpx
import json
import uuid

API_URL = "http://localhost:8000"


@cl.on_chat_start
async def start():
    # ========== 新增：生成并存储 session_id ==========
    session_id = str(uuid.uuid4())
    cl.user_session.set("session_id", session_id)
    print(f"🆕 新会话，session_id: {session_id}")
    # ================================================
    await cl.Message(
        content="""🚀 欢迎使用 **Aurora-Insight**！

我可以帮你分析数据库中的销售数据。

**试试问我：**
- 帮我分析一下销售数据
- 哪个产品销售最好
- 画一下销量统计图

💡 我会展示完整的思考过程。"""
    ).send()


@cl.on_message
async def main(message: cl.Message):
    query = message.content
    if not query:
        return
    # ========== 新增：从用户会话中获取 session_id ==========
    session_id = cl.user_session.get("session_id")
    if not session_id:
        session_id = str(uuid.uuid4())
        cl.user_session.set("session_id", session_id)
    # =======================================================

    msg = cl.Message(content="⏳ 处理中...")
    await msg.send()

    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            async with client.stream(
                "POST",
                f"{API_URL}/stream",
                json={
                    "query": query,
                    "session_id": session_id
                      }
            ) as response:

                if response.status_code != 200:
                    msg.content = f"❌ 错误: {response.status_code}"
                    await msg.update()
                    return

                display_lines = []
                final_answer = ""

                async for line in response.aiter_lines():
                    if not line.startswith("data: "):
                        continue
                    try:
                        event = json.loads(line[6:])
                    except:
                        continue

                    typ = event.get("type", "")
                    data = event.get("data", "")

                    # 规划阶段
                    if typ == "planning":
                        display_lines.append("📋 **规划阶段**")
                        display_lines.append("")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                    elif typ == "planning_step":
                        display_lines.append(f"  {data}")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                    # 执行阶段 - 只显示关键信息，不显示代码
                    elif typ == "executing":
                        display_lines.append("")
                        display_lines.append("🔧 **执行阶段**")
                        display_lines.append("")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                    elif typ == "executing_step":
                        step = data
                        # 跳过 SQL 代码块和 Pandas 代码块
                        if step.strip().startswith("```sql"):
                            continue
                        if step.strip().startswith("```python"):
                            continue
                        # 只显示自然语言描述
                        if not step.strip().startswith("```"):
                            display_lines.append(f"  {step}")
                            msg.content = "\n".join(display_lines)
                            await msg.update()

                    # 反思阶段
                    elif typ == "reflection":
                        display_lines.append("")
                        display_lines.append("🔍 **反思阶段**")
                        display_lines.append("")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                    elif typ == "reflection_step":
                        display_lines.append(f"  {data}")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                    # 验证阶段
                    elif typ == "validating":
                        display_lines.append("")
                        display_lines.append("✅ **验证阶段**")
                        display_lines.append("")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                    # 最终答案
                    elif typ == "final":
                        final_answer = data
                        display_lines.append("")
                        display_lines.append("📊 **最终结果**")
                        display_lines.append("")
                        display_lines.append(f"{final_answer}")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                        # 🔥 如果答案包含图表路径，显示图片
                        if "图表已生成" in final_answer:
                            import os
                            chart_path = final_answer.split(": ")[-1].strip()
                            if os.path.exists(chart_path):
                                await cl.Message(
                                    content="📊 **图表**",
                                    elements=[cl.Image(path=chart_path, name="分析图表")]
                                ).send()

                    # 错误
                    elif typ == "error":
                        display_lines.append("")
                        display_lines.append(f"❌ **错误**")
                        display_lines.append(f"{data}")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                    # 完成
                    elif typ == "end":
                        duration = event.get("duration", 0)
                        display_lines.append("")
                        display_lines.append(f"✅ 完成 ⏱️ {duration}s")
                        msg.content = "\n".join(display_lines)
                        await msg.update()

                if not final_answer:
                    msg.content = "⚠️ 未获取到回答"
                    await msg.update()

    except httpx.TimeoutException:
        msg.content = "⏰ 请求超时，请重试"
        await msg.update()
    except httpx.ConnectError:
        msg.content = "❌ 无法连接到 API 服务，请确保 `python run.py` 正在运行"
        await msg.update()
    except Exception as e:
        msg.content = f"❌ 错误: {str(e)}"
        await msg.update()