"""
飞书多维表格录入节点
"""
import os
import json
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from tools.feishu_bitable_tool import FeishuBitableClient
from graphs.state import GlobalState, GraphOutput


def feishu_bitable_input_node(
    state: GlobalState, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> GraphOutput:
    """
    title: 飞书多维表格录入
    desc: 将分析结果录入飞书多维表格
    integrations: 飞书多维表格
    """
    ctx = runtime.context
    
    # 从配置中获取app_token（需要用户在配置中指定）
    app_token = os.getenv("FEISHU_APP_TOKEN", "")
    
    if not app_token:
        return GraphOutput(
            final_report=f"⚠️ 未配置飞书多维表格app_token，无法录入数据。\n\n请设置环境变量 FEISHU_APP_TOKEN 或在配置中指定。\n\n报告内容：\n{state.final_report}"
        )
    
    try:
        # 初始化客户端
        client = FeishuBitableClient(app_token=app_token)
        
        # 列出所有表
        tables_result = client.list_tables(app_token)
        tables = tables_result["data"]["items"]
        
        # 生成唯一产品ID
        import time
        product_id = f"PRD{int(time.time())}"
        
        # 准备录入数据
        records_data = {
            "产品基础信息": [
                {
                    "fields": {
                        "产品名称": state.product_name,
                        "产品类型": state.product_type,
                        "加工方式": state.processing_method,
                        "目标市场": state.target_market,
                        "创建时间": int(time.time() * 1000),
                        "产品ID": product_id
                    }
                }
            ],
            "市场分析": [
                {
                    "fields": {
                        "产品ID": product_id,
                        "市场趋势": state.market_trends[:2000] if state.market_trends else "",
                        "竞品分析": state.competitor_analysis[:2000] if state.competitor_analysis else "",
                        "市场机会": "详见市场趋势分析",
                        "分析时间": int(time.time() * 1000)
                    }
                }
            ],
            "产品研发": [
                {
                    "fields": {
                        "产品ID": product_id,
                        "食材特性分析": state.product_suggestions[:1000] if state.product_suggestions else "",
                        "工艺优化建议": state.product_suggestions[1000:2000] if len(state.product_suggestions) > 1000 else "",
                        "风味搭配方案": state.product_suggestions[2000:3000] if len(state.product_suggestions) > 2000 else "",
                        "包装设计建议": state.product_suggestions[3000:4000] if len(state.product_suggestions) > 3000 else "",
                        "创新产品方向": state.product_suggestions[4000:5000] if len(state.product_suggestions) > 4000 else ""
                    }
                }
            ],
            "菜品应用": [
                {
                    "fields": {
                        "产品ID": product_id,
                        "烹饪特性": state.dish_applications[:1000] if state.dish_applications else "",
                        "餐饮应用方案": state.dish_applications[1000:2000] if len(state.dish_applications) > 1000 else "",
                        "零售应用方案": state.dish_applications[2000:3000] if len(state.dish_applications) > 2000 else "",
                        "烹饪建议": state.dish_applications[3000:4000] if len(state.dish_applications) > 3000 else ""
                    }
                }
            ],
            "社媒内容": [
                {
                    "fields": {
                        "产品ID": product_id,
                        "抖音内容": state.content_drafts[:1000] if state.content_drafts else "",
                        "小红书内容": state.content_drafts[1000:2000] if len(state.content_drafts) > 1000 else "",
                        "视频号内容": state.content_drafts[2000:3000] if len(state.content_drafts) > 2000 else "",
                        "视觉化建议": state.content_drafts[3000:4000] if len(state.content_drafts) > 3000 else ""
                    }
                }
            ]
        }
        
        # 录入数据
        success_tables = []
        for table in tables:
            table_name = table["name"]
            table_id = table["table_id"]
            
            if table_name in records_data:
                try:
                    client.add_records(table_id, records_data[table_name])
                    success_tables.append(table_name)
                except Exception as e:
                    ctx.logger.error(f"录入表 {table_name} 失败: {e}")
        
        result_msg = f"""✅ 数据已成功录入飞书多维表格！

📋 产品ID: {product_id}
📊 已录入表格: {', '.join(success_tables)}
🔗 查看链接: https://feishu.cn/base/{app_token}

产品信息:
- 产品名称: {state.product_name}
- 产品类型: {state.product_type}
- 加工方式: {state.processing_method}
- 目标市场: {state.target_market}

所有分析结果已结构化存储在多维表格中，可随时查看和编辑。"""
        
        return GraphOutput(final_report=result_msg)
    
    except Exception as e:
        return GraphOutput(
            final_report=f"⚠️ 飞书多维表格录入失败: {str(e)}\n\n报告内容：\n{state.final_report}"
        )
