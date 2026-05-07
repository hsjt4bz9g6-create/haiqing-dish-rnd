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


# ========== 菜品应用研发工作流状态定义 ==========

class InsightItem(BaseModel):
    """单个洞察项"""
    keyword: str = Field(..., description="关键词/菜品名")
    description: str = Field(..., description="简单介绍")
    image_url: str = Field(default="", description="图片URL")
    source: str = Field(default="", description="来源链接")
    platform: str = Field(default="", description="平台：大众点评/小红书")


class SocialMediaInsightInput(BaseModel):
    """社媒洞察节点输入"""
    platform: str = Field(default="小红书", description="平台：大众点评/小红书")
    keywords: list = Field(default=["鳕鱼", "三文鱼", "蟹柳", "裹粉鳕鱼", "调理狭鳕鱼"], description="搜索关键词列表")
    limit: int = Field(default=5, description="返回结果数量")


class SocialMediaInsightOutput(BaseModel):
    """社媒洞察节点输出"""
    insights: List[InsightItem] = Field(default=[], description="洞察列表")
    platform: str = Field(..., description="平台")
    total: int = Field(..., description="总数")


class DishDevelopmentInput(BaseModel):
    """菜品研发节点输入"""
    dish_name: str = Field(..., description="菜品名称")
    main_ingredient: str = Field(default="", description="主料")
    main_weight: str = Field(default="", description="主料克重")
    side_ingredient: str = Field(default="", description="辅料")
    side_weight: str = Field(default="", description="辅料克重")
    cooking_method: str = Field(default="", description="烹饪方法")


class DishDevelopmentOutput(BaseModel):
    """菜品研发节点输出"""
    dish_name: str = Field(..., description="菜品名称")
    image_url: str = Field(..., description="生成的菜品图片URL")
    selling_points: List[str] = Field(default=[], description="菜品卖点列表")


class DishRnDGraphInput(BaseModel):
    """菜品研发工作流输入"""
    action: Literal["社媒洞察", "菜品研发"] = Field(..., description="操作类型")
    # 社媒洞察参数
    platform: str = Field(default="小红书", description="平台：大众点评/小红书")
    # 菜品研发参数
    dish_name: str = Field(default="", description="菜品名称")
    main_ingredient: str = Field(default="", description="主料")
    main_weight: str = Field(default="", description="主料克重")
    side_ingredient: str = Field(default="", description="辅料")
    side_weight: str = Field(default="", description="辅料克重")
    cooking_method: str = Field(default="", description="烹饪方法")


class DishRnDGraphOutput(BaseModel):
    """菜品研发工作流输出"""
    action: str = Field(..., description="执行的操作")
    # 社媒洞察结果
    insights: List[InsightItem] = Field(default=[], description="洞察列表")
    # 菜品研发结果
    image_url: str = Field(default="", description="菜品图片URL")
    selling_points: List[str] = Field(default=[], description="卖点列表")


class WeeklyReportInput(BaseModel):
    """研发任务周报生成节点输入"""
    app_token: str = Field(default="XqpUbfoHIa4LjcsgS3Ccr1uJnjg", description="飞书多维表格app_token")
    table_id: str = Field(default="tblXZEsOcRXTT6Hp", description="任务表table_id")


class WeeklyReportOutput(BaseModel):
    """研发任务周报生成节点输出"""
    success: bool = Field(..., description="是否成功生成周报")
    message: str = Field(..., description="执行结果消息")
    pdf_url: str = Field(default="", description="生成的PDF下载链接")
    completed_count: int = Field(default=0, description="本周完成任务数")
    in_progress_count: int = Field(default=0, description="进行中任务数")
    next_week_count: int = Field(default=0, description="下周计划任务数")
    push_success: bool = Field(default=False, description="是否成功推送到飞书群")


class SocialMediaTrackInput(BaseModel):
    """社交媒体内容跟踪节点输入"""
    app_token: str = Field(default="TA64bckK3aMMbzssfFncLvu4n2e", description="飞书多维表格app_token")
    table_id: str = Field(default="tblCEdIkjthfJ7Of", description="社媒内容表table_id")


class SocialMediaTrackOutput(BaseModel):
    """社交媒体内容跟踪节点输出"""
    success: bool = Field(..., description="是否成功抓取内容")
    message: str = Field(..., description="执行结果消息")
    total_records: int = Field(default=0, description="总记录数")
    track_time: str = Field(default="", description="抓取时间")
    total_exposure: int = Field(default=0, description="总曝光量")
    total_likes: int = Field(default=0, description="总点赞量")
    total_shares: int = Field(default=0, description="总转发量")
