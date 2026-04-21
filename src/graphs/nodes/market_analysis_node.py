"""
市场分析节点
"""
import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import SearchClient, LLMClient
from langchain_core.messages import HumanMessage
from graphs.state import MarketAnalysisInput, MarketAnalysisOutput


def market_analysis_node(
    state: MarketAnalysisInput, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> MarketAnalysisOutput:
    """
    title: 市场趋势分析
    desc: 分析深海鱼产品市场趋势、监控社媒热点、调研竞品情况
    integrations: 大语言模型, 网络搜索
    """
    ctx = runtime.context
    
    # 读取配置文件
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""), 
        config.get("metadata", {}).get("llm_cfg", "config/market_analysis_cfg.json")
    )
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 渲染用户提示词
    up_tpl = Template(up)
    user_prompt = up_tpl.render({
        "product_type": state.product_type or "深海鱼产品"
    })
    
    # 1. 使用搜索工具获取市场信息
    search_client = SearchClient(ctx=ctx)
    
    # 搜索市场趋势
    trend_query = f"{state.product_type or '深海鱼产品'} 市场趋势 2024 2025"
    trend_results = search_client.web_search(query=trend_query, count=5)
    
    # 搜索社媒热点
    social_query = f"{state.product_type or '深海鱼产品'} 抖音 小红书 爆款"
    social_results = search_client.web_search(query=social_query, count=5)
    
    # 搜索竞品信息
    competitor_query = f"{state.product_type or '深海鱼产品'} 品牌 产品"
    competitor_results = search_client.web_search(query=competitor_query, count=5)
    
    # 2. 整合搜索结果
    search_info = f"""
## 市场趋势搜索结果：
{chr(10).join([f"- {item.title}: {item.snippet}" for item in trend_results.web_items[:3]])}

## 社媒热点搜索结果：
{chr(10).join([f"- {item.title}: {item.snippet}" for item in social_results.web_items[:3]])}

## 竞品搜索结果：
{chr(10).join([f"- {item.title}: {item.snippet}" for item in competitor_results.web_items[:3]])}
"""
    
    # 3. 使用大模型分析
    llm_client = LLMClient(ctx=ctx)
    
    messages = [
        HumanMessage(content=f"{user_prompt}\n\n## 参考信息：\n{search_info}")
    ]
    
    response = llm_client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.7),
        max_completion_tokens=llm_config.get("max_completion_tokens", 4096)
    )
    
    # 提取响应内容
    if isinstance(response.content, str):
        analysis_result = response.content
    elif isinstance(response.content, list):
        analysis_result = " ".join([
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in response.content
        ])
    else:
        analysis_result = str(response.content)
    
    # 分割市场趋势和竞品分析
    parts = analysis_result.split("## 竞品分析")
    market_trends = parts[0].replace("## 市场趋势分析", "").strip() if len(parts) > 0 else analysis_result
    competitor_analysis = parts[1].strip() if len(parts) > 1 else "详见市场分析报告"
    
    return MarketAnalysisOutput(
        market_trends=market_trends,
        competitor_analysis=competitor_analysis
    )
