"""
社媒爆款内容抓取测试工作流
"""
from langgraph.graph import StateGraph, END
from graphs.state import SocialMediaCrawlInput, SocialMediaCrawlOutput, GlobalState
from graphs.nodes.social_media_crawl_node import social_media_crawl_node

# 创建测试工作流
builder = StateGraph(
    GlobalState,
    input_schema=SocialMediaCrawlInput,
    output_schema=SocialMediaCrawlOutput
)

# 添加节点
builder.add_node("social_media_crawl", social_media_crawl_node)

# 设置入口点
builder.set_entry_point("social_media_crawl")

# 添加边
builder.add_edge("social_media_crawl", END)

# 编译图
social_media_crawl_graph = builder.compile()
