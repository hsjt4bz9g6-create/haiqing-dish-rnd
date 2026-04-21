"""
内容创作节点
"""
import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import HumanMessage
from graphs.state import ContentCreationInput, ContentCreationOutput


def content_creation_node(
    state: ContentCreationInput, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> ContentCreationOutput:
    """
    title: 社媒内容创作
    desc: 创作抖音、小红书、视频号等平台的社媒内容
    integrations: 大语言模型
    """
    ctx = runtime.context
    
    # 读取配置文件
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""), 
        config.get("metadata", {}).get("llm_cfg", "config/content_creation_cfg.json")
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
        "product_suggestions": state.product_suggestions or "暂无产品建议",
        "dish_applications": state.dish_applications or "暂无菜品应用方案"
    })
    
    # 使用大模型分析
    llm_client = LLMClient(ctx=ctx)
    
    messages = [HumanMessage(content=user_prompt)]
    
    response = llm_client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.85),
        max_completion_tokens=llm_config.get("max_completion_tokens", 4096)
    )
    
    # 提取响应内容
    if isinstance(response.content, str):
        content_drafts = response.content
    elif isinstance(response.content, list):
        content_drafts = " ".join([
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in response.content
        ])
    else:
        content_drafts = str(response.content)
    
    return ContentCreationOutput(content_drafts=content_drafts)
