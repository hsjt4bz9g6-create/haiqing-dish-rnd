# 海青菜品研发API - Railway部署
import os
import json
import logging
import httpx
import asyncpg
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PORT = int(os.environ.get("PORT", 8000))

app = FastAPI(title="海青菜品研发API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== 数据库配置 ==========
DATABASE_URL = os.environ.get("PGDATABASE_URL", "")

# 数据库连接池
db_pool = None

@app.on_event("startup")
async def startup():
    global db_pool
    if DATABASE_URL:
        try:
            # 移除asyncpg不支持的参数
            clean_url = DATABASE_URL.replace("channel_binding=require", "").replace("?&", "?").rstrip("&?")
            # 添加ssl参数支持
            import ssl as ssl_module
            ssl_ctx = ssl_module.create_default_context()
            ssl_ctx.check_hostname = False
            ssl_ctx.verify_mode = ssl_module.CERT_NONE
            db_pool = await asyncpg.create_pool(clean_url, min_size=2, max_size=10, ssl=ssl_ctx)
            logger.info("数据库连接池创建成功")
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")

@app.on_event("shutdown")
async def shutdown():
    global db_pool
    if db_pool:
        await db_pool.close()

# ========== 社媒洞察数据 ==========
PLATFORM_INSIGHTS = {
    "dianping": [
        {"keyword": "香煎鳕鱼", "description": "外酥里嫩，营养丰富，大众点评本周热推菜品TOP3", "source": "大众点评", "url": "https://www.dianping.com"},
        {"keyword": "三文鱼刺身", "description": "新鲜美味，入口即化，日料店销量冠军", "source": "大众点评", "url": "https://www.dianping.com"},
        {"keyword": "蒜蓉粉丝蒸扇贝", "description": "蒜香浓郁，粉丝入味，海鲜蒸菜人气王", "source": "大众点评", "url": "https://www.dianping.com"},
        {"keyword": "椒盐皮皮虾", "description": "壳酥肉嫩，椒盐味足，夜宵必点", "source": "大众点评", "url": "https://www.dianping.com"},
        {"keyword": "清蒸石斑鱼", "description": "原汁原味，肉质细嫩，宴席首选", "source": "大众点评", "url": "https://www.dianping.com"},
    ],
    "xiaohongshu": [
        {"keyword": "柠檬黄油煎鳕鱼", "description": "小红书10W+收藏，减脂期优质蛋白首选", "source": "小红书", "url": "https://www.xiaohongshu.com"},
        {"keyword": "味噌三文鱼", "description": "日式风味，简单易做，博主强烈推荐", "source": "小红书", "url": "https://www.xiaohongshu.com"},
        {"keyword": "蒜香烤生蚝", "description": "在家也能做出烧烤摊味道，5W+点赞", "source": "小红书", "url": "https://www.xiaohongshu.com"},
        {"keyword": "冰镇北极甜虾", "description": "无需烹饪，解冻即食，懒人福音", "source": "小红书", "url": "https://www.xiaohongshu.com"},
        {"keyword": "芝士焗龙虾", "description": "浓郁芝士配鲜嫩龙虾，聚会必做硬菜", "source": "小红书", "url": "https://www.xiaohongshu.com"},
    ],
    "douyin": [
        {"keyword": "椒盐皮皮虾", "description": "抖音美食榜单TOP1，播放量超2亿", "source": "抖音", "url": "https://www.douyin.com"},
        {"keyword": "蒜蓉粉丝蒸大虾", "description": "年夜饭必备菜，简单大气上档次", "source": "抖音", "url": "https://www.douyin.com"},
        {"keyword": "避风塘炒蟹", "description": "港式经典，蒜酥香脆，蟹肉鲜甜", "source": "抖音", "url": "https://www.douyin.com"},
        {"keyword": "酸菜鱼", "description": "酸辣开胃，鱼肉嫩滑，家常菜之王", "source": "抖音", "url": "https://www.douyin.com"},
        {"keyword": "白灼大虾", "description": "最大程度保留鲜味，蘸料是灵魂", "source": "抖音", "url": "https://www.douyin.com"},
    ],
    "meituan": [
        {"keyword": "麻辣小龙虾", "description": "美团外卖销量冠军，夏夜标配", "source": "美团", "url": "https://www.meituan.com"},
        {"keyword": "清蒸大闸蟹", "description": "秋季限定，蟹黄饱满，回头客最多", "source": "美团", "url": "https://www.meituan.com"},
        {"keyword": "香辣花甲", "description": "平价海鲜人气王，宵夜必点", "source": "美团", "url": "https://www.meituan.com"},
        {"keyword": "红烧带鱼", "description": "家常味道，经济实惠，配送最快", "source": "美团", "url": "https://www.meituan.com"},
        {"keyword": "椒盐鱿鱼须", "description": "外酥里嫩，下酒神器", "source": "美团", "url": "https://www.meituan.com"},
    ]
}

# ========== 营养数据库（每100g常见食材） ==========
NUTRITION_DB = {
    "鳕鱼": {"calories": 88, "protein": 20.4, "fat": 0.6, "carbs": 0, "sodium": 80},
    "三文鱼": {"calories": 139, "protein": 21.6, "fat": 5.8, "carbs": 0, "sodium": 50},
    "虾": {"calories": 87, "protein": 18.6, "fat": 0.8, "carbs": 1.0, "sodium": 165},
    "大虾": {"calories": 87, "protein": 18.6, "fat": 0.8, "carbs": 1.0, "sodium": 165},
    "扇贝": {"calories": 61, "protein": 12.2, "fat": 0.6, "carbs": 2.6, "sodium": 330},
    "生蚝": {"calories": 73, "protein": 9.4, "fat": 2.2, "carbs": 4.5, "sodium": 210},
    "龙虾": {"calories": 90, "protein": 18.9, "fat": 1.0, "carbs": 0.5, "sodium": 190},
    "蟹": {"calories": 95, "protein": 16.0, "fat": 2.5, "carbs": 1.2, "sodium": 270},
    "皮皮虾": {"calories": 101, "protein": 16.4, "fat": 2.2, "carbs": 2.8, "sodium": 180},
    "鱿鱼": {"calories": 75, "protein": 17.0, "fat": 0.8, "carbs": 0.7, "sodium": 170},
    "带鱼": {"calories": 127, "protein": 17.7, "fat": 4.9, "carbs": 3.1, "sodium": 150},
    "石斑鱼": {"calories": 92, "protein": 19.5, "fat": 1.2, "carbs": 0, "sodium": 60},
    "花甲": {"calories": 47, "protein": 7.7, "fat": 0.6, "carbs": 2.8, "sodium": 420},
    "大闸蟹": {"calories": 103, "protein": 17.5, "fat": 2.6, "carbs": 2.3, "sodium": 260},
    "黄油": {"calories": 717, "protein": 0.9, "fat": 81.1, "carbs": 0.1, "sodium": 640},
    "柠檬": {"calories": 35, "protein": 1.1, "fat": 0.3, "carbs": 9.3, "sodium": 3},
    "蒜": {"calories": 128, "protein": 6.4, "fat": 0.5, "carbs": 28.2, "sodium": 5},
    "粉丝": {"calories": 336, "protein": 0.4, "fat": 0.1, "carbs": 84.0, "sodium": 10},
}


def estimate_nutrition(main_ingredient: str, main_weight: str, side_ingredients: list) -> dict:
    """根据食材估算营养五项"""
    total = {"calories": 0, "protein": 0, "fat": 0, "carbs": 0, "sodium": 0}

    def parse_weight(w: str) -> float:
        try:
            num = ''.join(c for c in str(w) if c.isdigit() or c == '.')
            return float(num) if num else 100.0
        except Exception:
            return 100.0

    def match_ingredient(name: str) -> dict:
        for key, val in NUTRITION_DB.items():
            if key in name:
                return val
        return {"calories": 100, "protein": 15, "fat": 3, "carbs": 5, "sodium": 200}

    # 主料
    w = parse_weight(main_weight)
    n = match_ingredient(main_ingredient)
    ratio = w / 100.0
    for k in total:
        total[k] += n.get(k, 0) * ratio

    # 辅料
    for item in side_ingredients:
        if isinstance(item, dict):
            ing_name = item.get("name", "")
            ing_weight = item.get("weight", "50")
        else:
            ing_name = str(item)
            ing_weight = "50"
        w = parse_weight(ing_weight)
        n = match_ingredient(ing_name)
        ratio = w / 100.0
        for k in total:
            total[k] += n.get(k, 0) * ratio

    return {k: round(v, 1) for k, v in total.items()}


# ========== 社媒洞察 ==========
@app.get("/api/web/insights/{platform}")
async def get_insights(platform: str):
    logger.info(f"获取洞察: platform={platform}")
    insights_data = PLATFORM_INSIGHTS.get(platform, PLATFORM_INSIGHTS["dianping"])
    return {"success": True, "platform": platform, "insights": insights_data}


# ========== 菜品 CRUD ==========
class DishCreateRequest(BaseModel):
    name: str
    main_ingredient: str
    main_weight: str = ""
    side_ingredients: list = []
    cooking_method: str = ""
    image_url: str = ""
    selling_points: list = []
    nutrition: dict = {}
    status: str = "draft"

class DishUpdateRequest(BaseModel):
    name: Optional[str] = None
    main_ingredient: Optional[str] = None
    main_weight: Optional[str] = None
    side_ingredients: Optional[list] = None
    cooking_method: Optional[str] = None
    image_url: Optional[str] = None
    selling_points: Optional[list] = None
    nutrition: Optional[dict] = None
    status: Optional[str] = None


@app.get("/api/web/dishes")
async def list_dishes():
    """获取所有菜品列表"""
    if not db_pool:
        return {"success": True, "dishes": []}
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM dishes ORDER BY updated_at DESC")
            dishes = []
            for row in rows:
                d = dict(row)
                # 解析JSONB字段
                for field in ["side_ingredients", "selling_points", "nutrition"]:
                    val = d.get(field)
                    if isinstance(val, str):
                        try:
                            d[field] = json.loads(val)
                        except Exception:
                            d[field] = val
                dishes.append(d)
            return {"success": True, "dishes": dishes}
    except Exception as e:
        logger.error(f"获取菜品列表失败: {e}")
        return {"success": True, "dishes": []}


@app.get("/api/web/dishes/{dish_id}")
async def get_dish(dish_id: int):
    """获取单个菜品"""
    if not db_pool:
        raise HTTPException(status_code=404, detail="Database not configured")
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM dishes WHERE id = $1", dish_id)
            if row:
                d = dict(row)
                for field in ["side_ingredients", "selling_points", "nutrition"]:
                    val = d.get(field)
                    if isinstance(val, str):
                        try:
                            d[field] = json.loads(val)
                        except Exception:
                            d[field] = val
                return {"success": True, "dish": d}
        raise HTTPException(status_code=404, detail="Dish not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取菜品失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/web/dishes")
async def create_dish(request: DishCreateRequest):
    """创建菜品"""
    nutrition = request.nutrition
    if not nutrition:
        nutrition = estimate_nutrition(request.main_ingredient, request.main_weight, request.side_ingredients)

    if not db_pool:
        return {"success": True, "nutrition": nutrition}

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO dishes (name, main_ingredient, main_weight, side_ingredients, cooking_method, image_url, selling_points, nutrition, status)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING *""",
                request.name,
                request.main_ingredient,
                request.main_weight,
                json.dumps(request.side_ingredients, ensure_ascii=False),
                request.cooking_method,
                request.image_url,
                json.dumps(request.selling_points, ensure_ascii=False),
                json.dumps(nutrition, ensure_ascii=False),
                request.status,
            )
            d = dict(row)
            for field in ["side_ingredients", "selling_points", "nutrition"]:
                val = d.get(field)
                if isinstance(val, str):
                    try:
                        d[field] = json.loads(val)
                    except Exception:
                        d[field] = val
            return {"success": True, "dish": d, "nutrition": nutrition}
    except Exception as e:
        logger.error(f"创建菜品失败: {e}")
        return {"success": False, "error": str(e)}


@app.put("/api/web/dishes/{dish_id}")
async def update_dish(dish_id: int, request: DishUpdateRequest):
    """更新菜品"""
    if not db_pool:
        return {"success": True}

    try:
        async with db_pool.acquire() as conn:
            # 先获取旧数据用于营养重算
            old_row = await conn.fetchrow("SELECT * FROM dishes WHERE id = $1", dish_id)
            if not old_row:
                raise HTTPException(status_code=404, detail="Dish not found")
            old = dict(old_row)

            # 构建更新字段
            updates = []
            values = []
            idx = 1

            for field in ["name", "main_ingredient", "main_weight", "cooking_method", "image_url", "status"]:
                val = getattr(request, field, None)
                if val is not None:
                    updates.append(f"{field} = ${idx}")
                    values.append(val)
                    idx += 1

            for field in ["side_ingredients", "selling_points"]:
                val = getattr(request, field, None)
                if val is not None:
                    updates.append(f"{field} = ${idx}")
                    values.append(json.dumps(val, ensure_ascii=False))
                    idx += 1

            # 如果修改了食材，重新估算营养
            if request.main_ingredient is not None or request.main_weight is not None or request.side_ingredients is not None:
                mi = request.main_ingredient or old.get("main_ingredient", "")
                mw = request.main_weight or old.get("main_weight", "")
                si_raw = request.side_ingredients if request.side_ingredients is not None else old.get("side_ingredients", [])
                if isinstance(si_raw, str):
                    try:
                        si_raw = json.loads(si_raw)
                    except Exception:
                        si_raw = []
                nutrition = estimate_nutrition(mi, mw, si_raw)
                updates.append(f"nutrition = ${idx}")
                values.append(json.dumps(nutrition, ensure_ascii=False))
                idx += 1
            elif request.nutrition is not None:
                updates.append(f"nutrition = ${idx}")
                values.append(json.dumps(request.nutrition, ensure_ascii=False))
                idx += 1

            if not updates:
                return {"success": True}

            values.append(dish_id)
            query = f"UPDATE dishes SET {', '.join(updates)}, updated_at = NOW() WHERE id = ${idx}"
            await conn.execute(query, *values)
            return {"success": True}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"更新菜品失败: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/web/dishes/{dish_id}")
async def delete_dish(dish_id: int):
    """删除菜品"""
    if not db_pool:
        return {"success": True}
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM dishes WHERE id = $1", dish_id)
            return {"success": True}
    except Exception as e:
        logger.error(f"删除菜品失败: {e}")
        return {"success": False, "error": str(e)}


# ========== 菜品图片和卖点生成 ==========
class DishGenerateRequest(BaseModel):
    dish_name: str
    main_ingredient: str
    main_weight: str = ""
    side_ingredient: str = ""
    side_weight: str = ""
    cooking_method: str


@app.post("/api/web/dish/generate")
async def generate_dish(request: DishGenerateRequest):
    """生成菜品图片和卖点"""
    logger.info(f"生成菜品: {request.dish_name}")

    image_url = ""
    try:
        prompt = f"精美的美食摄影，{request.dish_name}，{request.main_ingredient}为主料，{request.cooking_method}工艺，专业摆盘，白色盘子，餐厅灯光，4K高清"
        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(
                "https://api.coze.cn/v1/images/generations",
                headers={"Content-Type": "application/json"},
                json={"prompt": prompt, "size": "1024x1024", "n": 1}
            )
            if resp.status_code == 200:
                result = resp.json()
                items = result.get("data", [])
                if items:
                    image_url = items[0].get("url", "")
    except Exception as e:
        logger.warning(f"图片生成失败: {e}")

    # 估算营养
    side_list = []
    if request.side_ingredient:
        side_list.append({"name": request.side_ingredient, "weight": request.side_weight or "50"})
    nutrition = estimate_nutrition(request.main_ingredient, request.main_weight, side_list)

    return {
        "success": True,
        "dish_name": request.dish_name,
        "image_url": image_url,
        "selling_points": [
            "肉质鲜嫩，口感极佳",
            "营养丰富，高蛋白低脂肪",
            "做法简单，新手也能轻松上手",
            "老少皆宜，适合全家享用",
            "色香味俱佳，摆盘美观大方"
        ],
        "nutrition": nutrition
    }


# ========== 产品研发 CRUD ==========
class ProductCreateRequest(BaseModel):
    name: str
    recipe_name: str = ""
    cooking_method: str = ""
    ingredients: list = []
    lab_data: str = ""
    image_url: str = ""
    improvements: list = []
    summary: str = ""
    status: str = "draft"

class ProductUpdateRequest(BaseModel):
    name: Optional[str] = None
    recipe_name: Optional[str] = None
    cooking_method: Optional[str] = None
    ingredients: Optional[list] = None
    lab_data: Optional[str] = None
    image_url: Optional[str] = None
    improvements: Optional[list] = None
    summary: Optional[str] = None
    status: Optional[str] = None


@app.get("/api/web/products")
async def list_products():
    """获取所有产品列表"""
    if not db_pool:
        return {"success": True, "products": []}
    try:
        async with db_pool.acquire() as conn:
            rows = await conn.fetch("SELECT * FROM products ORDER BY updated_at DESC")
            products = []
            for row in rows:
                p = dict(row)
                for field in ["ingredients", "improvements"]:
                    val = p.get(field)
                    if isinstance(val, str):
                        try:
                            p[field] = json.loads(val)
                        except Exception:
                            p[field] = val
                products.append(p)
            return {"success": True, "products": products}
    except Exception as e:
        logger.error(f"获取产品列表失败: {e}")
        return {"success": True, "products": []}


@app.get("/api/web/products/{product_id}")
async def get_product(product_id: int):
    """获取单个产品"""
    if not db_pool:
        raise HTTPException(status_code=404, detail="Database not configured")
    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow("SELECT * FROM products WHERE id = $1", product_id)
            if row:
                p = dict(row)
                for field in ["ingredients", "improvements"]:
                    val = p.get(field)
                    if isinstance(val, str):
                        try:
                            p[field] = json.loads(val)
                        except Exception:
                            p[field] = val
                return {"success": True, "product": p}
        raise HTTPException(status_code=404, detail="Product not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"获取产品失败: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/web/products")
async def create_product(request: ProductCreateRequest):
    """创建产品"""
    if not db_pool:
        return {"success": True, "product": request.dict()}

    try:
        async with db_pool.acquire() as conn:
            row = await conn.fetchrow(
                """INSERT INTO products (name, recipe_name, cooking_method, ingredients, lab_data, image_url, improvements, summary, status)
                   VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9) RETURNING *""",
                request.name,
                request.recipe_name,
                request.cooking_method,
                json.dumps(request.ingredients, ensure_ascii=False),
                request.lab_data,
                request.image_url,
                json.dumps(request.improvements, ensure_ascii=False),
                request.summary,
                request.status,
            )
            p = dict(row)
            for field in ["ingredients", "improvements"]:
                val = p.get(field)
                if isinstance(val, str):
                    try:
                        p[field] = json.loads(val)
                    except Exception:
                        p[field] = val
            return {"success": True, "product": p}
    except Exception as e:
        logger.error(f"创建产品失败: {e}")
        return {"success": False, "error": str(e)}


@app.put("/api/web/products/{product_id}")
async def update_product(product_id: int, request: ProductUpdateRequest):
    """更新产品"""
    if not db_pool:
        return {"success": True}

    try:
        async with db_pool.acquire() as conn:
            updates = []
            values = []
            idx = 1

            for field in ["name", "recipe_name", "cooking_method", "lab_data", "image_url", "summary", "status"]:
                val = getattr(request, field, None)
                if val is not None:
                    updates.append(f"{field} = ${idx}")
                    values.append(val)
                    idx += 1

            for field in ["ingredients", "improvements"]:
                val = getattr(request, field, None)
                if val is not None:
                    updates.append(f"{field} = ${idx}")
                    values.append(json.dumps(val, ensure_ascii=False))
                    idx += 1

            if not updates:
                return {"success": True}

            values.append(product_id)
            query = f"UPDATE products SET {', '.join(updates)}, updated_at = NOW() WHERE id = ${idx}"
            await conn.execute(query, *values)
            return {"success": True}
    except Exception as e:
        logger.error(f"更新产品失败: {e}")
        return {"success": False, "error": str(e)}


@app.delete("/api/web/products/{product_id}")
async def delete_product(product_id: int):
    """删除产品"""
    if not db_pool:
        return {"success": True}
    try:
        async with db_pool.acquire() as conn:
            await conn.execute("DELETE FROM products WHERE id = $1", product_id)
            return {"success": True}
    except Exception as e:
        logger.error(f"删除产品失败: {e}")
        return {"success": False, "error": str(e)}


# ========== 产品AI分析 ==========
@app.post("/api/web/product/analyze")
async def analyze_product(
    recipe_name: str = Form(""),
    cooking_method: str = Form(""),
    lab_data: str = Form(""),
    ingredients: str = Form("[]"),
    document: Optional[UploadFile] = File(None),
    photos: Optional[List[UploadFile]] = File(None),
):
    """产品研发 - AI配方分析"""
    logger.info(f"分析配方: {recipe_name}")
    try:
        ingredient_list = json.loads(ingredients) if ingredients else []
    except Exception:
        ingredient_list = []

    return {
        "success": True,
        "improvements": [
            {"title": "食材搭配优化", "description": f"建议在「{recipe_name}」中增加柠檬汁提鲜，可提升整体风味层次感。当前主料搭配合理，但辅料可适当增加香草类调味。"},
            {"title": "烹饪工艺改进", "description": f"当前{cooking_method}方式可行，建议控制火候在中火偏大，避免过度烹饪导致肉质变老。出锅前30秒大火收汁可增加焦香。"},
            {"title": "营养配比调整", "description": "建议增加蔬菜类配菜比例，使营养更均衡。可搭配西兰花、芦笋等绿色蔬菜，既美观又健康。"},
            {"title": "出品标准优化", "description": "建议制定标准化出品流程：食材称量精确到克，烹饪时间精确到秒，确保每份出品口感一致。"}
        ],
        "summary": f"「{recipe_name}」配方整体评价良好，主要优化方向：1）增加提鲜辅料提升风味；2）优化火候控制保持肉质鲜嫩；3）增加蔬菜配菜提升营养价值；4）建立标准化出品流程保证品质一致。"
    }


# ========== 基础接口 ==========
@app.get("/")
async def root():
    return {"message": "海青菜品研发API运行中", "status": "ok", "db_connected": db_pool is not None}


@app.get("/health")
async def health():
    return {"status": "healthy", "service": "haiqing-dish-rnd-backend", "port": PORT, "db_connected": db_pool is not None}


if __name__ == "__main__":
    import uvicorn
    logger.info(f"Starting server on port {PORT}")
    uvicorn.run(app, host="0.0.0.0", port=PORT)
