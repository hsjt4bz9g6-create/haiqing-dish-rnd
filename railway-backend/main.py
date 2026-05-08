# 海青菜品研发API - Railway部署

import os
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Railway会设置PORT环境变量
PORT = int(os.environ.get("PORT", 8000))

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


@app.get("/api/web/insights/{platform}")
async def get_insights(platform: str):
    """获取社媒洞察"""
    logger.info(f"获取洞察: platform={platform}")
    
    insights = [
        InsightItem(
            keyword="香煎鳕鱼",
            description="外酥里嫩，营养丰富",
            image_url="https://example.com/cod.jpg",
            source_url="https://www.dianping.com"
        ),
        InsightItem(
            keyword="三文鱼刺身",
            description="新鲜美味，入口即化",
            image_url="https://example.com/salmon.jpg",
            source_url="https://www.xiaohongshu.com"
        ),
    ]
    
    return InsightResponse(platform=platform, insights=insights)


@app.post("/api/web/dish/generate")
async def generate_dish(request: DishGenerateRequest):
    """生成菜品图片和卖点"""
    logger.info(f"生成菜品: {request.dish_name}")
    
    return DishGenerateResponse(
        dish_name=request.dish_name,
        image_url="",
        selling_points=[
            "肉质鲜嫩",
            "营养丰富",
            "做法简单",
            "老少皆宜",
            "色香味俱佳"
        ]
    )


@app.get("/")
async def root():
    return {"message": "海青菜品研发API运行中", "status": "ok"}


@app.get("/health")
async def health():
    """健康检查"""
    return {"status": "healthy", "service": "haiqing-dish-rnd-backend", "port": PORT}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
