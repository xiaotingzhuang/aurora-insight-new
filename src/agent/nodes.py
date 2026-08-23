# -*- coding: utf-8 -*-
"""
Agent 节点 - 完整版
包含：规划、执行（SQL/Pandas/图表）、反思、重规划、条件判断
"""
import json
import re
from typing import Dict, Any, List
from src.models.client import model_router
from src.agent.state import AgentState, PlanStep
from src.agent.prompts import PLANNER_PROMPT, REFLECTOR_PROMPT
from src.tools.sql_executor import sql_executor
from src.tools.pandas_executor import pandas_executor
from src.tools.plot_executor import plot_executor
from src.tools.safe_executor import safe_executor
from src.tools.hyde_retriever import hyde_retriever
# 在 nodes.py 最顶部，和其他的 import 放在一起


def parse_json(content: str) -> Any:
    """从模型回复中提取JSON - 增强版（带自动补全和容错）"""
    content = content.strip()

    # 尝试直接解析
    try:
        return json.loads(content)
    except:
        pass

    # 尝试提取 ```json ... ``` 中的内容
    match = re.search(r'```json\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass

    # 尝试提取 ``` ... ``` 中的内容（无语言标记）
    match = re.search(r'```\s*(.*?)\s*```', content, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except:
            pass

    # 尝试提取 [...] 或 {...}
    match = re.search(r'(\[.*\]|\{.*\})', content, re.DOTALL)
    if match:
        json_str = match.group(0)
        try:
            return json.loads(json_str)
        except:
            # 尝试自动补全不完整的 JSON
            if json_str.startswith('[') and not json_str.endswith(']'):
                json_str = json_str.rstrip(',') + ']'
                try:
                    return json.loads(json_str)
                except:
                    pass
            if json_str.startswith('{') and not json_str.endswith('}'):
                json_str = json_str.rstrip(',') + '}'
                try:
                    return json.loads(json_str)
                except:
                    pass

    # 尝试用正则提取所有完整的对象
    try:
        objects = re.findall(r'\{[^{}]*\}', content)
        if objects:
            parsed_objects = []
            for obj in objects:
                try:
                    parsed_objects.append(json.loads(obj))
                except:
                    pass
            if parsed_objects:
                return parsed_objects
    except:
        pass

    print(f"⚠️ 无法解析的内容: {content[:200]}...")
    raise ValueError(f"无法解析JSON: {content[:100]}")


# ============================================================
# 节点1：规划器
# ============================================================
def planner_node(state: AgentState) -> Dict[str, Any]:
    print(f"📋 [规划] 问题: {state['query']}")

    query = state['query']

    # ========== 提取历史对话 ==========
    history_messages = state.get("messages", [])
    history_text = ""
    if history_messages:
        history_parts = []
        for msg in history_messages[-6:]:
            role = msg.get("role", "user")
            content = msg.get("content", "")
            if role == "user":
                history_parts.append(f"用户之前问过：{content}")
            elif role == "assistant":
                history_parts.append(f"我之前回答过：{content}")
        history_text = "\n".join(history_parts) if history_parts else ""


    # ========== 检测是否为追问（复用历史数据） ==========
    follow_up_keywords = ['哪个', '最好', '最差', '排名', '对比', '最高', '最低', '多少', '怎么样', '如何', '呢',
                          '那']
    is_follow_up = any(kw in query for kw in follow_up_keywords)

    # 检查是否有历史分析结果可以复用
    tool_results = state.get("tool_results", [])
    has_previous_data = False
    previous_data = None

    if tool_results:
        # 从 tool_results 中提取上一轮的数据
        for item in reversed(tool_results):
            if isinstance(item, dict):
                # 尝试多种数据结构
                if "data" in item and isinstance(item["data"], list) and item["data"]:
                    previous_data = item["data"]
                    has_previous_data = True
                    break
                elif "result" in item and isinstance(item["result"], dict):
                    result_data = item["result"].get("data")
                    if result_data and isinstance(result_data, list) and result_data:
                        previous_data = result_data
                        has_previous_data = True
                        break

    # 如果是追问且有历史数据 → 不走 SQL，直接用 Pandas 分析历史数据
    if is_follow_up and has_previous_data and previous_data:
        print(f"   🔄 检测到追问，复用历史数据（{len(previous_data)} 条）")

        # 构造 Pandas 代码，直接分析上一轮的数据
        pandas_code = f"""
    import pandas as pd

    # 复用上一轮的数据
    df = pd.DataFrame({previous_data[:50]})

    print('📊 基于上一轮分析结果回答用户问题')
    print('数据行数：', len(df))
    print('列名：', df.columns.tolist())

    # 如果用户问"哪个最好""排名"等，找出最值
    numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
    if numeric_cols and len(df) > 0:
        # 找出第一个数值列的最大值对应的行
        col = numeric_cols[0]
        max_row = df.loc[df[col].idxmax()]
        print(f'\\n按 {{col}} 排序，最好的是：')
        print(max_row.to_string())

        # 把所有数据按数值列排序输出
        print(f'\\n所有数据按 {{col}} 降序：')
        print(df.sort_values(col, ascending=False).to_string(index=False))

        result = df.sort_values(col, ascending=False).to_dict('records')
    else:
        print('数据中没有数值列或数据为空')
        result = df.to_dict('records')
    """

        return {
            "plan": [
                {"step_id": 1, "tool": "pandas_execute", "args": {"code": pandas_code}, "status": "pending"},
                {"step_id": 2, "tool": "final_answer", "args": {"answer": "处理完成"}, "status": "pending"}
            ],
            "current_step": 0,
            "max_steps": 2,
            "final_answer": None,
            "tool_results": [],
            "reflection_log": [],
            "is_on_track": True,
            "replan_count": 0,
            "retry_count": 0,
            "error_log": [],
            "execution_log": []
        }

    # ========== 检测是否要求画图 ==========
    chart_keywords = ['画', '图', '图表', '饼状图', '柱状图', '折线图', '可视化', '展示', '显示', '绘制']
    need_chart = any(kw in query for kw in chart_keywords)

    # ========== 检测是否为数据分析问题 ==========
    analysis_keywords = ['分析', '销售', '数据', '查询', '统计', '汇总', '多少', '哪个', '最好', '最差', '销量',
                         '销售额', '产品']
    is_analysis = any(kw in query for kw in analysis_keywords)

    # ========== 用 HyDE 获取表结构 ==========
    context = hyde_retriever.get_context(
        query) or "表名: sales, 字段: product, category, region, sales_amount, quantity, sale_date"

    # ========== 动态生成 SQL ==========
    def generate_sql():
        try:
            model = model_router.get("code")
            sql_prompt = f"""根据用户问题生成 SQL 查询。

用户问题：{query}

数据表结构：
{context}

要求：
1. 只输出 SQL 语句，不要其他内容
2. 如果用户问的是"销量""销售额"，用 SUM/COUNT 聚合
3. 如果用户问"哪个最好""排名"，用 ORDER BY + LIMIT

SQL："""
            response = model.invoke(sql_prompt)
            sql = response.content.strip()

            match = re.search(r'```sql\s*(.*?)\s*```', sql, re.DOTALL)
            if match:
                sql = match.group(1)
            elif sql.startswith('```'):
                sql = sql.strip('`').strip()
            return sql
        except Exception as e:
            print(f"   ⚠️ SQL生成失败: {e}")
            return "SELECT * FROM sales LIMIT 100"

    # ========== 动态生成 Pandas 代码 ==========
    def generate_pandas_code(sql: str):
        try:
            model = model_router.get("code")
            pandas_prompt = f"""根据以下 SQL 查询，生成对应的 Pandas 分析代码。

SQL 查询：
{sql}

用户问题：{query}

要求：
1. 生成的代码要适配这个 SQL 返回的列名
2. 先打印列名：print(df.columns.tolist())
3. 再用正确的列名做分析
4. 只输出 Python 代码，不要其他内容

示例格式：
print('列名:', df.columns.tolist())
# 用实际的列名做分析
print(df.head())
# 如果有数值列，打印统计
numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
if numeric_cols:
    print(df[numeric_cols].describe())

Python代码："""
            response = model.invoke(pandas_prompt)
            code = response.content.strip()

            match = re.search(r'```python\s*(.*?)\s*```', code, re.DOTALL)
            if match:
                code = match.group(1)
            elif code.startswith('```'):
                code = code.strip('`').strip()
            return code
        except Exception as e:
            print(f"   ⚠️ Pandas代码生成失败: {e}")
            return """
print('列名:', df.columns.tolist())
print('数据概览:')
print(df.head())
numeric_cols = df.select_dtypes(include=['number']).columns.tolist()
if numeric_cols:
    print('数值列统计:')
    print(df[numeric_cols].describe())
    print('按第一列分组汇总:')
    group_col = df.columns[0]
    print(df.groupby(group_col)[numeric_cols[0]].sum().sort_values(ascending=False))
"""

    # ========== 数据分析 + 画图 ==========
    if is_analysis and need_chart:
        generated_sql = generate_sql()
        pandas_code = generate_pandas_code(generated_sql)

        chart_type = "bar"
        if "饼" in query or "占比" in query:
            chart_type = "pie"
        elif "折线" in query or "趋势" in query:
            chart_type = "line"

        return {
            "plan": [
                {"step_id": 1, "tool": "sql_query", "args": {"sql": generated_sql}, "status": "pending"},
                {"step_id": 2, "tool": "pandas_execute", "args": {"code": pandas_code}, "status": "pending"},
                {"step_id": 3, "tool": "plot_chart", "args": {"type": chart_type, "title": query[:20], "data": {}},
                 "status": "pending"},
                {"step_id": 4, "tool": "final_answer", "args": {"answer": "处理完成"}, "status": "pending"}
            ],
            "current_step": 0,
            "max_steps": 4,
            "final_answer": None,
            "tool_results": [],
            "reflection_log": [],
            "is_on_track": True,
            "replan_count": 0,
            "retry_count": 0,
            "error_log": [],
            "execution_log": []
        }

    # ========== 数据分析（纯文字） ==========
    if is_analysis:
        generated_sql = generate_sql()
        pandas_code = generate_pandas_code(generated_sql)

        return {
            "plan": [
                {"step_id": 1, "tool": "sql_query", "args": {"sql": generated_sql}, "status": "pending"},
                {"step_id": 2, "tool": "pandas_execute", "args": {"code": pandas_code}, "status": "pending"},
                {"step_id": 3, "tool": "final_answer", "args": {"answer": "处理完成"}, "status": "pending"}
            ],
            "current_step": 0,
            "max_steps": 3,
            "final_answer": None,
            "tool_results": [],
            "reflection_log": [],
            "is_on_track": True,
            "replan_count": 0,
            "retry_count": 0,
            "error_log": [],
            "execution_log": []
        }

    # ========== 其他问题用 LLM 生成计划 ==========
    try:
        context = hyde_retriever.get_context(query) or "暂无可用数据表"
        prompt = PLANNER_PROMPT.format(query=query, context=context, history=history_text)
        model = model_router.get("reasoning")
        response = model.invoke(prompt)
        plan_data = parse_json(response.content)
        if not isinstance(plan_data, list):
            plan_data = [plan_data]
        plan = []
        for i, step in enumerate(plan_data):
            plan.append({
                "step_id": step.get("step_id", i + 1),
                "tool": step.get("tool", "final_answer"),
                "args": step.get("args", {}),
                "status": "pending"
            })
        print(f"✅ 生成 {len(plan)} 个步骤")
    except Exception as e:
        print(f"⚠️ 规划失败: {e}")
        plan = [{"step_id": 1, "tool": "final_answer", "args": {"answer": f"规划失败：{str(e)}"}, "status": "pending"}]

    return {
        "plan": plan,
        "current_step": 0,
        "max_steps": len(plan),
        "final_answer": None,
        "tool_results": [],
        "reflection_log": [],
        "is_on_track": True,
        "replan_count": 0,
        "retry_count": 0,
        "error_log": [],
        "execution_log": []
    }


# ============================================================
# 节点2：执行器
# ============================================================
def executor_node(state: AgentState) -> Dict[str, Any]:
    step_idx = state.get("current_step", 0)
    plan = state.get("plan", [])

    if step_idx >= len(plan):
        return {"current_step": step_idx}

    step = plan[step_idx]
    tool = step.get("tool", "unknown")
    args = step.get("args", {})

    print(f"⚙️ [执行] 步骤 {step_idx + 1}/{len(plan)}: {tool}")
    print(f"   📝 参数: {args}")

    result = None
    final_answer = None
    execution_log = []

    # 失败时停止标志
    should_stop = False

    try:
        if tool == "sql_query":
            sql = args.get("sql", "")
            execution_log.append({"step": f"📝 **生成SQL查询**"})
            # execution_log.append({"step": f"```sql\n{sql}\n```"})
            execution_log.append({"step": f"🔍 **执行查询中...**"})

            result = safe_executor.execute_sql(sql)
            if result.get("success"):
                data = result.get("data", [])
                row_count = len(data)
                execution_log.append({"step": f"✅ SQL执行成功，返回 {row_count} 行数据"})

                # 把数据存到 tool_results 中，供 final_answer 使用
                # result 已经包含 data，会在 return 时存入 tool_results
            else:
                error_msg = result.get('error', '未知错误')
                final_answer = f"SQL查询失败: {error_msg}"
                execution_log.append({"step": f"❌ SQL执行失败: {error_msg}"})
                # SQL失败，停止执行
                should_stop = True

        elif tool == "pandas_execute":
            code = args.get("code", "")
            execution_log.append({"step": f"📝 **生成Pandas分析代码**"})
            # execution_log.append({"step": f"```python\n{code}\n```"})
            execution_log.append({"step": f"🔍 **执行分析中...**"})
            previous_data = None

            if state.get("tool_results"):
                for item in reversed(state["tool_results"]):
                    if isinstance(item, dict):
                        if "data" in item:
                            previous_data = item["data"]
                            break

                        elif "result" in item and isinstance(item["result"], dict) and "data" in item["result"]:
                            previous_data = item["result"]["data"]
                            break

            # 如果没有数据，不继续执行
            if previous_data is None:
                final_answer = "Pandas分析失败：没有可用的数据，请先执行SQL查询。"
                execution_log.append({"step": f"❌ Pandas分析失败：无数据"})
                should_stop = True
                result = {"success": False, "error": "无数据"}
            else:
                result = pandas_executor.execute(code, data=previous_data)

                if result.get("success"):
                    final_answer = None
                    execution_log.append({"step": f"✅ Pandas分析完成"})
                else:
                    error_msg = result.get('error', '未知错误')
                    final_answer = f"Pandas执行失败: {error_msg}"
                    execution_log.append({"step": f"❌ Pandas执行失败: {error_msg}"})
                    # Pandas失败，停止执行
                    should_stop = True

        elif tool == "plot_chart":
            chart_type = args.get("type", "bar")
            title = args.get("title", "数据图表")
            data = args.get("data", {})
            execution_log.append({"step": f"📊 **生成图表: {chart_type}**"})

            if (not data or not data.get('y')) and state.get("tool_results"):
                for item in reversed(state["tool_results"]):
                    if isinstance(item, dict):
                        result_data = None
                        if "result" in item and isinstance(item["result"], dict):
                            result_data = item["result"].get("data")
                        elif "data" in item:
                            result_data = item["data"]

                        if result_data and isinstance(result_data, list) and len(result_data) > 0:
                            first_row = result_data[0]
                            if isinstance(first_row, dict):
                                keys = list(first_row.keys())
                                if len(keys) >= 2:
                                    x_vals = [str(r.get(keys[0], "")) for r in result_data if
                                              r.get(keys[0]) is not None]
                                    y_vals = [float(r.get(keys[1], 0)) for r in result_data if
                                              r.get(keys[1]) is not None]
                                    if x_vals and y_vals:
                                        data = {"x": x_vals, "y": y_vals}
                                        break

            # 如果还是没有数据，生成失败
            if not data or not data.get('y'):
                final_answer = "图表生成失败：没有可用的数据来绘制图表。"
                execution_log.append({"step": f"❌ 图表生成失败：无数据"})
                should_stop = True
                result = {"success": False, "error": "无数据"}
            else:
                result = plot_executor.generate(chart_type, data, title)
                if result.get("success"):
                    final_answer = f"📊 图表已生成: {result.get('filename')}"
                    execution_log.append({"step": f"✅ 图表生成成功"})
                else:
                    error_msg = result.get('error', '未知错误')
                    final_answer = f"图表生成失败: {error_msg}"
                    execution_log.append({"step": f"❌ 图表生成失败: {error_msg}"})
                    # 图表失败，停止执行
                    should_stop = True

        elif tool == "final_answer":
            answer_text = args.get("answer", None)
            if answer_text and answer_text != "处理完成":
                final_answer = answer_text
            else:
                # 从 tool_results 取数据生成回答
                last_data = None
                if state.get("tool_results"):
                    for item in reversed(state["tool_results"]):
                        if isinstance(item, dict):
                            result_data = item.get("result")
                            if isinstance(result_data, dict):
                                if "data" in result_data and isinstance(result_data["data"], list) and result_data["data"]:
                                    last_data = result_data["data"]
                                    break
                                elif "result" in result_data and isinstance(result_data["result"], list) and \
                                        result_data["result"]:
                                    last_data = result_data["result"]
                                    break
                            elif "data" in item and isinstance(item["data"], list) and item["data"]:
                                last_data = item["data"]
                                break

                if last_data:
                    try:
                        sample = last_data[:5] if isinstance(last_data, list) else str(last_data)
                        summary_prompt = f"""请根据以下数据，用中文回答用户的问题。

用户问题：{state['query']}
数据：{sample}

要求：
- 直接回答用户的问题
- 有数字就说数字
- 只输出一句简洁的中文回答"""
                        model = model_router.get("reasoning")
                        response = model.invoke(summary_prompt)
                        final_answer = response.content.strip()
                        execution_log.append({"step": f"✅ 生成回答: {final_answer[:50]}..."})
                    except Exception as e:
                        print(f"⚠️ 总结失败: {e}")
                        final_answer = f"分析完成，数据：{str(last_data)[:200]}..."
                else:
                    # 兜底：没数据时提示用户，不编造
                    final_answer = "分析完成，但未获取到具体数据，请检查数据源是否正常。"
                    execution_log.append({"step": "⚠️ 无数据，提示用户检查数据源"})

                # ==========  调用验证器 ==========
                if last_data and isinstance(last_data, list):
                    try:
                        from src.tools.validator import validator
                        validation_result = validator.validate(last_data, state['query'])

                        if not validation_result.get("passed"):
                            alerts = validation_result.get("alerts", [])
                            if alerts:
                                alert_msg = "；".join(alerts)
                                # 把验证警告追加到最终回答后面
                                final_answer = f"{final_answer}\n\n⚠️ **数据验证提醒**：{alert_msg}"
                                execution_log.append({"step": f"⚠️ 数据验证提醒: {alert_msg}"})
                        else:
                            execution_log.append({"step": "✅ 数据验证通过"})
                    except Exception as e:
                        # 验证器异常不影响主流程
                        print(f"⚠️ 验证器调用失败: {e}")
                        execution_log.append({"step": "⚠️ 数据验证跳过（验证器异常）"})
                # ========================================

            result = {"success": True, "message": final_answer}
            execution_log.append({"step": f"✅ 最终回答已生成"})

        else:
            final_answer = f"未知工具: {tool}"
            result = {"success": False, "error": final_answer}
            execution_log.append({"step": f"❌ 未知工具: {tool}"})
            # 未知工具，停止执行
            should_stop = True

    except Exception as e:
        print(f"⚠️ 执行出错: {e}")
        final_answer = f"执行出错: {str(e)}"
        result = {"success": False, "error": str(e)}
        execution_log.append({"step": f"❌ 执行出错: {str(e)}"})
        # 异常，停止执行
        should_stop = True

    print(f"📝 [executor_node] execution_log: {execution_log}")

    # 如果失败，跳到计划末尾结束
    if should_stop:
        return {
            "current_step": len(plan),  # 直接跳到末尾
            "tool_results": state.get("tool_results", []) + [{
                "step": step_idx + 1,
                "tool": tool,
                "result": result
            }],
            "final_answer": final_answer,
            "execution_log": state.get("execution_log", []) + execution_log,
            "error_log": state.get("error_log", []) + [f"步骤{step_idx + 1}失败: {final_answer}"]
        }

    # 正常执行：推进到下一步
    return {
        "current_step": step_idx + 1,
        "tool_results": state.get("tool_results", []) + [{
            "step": step_idx + 1,
            "tool": tool,
            "result": result
        }],
        "final_answer": final_answer,
        "execution_log": state.get("execution_log", []) + execution_log,
        "messages": state.get("messages", []) + [{"role": "assistant", "content": final_answer}]
    }


# ============================================================
# 节点3：反思器
# ============================================================
def reflector_node(state: AgentState) -> Dict[str, Any]:
    """检查是否偏离目标"""
    print(f"🔍 [反思] 检查是否偏离目标")

    is_on_track = True
    log_entry = "反思: 正常（默认）"

    try:
        executed = state.get("tool_results", [])
        steps_summary = "\n".join([str(r) for r in executed[-3:]]) if executed else "无"

        prompt = REFLECTOR_PROMPT.format(
            query=state['query'],
            steps=steps_summary,
            status=f"已完成 {len(executed)} 步，共 {state.get('max_steps', 0)} 步"
        )

        model = model_router.get("reasoning")
        response = model.invoke(prompt)

        result = parse_json(response.content)

        is_on_track = result.get("is_on_track", True)
        issue = result.get("issue", "无")
        suggestion = result.get("suggestion", "")

        log_entry = f"反思: {'正常' if is_on_track else '偏离'} - {issue}"
        if suggestion:
            log_entry += f" 建议: {suggestion}"

        print(f"   ✅ 反思结果: {'正常' if is_on_track else '偏离'}")

    except Exception as e:
        print(f"⚠️ 反思调用失败: {e}")
        is_on_track = True
        log_entry = f"反思: 正常（容错）"

    return {
        "is_on_track": is_on_track,
        "reflection_log": state.get("reflection_log", []) + [log_entry]
    }


# ============================================================
# 节点4：重规划器
# ============================================================
def replan_node(state: AgentState) -> Dict[str, Any]:
    """重新生成计划"""
    print(f"🔄 [重规划] 重新生成计划")

    # 收集已完成步骤的信息
    completed = state.get("tool_results", [])
    reflection_log = state.get("reflection_log", [])

    print(f"   📊 已完成 {len(completed)} 步")
    print(f"   📝 反思日志: {reflection_log[-1] if reflection_log else '无'}")

    try:
        # 用 LLM 重新生成计划
        replan_prompt = f"""你是一个任务规划专家。之前的计划遇到问题，需要重新规划。

原始目标：{state['query']}
已完成的步骤：{len(completed)} 步
反思结果：{reflection_log[-1] if reflection_log else '无'}

请生成一个新的执行计划，用 final_answer 步骤给出答案。

输出格式（JSON数组）：
[
    {{"step_id": 1, "tool": "final_answer", "args": {{"answer": "你的回答"}}}}
]

只输出JSON数组："""

        model = model_router.get("reasoning")
        response = model.invoke(replan_prompt)

        try:
            plan_data = parse_json(response.content)
            if not isinstance(plan_data, list):
                plan_data = [plan_data]
        except:
            plan_data = [{
                "step_id": 1,
                "tool": "final_answer",
                "args": {"answer": "重规划后完成分析"}
            }]

        plan = []
        for i, step in enumerate(plan_data):
            plan.append({
                "step_id": step.get("step_id", i + 1),
                "tool": step.get("tool", "final_answer"),
                "args": step.get("args", {}),
                "status": "pending"
            })

        print(f"   ✅ 重规划生成 {len(plan)} 个步骤")

    except Exception as e:
        print(f"   ⚠️ 重规划失败: {e}")
        plan = [{
            "step_id": 1,
            "tool": "final_answer",
            "args": {"answer": f"重规划后完成分析，原始错误: {str(e)}"},
            "status": "pending"
        }]

    return {
        "plan": plan,
        "max_steps": len(plan),
        "current_step": 0,
        "is_on_track": True,
        "replan_count": state.get("replan_count", 0) + 1
    }


# ============================================================
# 条件判断
# ============================================================
def should_continue(state: AgentState) -> str:
    """判断下一步走向"""
    current = state.get("current_step", 0)
    max_steps = state.get("max_steps", 0)
    final_answer = state.get("final_answer")
    is_on_track = state.get("is_on_track", True)

    print(f"🔍 [should_continue] current_step={current}, max_steps={max_steps}")
    print(f"   final_answer={final_answer}, is_on_track={is_on_track}")

    # 1. 如果有最终答案，结束
    if final_answer and final_answer != "处理完成":
        print("  → 结束: 已有最终答案")
        return "end"

    # 2. 如果所有步骤执行完，结束
    if current >= max_steps:
        print("  → 结束: 已完成所有步骤")
        return "end"

    # 3. 如果偏离目标，重规划
    if not is_on_track:
        print("  → 重规划: 偏离目标")
        return "replan"

    # 4. 每3步反思一次（但不超过总步数）
    if current > 0 and current % 3 == 0 and current < max_steps:
        print("  → 反思: 每3步反思")
        return "reflector"

    # 5. 继续执行下一步
    print("  → 继续执行下一步")
    return "execute"
