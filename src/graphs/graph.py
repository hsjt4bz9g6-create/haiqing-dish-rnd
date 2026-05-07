"""
大连海青水产智能体工作流主图编排
"""
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from graphs.state import (
    GlobalState,
    GraphInput,
    GraphOutput,
    DishRnDGraphInput,
    DishRnDGraphOutput,
    SocialMediaInsightInput,
    DishDevelopmentInput
)

from graphs.nodes.market_analysis_node import market_analysis_node
from graphs.nodes.product_rnd_node import product_rnd_node
from graphs.nodes.dish_application_node import dish_application_node
from graphs.nodes.content_creation_node import content_creation_node
from graphs.nodes.report_generation_node import report_generation_node
from graphs.nodes.feishu_bitable_input_node import feishu_bitable_input_node
from graphs.nodes.social_media_insight_node import social_media_insight_node
from graphs.nodes.dish_development_node import dish_development_node


# ========== 原有工作流 ==========

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


# ========== 菜品研发工作流 ==========

def dish_rnd_router(state: DishRnDGraphInput) -> str:
    """
    title: 路由节点
    desc: 根据action决定执行哪个节点
    """
    if state.action == "社媒洞察":
        return "social_media_insight"
    elif state.action == "菜品研发":
        return "dish_development"
    else:
        return "end"


# 创建菜品研发状态图
dish_rnd_builder = StateGraph(
    DishRnDGraphInput,
    input_schema=DishRnDGraphInput,
    output_schema=DishRnDGraphOutput
)

# 添加节点
dish_rnd_builder.add_node("social_media_insight", social_media_insight_node)
dish_rnd_builder.add_node("dish_development", dish_development_node)

# 设置条件分支
dish_rnd_builder.set_conditional_entry_point(
    dish_rnd_router,
    {
        "social_media_insight": "social_media_insight",
        "dish_development": "dish_development",
        "end": END
    }
)

# 添加边
dish_rnd_builder.add_edge("social_media_insight", END)
dish_rnd_builder.add_edge("dish_development", END)

# 编译菜品研发图
dish_rnd_graph = dish_rnd_builder.compile()
