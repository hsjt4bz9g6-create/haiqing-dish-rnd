"""
飞书多维表格录入节点
"""
import os
import json
import time
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from tools.feishu_bitable_tool import FeishuBitableClient
from graphs.state import FeishuBitableInput, GraphOutput


def feishu_bitable_input_node(
    state: FeishuBitableInput, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> GraphOutput:
    """
    title: 飞书多维表格录入
    desc: 将分析结果录入飞书多维表格
    integrations: 飞书多维表格
    """
    ctx = runtime.context
    
    # 飞书多维表格配置（已配置好）
    app_token = "TA64bckK3aMMbzssfFncLvu4n2e"
    table_id = "tblCkiCENBXeAc6t"
    
    try:
        # 初始化客户端
        client = FeishuBitableClient(app_token=app_token)
        
        # 生成唯一产品ID
        product_id = f"PRD{int(time.time())}"
        
        # 准备录入数据（单表结构）
        record = {
            "fields": {
                "产品名称": state.product_name,
                "产品类型": state.product_type,
                "加工方式": state.processing_method,
                "目标市场": state.target_market,
                "创建时间": int(time.time() * 1000),
                "产品ID": product_id,
                "市场趋势": state.market_trends[:2000] if state.market_trends else "",
                "竞品分析": state.competitor_analysis[:2000] if state.competitor_analysis else "",
                "产品研发建议": state.product_suggestions[:3000] if state.product_suggestions else "",
                "菜品应用方案": state.dish_applications[:3000] if state.dish_applications else "",
                "社媒内容": state.content_drafts[:3000] if state.content_drafts else ""
            }
        }
        
        # 录入数据
        client.add_records(table_id, [record])
        
        result_msg = f"""✅ 数据已成功录入飞书多维表格！

📋 产品ID: {product_id}
📊 数据表: 产品分析数据库
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
