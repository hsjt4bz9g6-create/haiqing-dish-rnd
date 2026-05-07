"""
菜品研发节点
根据菜品信息生成AI菜品图片和卖点文案
"""
import os
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import ImageGenerationClient, LLMClient
from langchain_core.messages import HumanMessage
from graphs.state import DishDevelopmentInput, DishDevelopmentOutput


def dish_development_node(
    state: DishDevelopmentInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> DishDevelopmentOutput:
    """
    title: 菜品研发
    desc: 根据菜品信息生成AI菜品图片和卖点文案
    integrations: 图片生成, 大语言模型
    """
    ctx = runtime.context
    
    # 初始化客户端
    image_client = ImageGenerationClient(ctx=ctx)
    llm_client = LLMClient(ctx=ctx)
    
    # 构建菜品描述
    dish_desc = f"{state.dish_name}"
    if state.main_ingredient:
        dish_desc += f"，主料：{state.main_ingredient}"
        if state.main_weight:
            dish_desc += f" {state.main_weight}"
    if state.side_ingredient:
        dish_desc += f"，辅料：{state.side_ingredient}"
        if state.side_weight:
            dish_desc += f" {state.side_weight}"
    if state.cooking_method:
        dish_desc += f"，烹饪方法：{state.cooking_method}"
    
    image_url = ""
    selling_points: List[str] = []
    
    try:
        # 1. 生成菜品图片
        image_prompt = f"专业美食摄影，{state.dish_name}，{state.main_ingredient if state.main_ingredient else ''}，高端餐厅风格，自然光线，精致摆盘，高清细节， appetizing，4K"
        
        image_response = image_client.generate(
            prompt=image_prompt,
            size="2K"
        )
        
        if image_response.success and image_response.image_urls:
            image_url = image_response.image_urls[0]
        
    except Exception as e:
        # 图片生成失败不影响后续流程
        pass
    
    try:
        # 2. 生成菜品卖点
        llm_prompt = f"""你是一位专业的菜品研发专家，请根据以下菜品信息，提炼出5个核心卖点。

菜品信息：{dish_desc}

要求：
1. 每个卖点简洁有力，不超过15个字
2. 突出口感、营养、便捷性、适用场景等
3. 适合餐饮B端客户

请直接输出5个卖点，每个卖点一行，不要编号和标点。"""

        llm_response = llm_client.invoke(
            messages=[HumanMessage(content=llm_prompt)],
            model="doubao-seed-1-8-251228",
            temperature=0.7
        )
        
        if llm_response and llm_response.content:
            # 处理响应内容
            content = llm_response.content
            if isinstance(content, str):
                # 按行分割，过滤空行
                selling_points = [
                    line.strip()
                    for line in content.split("\n")
                    if line.strip() and len(line.strip()) <= 15
                ][:5]  # 最多5个
        
    except Exception as e:
        # 卖点生成失败不影响图片展示
        pass
    
    return DishDevelopmentOutput(
        dish_name=state.dish_name,
        image_url=image_url,
        selling_points=selling_points
    )
