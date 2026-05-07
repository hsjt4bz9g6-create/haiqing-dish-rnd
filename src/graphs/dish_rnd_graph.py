"""
菜品应用研发工作流主图编排
"""
from langgraph.graph import StateGraph, END
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime

from graphs.state import (
    DishRnDGraphInput,
    DishRnDGraphOutput,
    SocialMediaInsightInput,
    DishDevelopmentInput
)

from graphs.nodes.social_media_insight_node import social_media_insight_node
from graphs.nodes.dish_development_node import dish_development_node


def should_do_insight(state: DishRnDGraphInput) -> str:
    """
    title: 判断操作类型
    desc: 根据action判断执行哪个节点
    """
    if state.action == "社媒洞察":
        return "社媒洞察"
    elif state.action == "菜品研发":
        return "菜品研发"
    else:
        return "结束"


def insight_entry(state: DishRnDGraphInput) -> SocialMediaInsightInput:
    """社媒洞察节点入参转换"""
    return SocialMediaInsightInput(
        platform=state.platform,
        keywords=["鳕鱼", "三文鱼", "蟹柳", "裹粉鳕鱼", "调理狭鳕鱼"],
        limit=5
    )


def dish_entry(state: DishRnDGraphInput) -> DishDevelopmentInput:
    """菜品研发节点入参转换"""
    return DishDevelopmentInput(
        dish_name=state.dish_name,
        main_ingredient=state.main_ingredient,
        main_weight=state.main_weight,
        side_ingredient=state.side_ingredient,
        side_weight=state.side_weight,
        cooking_method=state.cooking_method
    )


def insight_to_output(state, result) -> DishRnDGraphOutput:
    """社媒洞察结果转换为工作流输出"""
    return DishRnDGraphOutput(
        action="社媒洞察",
        insights=result.insights,
        image_url="",
        selling_points=[]
    )


def dish_to_output(state, result) -> DishRnDGraphOutput:
    """菜品研发结果转换为工作流输出"""
    return DishRnDGraphOutput(
        action="菜品研发",
        insights=[],
        image_url=result.image_url,
        selling_points=result.selling_points
    )


# 创建状态图
builder = StateGraph(
    DishRnDGraphInput,
    input_schema=DishRnDGraphInput,
    output_schema=DishRnDGraphOutput
)

# 添加节点
builder.add_node("社媒洞察", social_media_insight_node)
builder.add_node("菜品研发", dish_development_node)

# 设置入口点
builder.set_entry_point("路由")

# 添加条件分支
builder.add_conditional_edges(
    source="路由",
    path=should_do_insight,
    path_map={
        "社媒洞察": "社媒洞察",
        "菜品研发": "菜品研发",
        "结束": END
    }
)

# 添加边
builder.add_edge("社媒洞察", END)
builder.add_edge("菜品研发", END)

# 编译图
dish_rnd_graph = builder.compile()
