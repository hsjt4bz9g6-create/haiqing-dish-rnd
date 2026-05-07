"""
菜品应用研发工作台 - Web应用
大连海青水产有限公司 - 菜品研发系统
"""
import os
import json
from typing import List, Optional
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from coze_coding_dev_sdk import SearchClient, LLMClient, ImageGenerationClient
from coze_coding_utils.runtime_ctx.context import new_context
from langchain_core.messages import HumanMessage, SystemMessage

# 创建FastAPI应用
app = FastAPI(title="菜品应用研发工作台", description="大连海青水产 - 菜品研发系统")

# 静态文件目录
static_dir = os.path.join(os.path.dirname(__file__), "static")
if not os.path.exists(static_dir):
    os.makedirs(static_dir)

app.mount("/static", StaticFiles(directory=static_dir), name="static")


# ========== 数据模型 ==========
class DishInfo(BaseModel):
    """菜品信息"""
    name: str
    main_ingredient: str
    main_ingredient_weight: str
    auxiliary_ingredient: str
    auxiliary_ingredient_weight: str
    cooking_method: str


class InsightItem(BaseModel):
    """社媒洞察项"""
    keyword: str
    description: str
    source: str
    url: str


class GenerateDishRequest(BaseModel):
    """生成菜品请求"""
    dish_info: DishInfo


class GenerateDishResponse(BaseModel):
    """生成菜品响应"""
    dish_name: str
    image_url: str
    selling_points: List[str]


# ========== API接口 ==========

@app.get("/", response_class=HTMLResponse)
async def index():
    """主页"""
    html_path = os.path.join(os.path.dirname(__file__), "templates", "index.html")
    if not os.path.exists(html_path):
        # 如果模板不存在，返回内置HTML
        return get_builtin_html()
    
    with open(html_path, "r", encoding="utf-8") as f:
        return f.read()


@app.get("/api/insights/dianping")
async def get_dianping_insights(keyword: Optional[str] = "深海鱼 鳕鱼"):
    """
    获取大众点评餐饮洞察
    搜索大众点评上的深海鱼菜品
    """
    try:
        ctx = new_context(method="search.web")
        client = SearchClient(ctx=ctx)
        
        # 搜索大众点评深海鱼菜品
        response = client.search(
            query=f"{keyword} 菜品 做法",
            sites="dianping.com",
            count=10,
            need_summary=True
        )
        
        insights = []
        if response.web_items:
            for item in response.web_items:
                # 使用AI提炼关键词和简介
                insights.append({
                    "keyword": item.title[:50] if item.title else "",
                    "description": item.snippet[:100] if item.snippet else "",
                    "source": item.site_name or "大众点评",
                    "url": item.url
                })
        
        return {"success": True, "data": insights}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.get("/api/insights/xiaohongshu")
async def get_xiaohongshu_insights(keyword: Optional[str] = "家庭深海鱼"):
    """
    获取小红书家庭深海鱼洞察
    搜索小红书上的家庭深海鱼菜品
    """
    try:
        ctx = new_context(method="search.web")
        client = SearchClient(ctx=ctx)
        
        # 搜索小红书家庭深海鱼菜品
        response = client.search(
            query=f"{keyword} 菜谱 教程",
            sites="xiaohongshu.com",
            count=10,
            need_summary=True
        )
        
        insights = []
        if response.web_items:
            for item in response.web_items:
                insights.append({
                    "keyword": item.title[:50] if item.title else "",
                    "description": item.snippet[:100] if item.snippet else "",
                    "source": item.site_name or "小红书",
                    "url": item.url
                })
        
        return {"success": True, "data": insights}
    
    except Exception as e:
        return {"success": False, "error": str(e)}


@app.post("/api/dish/generate")
async def generate_dish(request: GenerateDishRequest):
    """
    生成菜品图片和卖点
    """
    try:
        dish_info = request.dish_info
        
        # 1. 生成菜品图片
        ctx_img = new_context(method="generate")
        img_client = ImageGenerationClient(ctx=ctx_img)
        
        # 构建图片生成提示词
        prompt = f"""
        专业美食摄影，高清菜品图片：
        菜品名称：{dish_info.name}
        主料：{dish_info.main_ingredient} {dish_info.main_ingredient_weight}
        辅料：{dish_info.auxiliary_ingredient} {dish_info.auxiliary_ingredient_weight}
        烹饪方式：{dish_info.cooking_method}
        
        要求：
        - 高品质美食摄影
        - 自然光线
        - 专业摆盘
        - 清晰展现食材和烹饪效果
        - 诱人的色泽和质感
        """
        
        img_response = img_client.generate(
            prompt=prompt,
            size="2K",
            watermark=False
        )
        
        if not img_response.success:
            raise HTTPException(status_code=500, detail="图片生成失败")
        
        image_url = img_response.image_urls[0] if img_response.image_urls else ""
        
        # 2. 生成菜品卖点
        ctx_llm = new_context(method="invoke")
        llm_client = LLMClient(ctx=ctx_llm)
        
        # 构建提示词
        system_prompt = """你是一位专业的餐饮产品营销专家，擅长提炼菜品卖点和撰写美食文案。
你需要根据菜品信息，提炼出3-5个核心卖点，包括：
1. 口味特点（风味、口感、层次）
2. 适用场景（家庭聚餐、商务宴请、日常快手菜等）
3. 目标人群（儿童、老人、健身人群、白领等）
4. 营养价值（蛋白质、低脂、健康等）
5. 制作优势（简单易做、快手菜、适合批量制作等）

输出格式：
{
  "selling_points": ["卖点1", "卖点2", "卖点3"]
}

只输出JSON，不要输出其他内容。"""
        
        user_prompt = f"""
        菜品名称：{dish_info.name}
        主料：{dish_info.main_ingredient} {dish_info.main_ingredient_weight}
        辅料：{dish_info.auxiliary_ingredient} {dish_info.auxiliary_ingredient_weight}
        烹饪方式：{dish_info.cooking_method}
        
        请提炼这道菜的核心卖点。
        """
        
        messages = [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt)
        ]
        
        llm_response = llm_client.invoke(
            messages=messages,
            model="doubao-seed-1-8-251228",
            temperature=0.7
        )
        
        # 解析LLM响应
        selling_points = []
        if isinstance(llm_response.content, str):
            try:
                # 尝试提取JSON
                content = llm_response.content.strip()
                # 去除可能的markdown代码块标记
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                
                result = json.loads(content.strip())
                selling_points = result.get("selling_points", [])
            except json.JSONDecodeError:
                # 如果JSON解析失败，按行分割
                selling_points = [line.strip() for line in llm_response.content.split("\n") if line.strip()]
        
        return {
            "success": True,
            "data": {
                "dish_name": dish_info.name,
                "image_url": image_url,
                "selling_points": selling_points[:5]  # 最多返回5个卖点
            }
        }
    
    except Exception as e:
        return {"success": False, "error": str(e)}


# ========== 内置HTML模板 ==========
def get_builtin_html() -> str:
    """返回内置HTML模板（符合海青水产设计风格）"""
    return """
<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>菜品应用研发工作台 - 大连海青水产</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Microsoft YaHei', '微软雅黑', Arial, sans-serif;
            background: linear-gradient(135deg, #003366 0%, #00509e 100%);
            min-height: 100vh;
            color: #333;
        }
        
        /* 头部 */
        .header {
            background: rgba(255, 255, 255, 0.95);
            padding: 20px 40px;
            box-shadow: 0 2px 10px rgba(0, 51, 102, 0.1);
            display: flex;
            align-items: center;
            justify-content: space-between;
        }
        
        .header h1 {
            color: #003366;
            font-size: 28px;
            font-weight: 600;
        }
        
        .header .subtitle {
            color: #00509e;
            font-size: 14px;
            margin-top: 5px;
        }
        
        .logo {
            display: flex;
            align-items: center;
            gap: 15px;
        }
        
        .logo-icon {
            width: 50px;
            height: 50px;
            background: linear-gradient(135deg, #003366, #00509e);
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            color: white;
            font-size: 24px;
            font-weight: bold;
        }
        
        /* 主容器 */
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
        /* 卡片 */
        .card {
            background: rgba(255, 255, 255, 0.95);
            border-radius: 15px;
            padding: 30px;
            box-shadow: 0 4px 20px rgba(0, 51, 102, 0.1);
        }
        
        .card h2 {
            color: #003366;
            font-size: 22px;
            margin-bottom: 20px;
            padding-bottom: 15px;
            border-bottom: 2px solid #00509e;
            display: flex;
            align-items: center;
            gap: 10px;
        }
        
        .card h2::before {
            content: '';
            width: 4px;
            height: 22px;
            background: #003366;
            border-radius: 2px;
        }
        
        /* 社媒洞察区 */
        .insights-tabs {
            display: flex;
            gap: 10px;
            margin-bottom: 20px;
        }
        
        .tab-btn {
            padding: 10px 20px;
            background: #f0f0f0;
            border: none;
            border-radius: 8px;
            color: #666;
            cursor: pointer;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .tab-btn.active {
            background: #003366;
            color: white;
        }
        
        .tab-btn:hover {
            background: #00509e;
            color: white;
        }
        
        .insights-list {
            max-height: 500px;
            overflow-y: auto;
        }
        
        .insight-item {
            padding: 15px;
            background: #f8f9fa;
            border-radius: 8px;
            margin-bottom: 10px;
            border-left: 3px solid #003366;
            transition: all 0.3s;
        }
        
        .insight-item:hover {
            transform: translateX(5px);
            box-shadow: 0 2px 10px rgba(0, 51, 102, 0.1);
        }
        
        .insight-item h3 {
            color: #003366;
            font-size: 16px;
            margin-bottom: 8px;
        }
        
        .insight-item p {
            color: #666;
            font-size: 14px;
            line-height: 1.6;
            margin-bottom: 8px;
        }
        
        .insight-item a {
            color: #00509e;
            text-decoration: none;
            font-size: 12px;
        }
        
        .insight-item a:hover {
            text-decoration: underline;
        }
        
        /* 菜品研发区 */
        .form-group {
            margin-bottom: 20px;
        }
        
        .form-group label {
            display: block;
            color: #003366;
            font-size: 14px;
            font-weight: 600;
            margin-bottom: 8px;
        }
        
        .form-group input,
        .form-group textarea {
            width: 100%;
            padding: 12px 15px;
            border: 2px solid #e0e0e0;
            border-radius: 8px;
            font-size: 14px;
            transition: all 0.3s;
        }
        
        .form-group input:focus,
        .form-group textarea:focus {
            outline: none;
            border-color: #003366;
            box-shadow: 0 0 0 3px rgba(0, 51, 102, 0.1);
        }
        
        .form-row {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 15px;
        }
        
        .btn-primary {
            width: 100%;
            padding: 15px;
            background: linear-gradient(135deg, #003366, #00509e);
            color: white;
            border: none;
            border-radius: 8px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.3s;
        }
        
        .btn-primary:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 15px rgba(0, 51, 102, 0.3);
        }
        
        .btn-primary:disabled {
            background: #ccc;
            cursor: not-allowed;
            transform: none;
        }
        
        /* 结果展示区 */
        .result-section {
            margin-top: 30px;
            padding-top: 30px;
            border-top: 2px solid #e0e0e0;
        }
        
        .result-section h3 {
            color: #003366;
            font-size: 18px;
            margin-bottom: 20px;
        }
        
        .dish-image {
            width: 100%;
            max-height: 400px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 20px;
            box-shadow: 0 4px 15px rgba(0, 51, 102, 0.1);
        }
        
        .selling-points {
            list-style: none;
        }
        
        .selling-points li {
            padding: 12px 15px;
            background: linear-gradient(135deg, #f8f9fa, #e9ecef);
            border-radius: 8px;
            margin-bottom: 10px;
            color: #333;
            border-left: 3px solid #003366;
        }
        
        .selling-points li::before {
            content: '✓';
            color: #003366;
            font-weight: bold;
            margin-right: 10px;
        }
        
        /* 加载动画 */
        .loading {
            text-align: center;
            padding: 20px;
            color: #666;
        }
        
        .loading::after {
            content: '...';
            animation: dots 1.5s steps(4, end) infinite;
        }
        
        @keyframes dots {
            0%, 20% { content: '.'; }
            40% { content: '..'; }
            60%, 100% { content: '...'; }
        }
        
        /* 响应式 */
        @media (max-width: 1024px) {
            .container {
                grid-template-columns: 1fr;
            }
        }
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">
            <div class="logo-icon">海</div>
            <div>
                <h1>菜品应用研发工作台</h1>
                <div class="subtitle">大连海青水产有限公司 - 专业深海鱼研发平台</div>
            </div>
        </div>
    </div>
    
    <div class="container">
        <!-- 左侧：社媒洞察区 -->
        <div class="card">
            <h2>社媒洞察</h2>
            
            <div class="insights-tabs">
                <button class="tab-btn active" onclick="loadInsights('dianping')">
                    大众点评
                </button>
                <button class="tab-btn" onclick="loadInsights('xiaohongshu')">
                    小红书
                </button>
                <button onclick="refreshInsights()" style="margin-left: auto; padding: 10px 20px; background: #00509e; color: white; border: none; border-radius: 8px; cursor: pointer;">
                    刷新
                </button>
            </div>
            
            <div class="insights-list" id="insightsList">
                <div class="loading">正在加载洞察数据</div>
            </div>
        </div>
        
        <!-- 右侧：菜品研发区 -->
        <div class="card">
            <h2>菜品研发</h2>
            
            <div class="form-group">
                <label>菜品名称</label>
                <input type="text" id="dishName" placeholder="例如：香煎鳕鱼配柠檬黄油酱">
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>主料名称</label>
                    <input type="text" id="mainIngredient" placeholder="例如：鳕鱼">
                </div>
                <div class="form-group">
                    <label>主料克重</label>
                    <input type="text" id="mainWeight" placeholder="例如：200g">
                </div>
            </div>
            
            <div class="form-row">
                <div class="form-group">
                    <label>辅料名称</label>
                    <input type="text" id="auxIngredient" placeholder="例如：柠檬、黄油">
                </div>
                <div class="form-group">
                    <label>辅料克重</label>
                    <input type="text" id="auxWeight" placeholder="例如：50g">
                </div>
            </div>
            
            <div class="form-group">
                <label>烹饪方法</label>
                <textarea id="cookingMethod" rows="4" placeholder="详细描述烹饪步骤和方法..."></textarea>
            </div>
            
            <button class="btn-primary" onclick="generateDish()">
                生成菜品图片和卖点
            </button>
            
            <!-- 结果展示区 -->
            <div class="result-section" id="resultSection" style="display: none;">
                <h3>生成结果</h3>
                <img id="dishImage" class="dish-image" src="" alt="菜品图片">
                <h4 style="color: #003366; margin-bottom: 15px;">菜品卖点</h4>
                <ul class="selling-points" id="sellingPoints"></ul>
            </div>
        </div>
    </div>
    
    <script>
        let currentTab = 'dianping';
        
        // 加载洞察数据
        async function loadInsights(type) {
            currentTab = type;
            
            // 更新标签状态
            document.querySelectorAll('.tab-btn').forEach(btn => {
                btn.classList.remove('active');
            });
            event.target.classList.add('active');
            
            const list = document.getElementById('insightsList');
            list.innerHTML = '<div class="loading">正在加载洞察数据</div>';
            
            try {
                const url = type === 'dianping' ? '/api/insights/dianping' : '/api/insights/xiaohongshu';
                const response = await fetch(url);
                const data = await response.json();
                
                if (data.success && data.data.length > 0) {
                    list.innerHTML = data.data.map(item => `
                        <div class="insight-item">
                            <h3>${item.keyword}</h3>
                            <p>${item.description}</p>
                            <a href="${item.url}" target="_blank">来源：${item.source} →</a>
                        </div>
                    `).join('');
                } else {
                    list.innerHTML = '<p style="text-align: center; color: #999; padding: 20px;">暂无数据</p>';
                }
            } catch (error) {
                list.innerHTML = `<p style="text-align: center; color: #e74c3c; padding: 20px;">加载失败：${error.message}</p>`;
            }
        }
        
        // 刷新洞察
        function refreshInsights() {
            loadInsights(currentTab);
        }
        
        // 生成菜品
        async function generateDish() {
            const dishName = document.getElementById('dishName').value;
            const mainIngredient = document.getElementById('mainIngredient').value;
            const mainWeight = document.getElementById('mainWeight').value;
            const auxIngredient = document.getElementById('auxIngredient').value;
            const auxWeight = document.getElementById('auxWeight').value;
            const cookingMethod = document.getElementById('cookingMethod').value;
            
            if (!dishName || !mainIngredient || !cookingMethod) {
                alert('请填写菜品名称、主料和烹饪方法！');
                return;
            }
            
            const btn = document.querySelector('.btn-primary');
            btn.disabled = true;
            btn.textContent = '正在生成...';
            
            try {
                const response = await fetch('/api/dish/generate', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        dish_info: {
                            name: dishName,
                            main_ingredient: mainIngredient,
                            main_ingredient_weight: mainWeight,
                            auxiliary_ingredient: auxIngredient,
                            auxiliary_ingredient_weight: auxWeight,
                            cooking_method: cookingMethod
                        }
                    })
                });
                
                const data = await response.json();
                
                if (data.success) {
                    // 显示结果
                    document.getElementById('resultSection').style.display = 'block';
                    document.getElementById('dishImage').src = data.data.image_url;
                    
                    const pointsList = document.getElementById('sellingPoints');
                    pointsList.innerHTML = data.data.selling_points.map(point => 
                        `<li>${point}</li>`
                    ).join('');
                    
                    // 滚动到结果区
                    document.getElementById('resultSection').scrollIntoView({ behavior: 'smooth' });
                } else {
                    alert('生成失败：' + data.error);
                }
            } catch (error) {
                alert('生成失败：' + error.message);
            } finally {
                btn.disabled = false;
                btn.textContent = '生成菜品图片和卖点';
            }
        }
        
        // 页面加载时自动加载大众点评洞察
        window.onload = function() {
            loadInsights('dianping');
        };
    </script>
</body>
</html>
    """


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
