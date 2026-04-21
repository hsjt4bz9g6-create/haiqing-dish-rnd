"""
产品研发节点
"""
import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import HumanMessage
from graphs.state import ProductRnDInput, ProductRnDOutput


def product_rnd_node(
    state: ProductRnDInput, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> ProductRnDOutput:
    """
    title: 产品研发建议
    desc: 为深海鱼产品提供工艺优化、风味搭配和包装设计建议
    integrations: 大语言模型
    """
    ctx = runtime.context
    
    # 读取配置文件
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""), 
        config.get("metadata", {}).get("llm_cfg", "config/product_rnd_cfg.json")
    )
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 渲染用户提示词
    up_tpl = Template(up)
    user_prompt = up_tpl.render({
        "product_name": state.product_name or "深海鱼产品",
        "product_type": state.product_type or "深海鱼",
        "processing_method": state.processing_method or "调理腌制",
        "market_trends": state.market_trends or "暂无市场趋势信息"
    })
    
    # 使用大模型分析
    llm_client = LLMClient(ctx=ctx)
    
    messages = [HumanMessage(content=user_prompt)]
    
    response = llm_client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.8),
        max_completion_tokens=llm_config.get("max_completion_tokens", 4096),
        thinking=llm_config.get("thinking", "enabled")
    )
    
    # 提取响应内容
    if isinstance(response.content, str):
        suggestions = response.content
    elif isinstance(response.content, list):
        suggestions = " ".join([
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in response.content
        ])
    else:
        suggestions = str(response.content)
    
    return ProductRnDOutput(product_suggestions=suggestions)
