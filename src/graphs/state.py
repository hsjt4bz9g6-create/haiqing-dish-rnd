"""
大连海青水产智能体工作流状态定义
"""
from typing import List, Dict, Optional, Literal
from pydantic import BaseModel, Field


class GlobalState(BaseModel):
    """全局状态定义"""
    # 任务类型
    task_type: str = Field(default="", description="任务类型：市场分析/产品研发/菜品应用/内容创作")
    
    # 产品信息
    product_name: str = Field(default="", description="产品名称")
    product_type: str = Field(default="", description="产品类型：鳕鱼/三文鱼/虾等")
    processing_method: str = Field(default="", description="加工方式：调理腌制/裹粉/裹面包糠/生冻/预炸")
    target_market: str = Field(default="", description="目标市场：餐饮/零售")
    
    # 分析结果
    market_trends: str = Field(default="", description="市场趋势分析")
    competitor_analysis: str = Field(default="", description="竞品分析")
    product_suggestions: str = Field(default="", description="产品研发建议")
    dish_applications: str = Field(default="", description="菜品应用方案")
    content_drafts: str = Field(default="", description="社媒内容草稿")
    
    # 最终报告
    final_report: str = Field(default="", description="整合后的最终报告")


class GraphInput(BaseModel):
    """工作流输入"""
    task_type: Literal["市场分析", "产品研发", "菜品应用", "内容创作"] = Field(
        ..., description="任务类型：市场分析/产品研发/菜品应用/内容创作"
    )
    product_name: str = Field(default="", description="产品名称（可选）")
    product_type: str = Field(default="", description="产品类型：鳕鱼/三文鱼/虾等（可选）")
    processing_method: str = Field(default="", description="加工方式：调理腌制/裹粉/裹面包糠/生冻/预炸（可选）")
    target_market: str = Field(default="", description="目标市场：餐饮/零售（可选）")


class GraphOutput(BaseModel):
    """工作流输出"""
    final_report: str = Field(..., description="最终生成的分析报告")


# ========== 节点输入输出定义 ==========

class MarketAnalysisInput(BaseModel):
    """市场分析节点输入"""
    task_type: str = Field(..., description="任务类型")
    product_type: str = Field(default="", description="产品类型")


class MarketAnalysisOutput(BaseModel):
    """市场分析节点输出"""
    market_trends: str = Field(..., description="市场趋势分析结果")
    competitor_analysis: str = Field(..., description="竞品分析结果")


class ProductRnDInput(BaseModel):
    """产品研发节点输入"""
    product_name: str = Field(default="", description="产品名称")
    product_type: str = Field(default="", description="产品类型")
    processing_method: str = Field(default="", description="加工方式")
    market_trends: str = Field(default="", description="市场趋势信息")


class ProductRnDOutput(BaseModel):
    """产品研发节点输出"""
    product_suggestions: str = Field(..., description="产品研发建议")


class DishApplicationInput(BaseModel):
    """菜品应用节点输入"""
    product_name: str = Field(default="", description="产品名称")
    product_type: str = Field(default="", description="产品类型")
    target_market: str = Field(default="", description="目标市场")


class DishApplicationOutput(BaseModel):
    """菜品应用节点输出"""
    dish_applications: str = Field(..., description="菜品应用方案")


class ContentCreationInput(BaseModel):
    """内容创作节点输入"""
    product_name: str = Field(default="", description="产品名称")
    product_type: str = Field(default="", description="产品类型")
    product_suggestions: str = Field(default="", description="产品建议")
    dish_applications: str = Field(default="", description="菜品应用方案")


class ContentCreationOutput(BaseModel):
    """内容创作节点输出"""
    content_drafts: str = Field(..., description="社媒内容草稿")


class ReportGenerationInput(BaseModel):
    """报告生成节点输入"""
    market_trends: str = Field(default="", description="市场趋势分析")
    competitor_analysis: str = Field(default="", description="竞品分析")
    product_suggestions: str = Field(default="", description="产品建议")
    dish_applications: str = Field(default="", description="菜品应用方案")
    content_drafts: str = Field(default="", description="社媒内容")


class ReportGenerationOutput(BaseModel):
    """报告生成节点输出"""
    final_report: str = Field(..., description="最终报告")


class FeishuPushInput(BaseModel):
    """飞书推送节点输入"""
    final_report: str = Field(..., description="要推送的报告内容")


class FeishuPushOutput(BaseModel):
    """飞书推送节点输出"""
    push_status: str = Field(..., description="推送状态：成功/失败")
    push_message: str = Field(..., description="推送结果消息")


class FeishuBitableInput(BaseModel):
    """飞书多维表格录入节点输入"""
    product_name: str = Field(default="", description="产品名称")
    product_type: str = Field(default="", description="产品类型")
    processing_method: str = Field(default="", description="加工方式")
    target_market: str = Field(default="", description="目标市场")
    market_trends: str = Field(default="", description="市场趋势分析")
    competitor_analysis: str = Field(default="", description="竞品分析")
    product_suggestions: str = Field(default="", description="产品研发建议")
    dish_applications: str = Field(default="", description="菜品应用方案")
    content_drafts: str = Field(default="", description="社媒内容草稿")
    final_report: str = Field(default="", description="最终报告")


class SocialMediaCrawlInput(BaseModel):
    """社媒内容抓取节点输入"""
    keywords: list = Field(default=["鳕鱼", "三文鱼", "深海鱼", "虾", "鱼糜制品", "蟹柳棒"], description="搜索关键词列表")
    channels: list = Field(default=["小红书", "抖音", "视频号", "快手", "公众号"], description="社媒渠道列表")


class SocialMediaCrawlOutput(BaseModel):
    """社媒内容抓取节点输出"""
    total_records: int = Field(..., description="抓取的总记录数")
    crawl_time: str = Field(..., description="抓取时间")
    message: str = Field(..., description="执行结果消息")
