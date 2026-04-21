"""
社媒爆款内容抓取节点
"""
import os
import json
import time
from datetime import datetime
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from tools.feishu_bitable_tool import FeishuBitableClient
from graphs.state import SocialMediaCrawlInput, SocialMediaCrawlOutput


def social_media_crawl_node(
    state: SocialMediaCrawlInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> SocialMediaCrawlOutput:
    """
    title: 社媒爆款内容抓取
    desc: 抓取社媒渠道（小红书、抖音、视频号、快手、公众号）的爆款内容
    integrations: 网络搜索, 飞书多维表格
    """
    ctx = runtime.context
    
    # 飞书多维表格配置
    app_token = "TA64bckK3aMMbzssfFncLvu4n2e"
    table_id = "tblCkiCENBXeAc6t"
    
    try:
        # 初始化飞书多维表格客户端
        bitable_client = FeishuBitableClient(app_token=app_token)
        
        # 抓取时间
        crawl_timestamp = int(time.time() * 1000)
        crawl_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # 模拟抓取数据（实际应用中需要接入真实的社媒API或爬虫）
        # TODO: 接入真实的社媒搜索API
        crawled_data = []
        
        for keyword in state.keywords:
            for channel in state.channels:
                # 模拟数据（实际应用中替换为真实抓取）
                mock_record = {
                    "社媒渠道": channel,
                    "搜索关键词": keyword,
                    "情绪类型": "正面",
                    "笔记标题": f"【{channel}】{keyword}爆款内容推荐",
                    "内容摘要": f"本周{channel}平台关于{keyword}的热门内容...",
                    "点赞数": 10000.0 + hash(f"{keyword}{channel}") % 50000,
                    "收藏数": 5000.0 + hash(f"{keyword}{channel}") % 30000,
                    "热度标签": "上升" if hash(f"{keyword}{channel}") % 3 == 0 else "稳定",
                    "笔记链接/视频链接": f"https://example.com/{channel}/{keyword}",
                    "关联竞品或产品建议": f"基于{keyword}的产品开发建议",
                    "抓取时间": crawl_timestamp
                }
                crawled_data.append(mock_record)
        
        # 录入到飞书多维表格
        records = [{"fields": data} for data in crawled_data]
        bitable_client.add_records(table_id, records)
        
        return SocialMediaCrawlOutput(
            total_records=len(crawled_data),
            crawl_time=crawl_time_str,
            message=f"✅ 成功抓取并录入 {len(crawled_data)} 条社媒内容"
        )
    
    except Exception as e:
        return SocialMediaCrawlOutput(
            total_records=0,
            crawl_time=datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            message=f"❌ 抓取失败: {str(e)}"
        )
