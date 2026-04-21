"""
大连海青水产智能体工作流主图编排
"""
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput
)

from graphs.nodes.market_analysis_node import market_analysis_node
from graphs.nodes.product_rnd_node import product_rnd_node
from graphs.nodes.dish_application_node import dish_application_node
from graphs.nodes.content_creation_node import content_creation_node
from graphs.nodes.report_generation_node import report_generation_node
from graphs.nodes.feishu_bitable_input_node import feishu_bitable_input_node


# 创建状态图
builder = StateGraph(
    GlobalState, 
    input_schema=GraphInput, 
    output_schema=GraphOutput
)

# 添加节点
builder.add_node(
    "market_analysis", 
    market_analysis_node, 
    metadata={"type": "agent", "llm_cfg": "config/market_analysis_cfg.json"}
)

builder.add_node(
    "product_rnd", 
    product_rnd_node, 
    metadata={"type": "agent", "llm_cfg": "config/product_rnd_cfg.json"}
)

builder.add_node(
    "dish_application", 
    dish_application_node, 
    metadata={"type": "agent", "llm_cfg": "config/dish_application_cfg.json"}
)

builder.add_node(
    "content_creation", 
    content_creation_node, 
    metadata={"type": "agent", "llm_cfg": "config/content_creation_cfg.json"}
)

builder.add_node(
    "report_generation", 
    report_generation_node, 
    metadata={"type": "agent", "llm_cfg": "config/report_generation_cfg.json"}
)

builder.add_node(
    "feishu_bitable_input", 
    feishu_bitable_input_node
)

# 设置入口点
builder.set_entry_point("market_analysis")

# 添加边 - 市场分析后并行执行产品研发和菜品应用
builder.add_edge("market_analysis", "product_rnd")
builder.add_edge("market_analysis", "dish_application")

# 产品研发和菜品应用完成后，汇聚到内容创作
builder.add_edge(["product_rnd", "dish_application"], "content_creation")

# 内容创作后生成报告
builder.add_edge("content_creation", "report_generation")

# 报告生成后录入飞书多维表格
builder.add_edge("report_generation", "feishu_bitable_input")

# 飞书多维表格录入后结束
builder.add_edge("feishu_bitable_input", END)

# 编译图
main_graph = builder.compile()
