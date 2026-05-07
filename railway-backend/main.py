# Railway后端部署配置
# 这是一个简化版的后端，用于Railway部署

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 初始化FastAPI
app = FastAPI(title="海青菜品研发API")

# 配置CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class InsightItem(BaseModel):
    keyword: str
    description: str
    image_url: Optional[str] = ""
    source_url: str


class InsightResponse(BaseModel):
    platform: str
    insights: List[InsightItem]


class DishGenerateRequest(BaseModel):
    dish_name: str
    main_ingredient: str
    main_weight: str = ""
    side_ingredient: str = ""
    side_weight: str = ""
    cooking_method: str


class DishGenerateResponse(BaseModel):
    dish_name: str
    image_url: str
    selling_points: List[str]


def get_search_client():
    """延迟初始化搜索客户端"""
    try:
        from coze_coding_dev_sdk.search import SyncSearchClient
        return SyncSearchClient()
    except Exception as e:
        logger.error(f"初始化搜索客户端失败: {e}")
        return None


def get_llm_client():
    """延迟初始化LLM客户端"""
    try:
        from coze_coding_dev_sdk.llm import LLMClient
        return LLMClient(model_id="doubao-seed-1-8-251228")
    except Exception as e:
        logger.error(f"初始化LLM客户端失败: {e}")
        return None


def get_image_client():
    """延迟初始化图片生成客户端"""
    try:
        from coze_coding_dev_sdk.image_generation import ImageGenerationClient
        return ImageGenerationClient()
    except Exception as e:
        logger.error(f"初始化图片生成客户端失败: {e}")
        return None


@app.get("/api/web/insights/{platform}")
async def get_insights(platform: str):
    """获取社媒洞察"""
    try:
        search_client = get_search_client()
        if not search_client:
            return InsightResponse(platform=platform, insights=[])
        
        # 搜索关键词
        if platform == "dianping":
            query = "大众点评 深海鱼 鳕鱼 三文鱼 蟹柳 菜品"
        else:
            query = "小红书 深海鱼 鳕鱼 三文鱼 家庭做法"
        
        # 搜索网页
        web_results = search_client.search_web(query=query, max_results=3)
        
        # 搜索图片
        image_results = search_client.search_images(query=f"{query} 菜品", max_results=3)
        
        insights = []
        for i, result in enumerate(web_results[:3]):
            image_url = ""
            if i < len(image_results):
                image_url = image_results[i].get("url", "")
            
            insights.append(InsightItem(
                keyword=result.get("title", "深海鱼菜品")[:20],
                description=result.get("snippet", "深海鱼美味菜品")[:50],
                image_url=image_url,
                source_url=result.get("url", "https://www.dianping.com")
            ))
        
        return InsightResponse(platform=platform, insights=insights)
    
    except Exception as e:
        logger.error(f"获取洞察失败: {e}")
        return InsightResponse(platform=platform, insights=[])


@app.post("/api/web/dish/generate")
async def generate_dish(request: DishGenerateRequest):
    """生成菜品图片和卖点"""
    try:
        image_client = get_image_client()
        llm_client = get_llm_client()
        
        if not image_client or not llm_client:
            raise Exception("客户端初始化失败，请检查环境变量配置")
        
        # 生成图片
        prompt = f"精美的{request.dish_name}菜品，{request.main_ingredient}，{request.cooking_method}，专业美食摄影，高清，诱人"
        image_result = image_client.generate_image(prompt=prompt)
        image_url = image_result.get("url", "")
        
        # 生成卖点
        llm_prompt = f"""
        为以下菜品生成5个核心卖点，每个卖点10字以内：
        菜品：{request.dish_name}
        主料：{request.main_ingredient} {request.main_weight}
        辅料：{request.side_ingredient} {request.side_weight}
        烹饪：{request.cooking_method}
        
        直接输出5个卖点，每行一个，不要编号。
        """
        
        llm_response = llm_client.chat(llm_prompt)
        selling_points = [line.strip() for line in llm_response.split("\n") if line.strip()][:5]
        
        return DishGenerateResponse(
            dish_name=request.dish_name,
            image_url=image_url,
            selling_points=selling_points
        )
    
    except Exception as e:
        logger.error(f"生成失败: {e}")
        raise


@app.get("/")
async def root():
    return {"message": "海青菜品研发API运行中"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "haiqing-dish-rnd-backend"}


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
