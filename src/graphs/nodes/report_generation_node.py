"""
报告生成节点
"""
import os
import json
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import LLMClient
from langchain_core.messages import HumanMessage
from graphs.state import ReportGenerationInput, ReportGenerationOutput


def report_generation_node(
    state: ReportGenerationInput, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> ReportGenerationOutput:
    """
    title: 报告整合生成
    desc: 整合所有分析结果生成最终报告
    integrations: 大语言模型
    """
    ctx = runtime.context
    
    # 读取配置文件
    cfg_file = os.path.join(
        os.getenv("COZE_WORKSPACE_PATH", ""), 
        config.get("metadata", {}).get("llm_cfg", "config/report_generation_cfg.json")
    )
    with open(cfg_file, 'r', encoding='utf-8') as fd:
        _cfg = json.load(fd)
    
    llm_config = _cfg.get("config", {})
    sp = _cfg.get("sp", "")
    up = _cfg.get("up", "")
    
    # 渲染用户提示词
    up_tpl = Template(up)
    user_prompt = up_tpl.render({
        "market_trends": state.market_trends or "暂无市场趋势分析",
        "competitor_analysis": state.competitor_analysis or "暂无竞品分析",
        "product_suggestions": state.product_suggestions or "暂无产品研发建议",
        "dish_applications": state.dish_applications or "暂无菜品应用方案",
        "content_drafts": state.content_drafts or "暂无社媒内容"
    })
    
    # 使用大模型分析
    llm_client = LLMClient(ctx=ctx)
    
    messages = [HumanMessage(content=user_prompt)]
    
    response = llm_client.invoke(
        messages=messages,
        model=llm_config.get("model", "doubao-seed-1-8-251228"),
        temperature=llm_config.get("temperature", 0.5),
        max_completion_tokens=llm_config.get("max_completion_tokens", 4096)
    )
    
    # 提取响应内容
    if isinstance(response.content, str):
        final_report = response.content
    elif isinstance(response.content, list):
        final_report = " ".join([
            item.get("text", "") if isinstance(item, dict) else str(item)
            for item in response.content
        ])
    else:
        final_report = str(response.content)
    
    return ReportGenerationOutput(final_report=final_report)
