"""
产品研发分析节点
"""
import json
from typing import List
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk.llm import LLMClient

from graphs.state import (
    ProductDevelopmentInput,
    ProductDevelopmentOutput,
    ImprovementItem
)


def product_development_node(
    state: ProductDevelopmentInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> ProductDevelopmentOutput:
    """
    title: 产品研发分析
    desc: 分析配方改进点，提供优化建议
    integrations: 大语言模型
    """
    # 构建配料列表文本
    ingredients_text = ""
    if state.ingredients:
        ingredients_text = "\n".join([
            f"- {ing.name}: {ing.amount}"
            for ing in state.ingredients
        ])
    
    # 构建完整的分析内容
    analysis_content = f"""
## 配方名称
{state.recipe_name}

## 配料清单
{ingredients_text if ingredients_text else "未提供"}

## 实验室数据
{state.lab_data if state.lab_data else "未提供"}

## 烹饪方式
{state.cooking_method}

## 工艺文档内容
{state.document_content if state.document_content else "未提供"}

## 产品照片
{f"已上传 {len(state.photo_urls)} 张照片" if state.photo_urls else "未提供"}
"""
    
    # 系统提示词
    system_prompt = """你是一位资深的食品研发专家，专注于深海鱼类产品的配方优化和工艺改进。

你的任务是分析用户提供的配方信息，包括：
- 配料清单及用量
- 实验室测试数据
- 烹饪方式
- 工艺文档内容

请从以下维度进行分析：
1. **风味优化**：配料搭配是否合理，能否提升口感和风味
2. **营养价值**：蛋白质、脂肪等营养成分是否达标，如何优化
3. **工艺改进**：烹饪方式是否合理，能否提高生产效率
4. **成本控制**：配料成本是否可控，有无替代方案
5. **货架期**：保鲜期是否达标，如何延长
6. **食品安全**：添加剂使用是否合规，有无安全风险

输出要求：
- 每个改进点都要说明"为什么这样改进"
- 改进建议要具体、可操作
- 考虑餐饮和零售客户的实际需求
- 符合大连海青水产的产品定位"""

    # 用户提示词
    user_prompt = f"""请分析以下产品配方，提供改进建议：

{analysis_content}

请输出JSON格式，包含：
1. improvements: 改进点列表，每个改进点包含：
   - point: 改进点描述（简洁明了）
   - reason: 为什么这样改进（详细说明原因和依据）
2. summary: 整体优化建议总结（200字以内）

示例格式：
{{
  "improvements": [
    {{
      "point": "增加磷酸盐含量至0.3%",
      "reason": "当前实验室数据显示水分保持率为82%，略低于行业标准85%。增加磷酸盐可以提升保水性，改善口感，延长货架期。"
    }}
  ],
  "summary": "该配方整体设计合理，建议重点优化水分保持和风味平衡..."
}}"""

    # 调用LLM
    llm_client = LLMClient()
    
    response = llm_client.chat(
        model="doubao-seed-1-8-251228",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.7
    )
    
    # 解析响应
    result_text = response.choices[0].message.content
    
    # 提取JSON部分
    import re
    json_match = re.search(r'\{[\s\S]*\}', result_text)
    if json_match:
        result_data = json.loads(json_match.group())
    else:
        # 如果没有找到JSON，返回默认结果
        result_data = {
            "improvements": [
                {
                    "point": "建议完善实验室数据",
                    "reason": "当前提供的实验数据不够详细，建议补充水分含量、蛋白质含量、口感评分等关键指标，以便进行更精准的分析。"
                }
            ],
            "summary": "请提供更详细的配方信息和实验室数据，以便进行深入分析。"
        }
    
    # 构建改进项列表
    improvements = []
    for item in result_data.get("improvements", []):
        improvements.append(ImprovementItem(
            point=item.get("point", ""),
            reason=item.get("reason", "")
        ))
    
    return ProductDevelopmentOutput(
        recipe_name=state.recipe_name,
        improvements=improvements,
        summary=result_data.get("summary", "分析完成，请查看详细改进建议。")
    )
