"""
社媒洞察节点
从大众点评和小红书抓取深海鱼菜品信息
"""
import os
from typing import List
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk.search import SearchClient
from graphs.state import SocialMediaInsightInput, SocialMediaInsightOutput, InsightItem


def social_media_insight_node(
    state: SocialMediaInsightInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SocialMediaInsightOutput:
    """
    title: 社媒洞察
    desc: 从大众点评或小红书抓取深海鱼菜品趋势，返回关键词、简介和图片
    integrations: 网络搜索
    """
    ctx = runtime.context
    
    # 初始化搜索客户端
    search_client = SearchClient()
    
    # 根据平台选择搜索关键词
    platform = state.platform
    keywords = state.keywords
    
    # 构建搜索查询
    if platform == "大众点评":
        search_query = f"大众点评 深海鱼 {' '.join(keywords[:3])} 菜品"
    else:  # 小红书
        search_query = f"小红书 深海鱼 {' '.join(keywords[:3])} 家常菜"
    
    insights: List[InsightItem] = []
    
    try:
        # 搜索网页内容
        web_results = search_client.search(
            query=search_query,
            count=state.limit,
            search_type="web"
        )
        
        # 提取洞察信息
        if web_results and isinstance(web_results, dict):
            results_list = web_results.get("results", [])
            
            for i, result in enumerate(results_list[:state.limit]):
                if isinstance(result, dict):
                    # 提取标题和摘要
                    title = result.get("title", "")
                    snippet = result.get("content", "") or result.get("snippet", "")
                    url = result.get("url", "")
                    
                    # 提取关键词（从标题中提取菜品名）
                    keyword = title.split(" ")[0] if title else f"深海鱼菜品{i+1}"
                    
                    # 生成简单介绍（截取前100字）
                    description = snippet[:100] + "..." if len(snippet) > 100 else snippet
                    
                    # 搜索相关图片
                    image_url = ""
                    try:
                        image_results = search_client.search(
                            query=f"{keyword} 菜品图片",
                            count=1,
                            search_type="image"
                        )
                        if image_results and isinstance(image_results, dict):
                            img_list = image_results.get("results", [])
                            if img_list and isinstance(img_list[0], dict):
                                image_url = img_list[0].get("url", "")
                    except Exception:
                        pass  # 图片搜索失败不影响主流程
                    
                    # 创建洞察项
                    insight = InsightItem(
                        keyword=keyword,
                        description=description,
                        image_url=image_url,
                        source=url,
                        platform=platform
                    )
                    insights.append(insight)
        
    except Exception:
        # 如果搜索失败，返回空列表
        pass
    
    return SocialMediaInsightOutput(
        insights=insights,
        platform=platform,
        total=len(insights)
    )
