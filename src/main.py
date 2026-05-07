import argparse
import asyncio
import json
import threading
import traceback
import logging
import os
from typing import Any, Dict, Iterable, AsyncIterable, AsyncGenerator, Optional
import cozeloop
import uvicorn
import time
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import StreamingResponse, JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from langchain_core.runnables import RunnableConfig
from langgraph.graph import StateGraph, END
from langgraph.graph.state import CompiledStateGraph
from coze_coding_utils.runtime_ctx.context import new_context, Context
from coze_coding_utils.helper import graph_helper
from coze_coding_utils.log.node_log import LOG_FILE
from coze_coding_utils.log.write_log import setup_logging, request_context
from coze_coding_utils.log.config import LOG_LEVEL
from coze_coding_utils.error.classifier import ErrorClassifier, classify_error
from coze_coding_utils.helper.stream_runner import AgentStreamRunner, WorkflowStreamRunner,agent_stream_handler,workflow_stream_handler, RunOpt

# Web应用相关导入
from pydantic import BaseModel
from coze_coding_dev_sdk import SearchClient, LLMClient, ImageGenerationClient
from langchain_core.messages import HumanMessage, SystemMessage

setup_logging(
    log_file=LOG_FILE,
    max_bytes=100 * 1024 * 1024, # 100MB
    backup_count=5,
    log_level=LOG_LEVEL,
    use_json_format=True,
    console_output=True
)

logger = logging.getLogger(__name__)
from coze_coding_utils.helper.agent_helper import to_stream_input
from coze_coding_utils.openai.handler import OpenAIChatHandler
from coze_coding_utils.log.parser import LangGraphParser
from coze_coding_utils.log.err_trace import extract_core_stack
from coze_coding_utils.log.loop_trace import init_run_config, init_agent_config


# 超时配置常量
TIMEOUT_SECONDS = 900  # 15分钟

class GraphService:
    def __init__(self):
        # 用于跟踪正在运行的任务（使用asyncio.Task）
        self.running_tasks: Dict[str, asyncio.Task] = {}
        # 错误分类器
        self.error_classifier = ErrorClassifier()
        # stream runner
        self._agent_stream_runner = AgentStreamRunner()
        self._workflow_stream_runner = WorkflowStreamRunner()
        self._graph = None
        self._graph_lock = threading.Lock()

    def _get_graph(self, ctx=Context):
        if graph_helper.is_agent_proj():
            return graph_helper.get_agent_instance("agents.agent", ctx)

        if self._graph is not None:
            return self._graph
        with self._graph_lock:
            if self._graph is not None:
                return self._graph
            self._graph = graph_helper.get_graph_instance("graphs.graph")
            return self._graph

    @staticmethod
    def _sse_event(data: Any, event_id: Any = None) -> str:
        id_line = f"id: {event_id}\n" if event_id else ""
        return f"{id_line}event: message\ndata: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

    def _get_stream_runner(self):
        if graph_helper.is_agent_proj():
            return self._agent_stream_runner
        else:
            return self._workflow_stream_runner

    # 流式运行（原始迭代器）：本地调用使用
    def stream(self, payload: Dict[str, Any], run_config: RunnableConfig, ctx=Context) -> Iterable[Any]:
        graph = self._get_graph(ctx)
        stream_runner = self._get_stream_runner()
        for chunk in stream_runner.stream(payload, graph, run_config, ctx):
            yield chunk

    # 同步运行：本地/HTTP 通用
    async def run(self, payload: Dict[str, Any], ctx=None) -> Dict[str, Any]:
        if ctx is None:
            ctx = new_context("run")

        run_id = ctx.run_id
        logger.info(f"Starting run with run_id: {run_id}")

        try:
            graph = self._get_graph(ctx)
            # custom tracer
            run_config = init_run_config(graph, ctx)
            run_config["configurable"] = {"thread_id": ctx.run_id}

            # 直接调用，LangGraph会在当前任务上下文中执行
            # 如果当前任务被取消，LangGraph的执行也会被取消
            return await graph.ainvoke(payload, config=run_config, context=ctx)

        except asyncio.CancelledError:
            logger.info(f"Run {run_id} was cancelled")
            return {"status": "cancelled", "run_id": run_id, "message": "Execution was cancelled"}
        except Exception as e:
            # 使用错误分类器分类错误
            err = self.error_classifier.classify(e, {"node_name": "run", "run_id": run_id})
            # 记录详细的错误信息和堆栈跟踪
            logger.error(
                f"Error in GraphService.run: [{err.code}] {err.message}\n"
                f"Category: {err.category.name}\n"
                f"Traceback:\n{extract_core_stack()}"
            )
            # 保留原始异常堆栈，便于上层返回真正的报错位置
            raise
        finally:
            # 清理任务记录
            self.running_tasks.pop(run_id, None)

    # 流式运行（SSE 格式化）：HTTP 路由使用
    async def stream_sse(self, payload: Dict[str, Any], ctx=None, run_opt: Optional[RunOpt] = None) -> AsyncGenerator[str, None]:
        if ctx is None:
            ctx = new_context(method="stream_sse")
        if run_opt is None:
            run_opt = RunOpt()

        run_id = ctx.run_id
        logger.info(f"Starting stream with run_id: {run_id}")
        graph = self._get_graph(ctx)
        if graph_helper.is_agent_proj():
            run_config = init_agent_config(graph, ctx)
        else:
            run_config = init_run_config(graph, ctx)  # vibeflow

        is_workflow = not graph_helper.is_agent_proj()

        try:
            async for chunk in self.astream(payload, graph, run_config=run_config, ctx=ctx, run_opt=run_opt):
                if is_workflow and isinstance(chunk, tuple):
                    event_id, data = chunk
                    yield self._sse_event(data, event_id)
                else:
                    yield self._sse_event(chunk)
        finally:
            # 清理任务记录
            self.running_tasks.pop(run_id, None)
            cozeloop.flush()

    # 取消执行 - 使用asyncio的标准方式
    def cancel_run(self, run_id: str, ctx: Optional[Context] = None) -> Dict[str, Any]:
        """
        取消指定run_id的执行

        使用asyncio.Task.cancel()来取消任务,这是标准的Python异步取消机制。
        LangGraph会在节点之间检查CancelledError,实现优雅的取消。
        """
        logger.info(f"Attempting to cancel run_id: {run_id}")

        # 查找对应的任务
        if run_id in self.running_tasks:
            task = self.running_tasks[run_id]
            if not task.done():
                # 使用asyncio的标准取消机制
                # 这会在下一个await点抛出CancelledError
                task.cancel()
                logger.info(f"Cancellation requested for run_id: {run_id}")
                return {
                    "status": "success",
                    "run_id": run_id,
                    "message": "Cancellation signal sent, task will be cancelled at next await point"
                }
            else:
                logger.info(f"Task already completed for run_id: {run_id}")
                return {
                    "status": "already_completed",
                    "run_id": run_id,
                    "message": "Task has already completed"
                }
        else:
            logger.warning(f"No active task found for run_id: {run_id}")
            return {
                "status": "not_found",
                "run_id": run_id,
                "message": "No active task found with this run_id. Task may have already completed or run_id is invalid."
            }

    # 运行指定节点：本地/HTTP 通用
    async def run_node(self, node_id: str, payload: Dict[str, Any], ctx=None) -> Any:
        if ctx is None or Context.run_id == "":
            ctx = new_context(method="node_run")

        _graph = self._get_graph()
        node_func, input_cls, output_cls = graph_helper.get_graph_node_func_with_inout(_graph.get_graph(), node_id)
        if node_func is None or input_cls is None:
            raise KeyError(f"node_id '{node_id}' not found")

        parser = LangGraphParser(_graph)
        metadata = parser.get_node_metadata(node_id) or {}

        _g = StateGraph(input_cls, input_schema=input_cls, output_schema=output_cls)
        _g.add_node("sn", node_func, metadata=metadata)
        _g.set_entry_point("sn")
        _g.add_edge("sn", END)
        _graph = _g.compile()

        run_config = init_run_config(_graph, ctx)
        return await _graph.ainvoke(payload, config=run_config)

    def graph_inout_schema(self) -> Any:
        if graph_helper.is_agent_proj():
            return {"input_schema": {}, "output_schema": {}}
        builder = getattr(self._get_graph(), 'builder', None)
        if builder is not None:
            input_cls = getattr(builder, 'input_schema', None) or self.graph.get_input_schema()
            output_cls = getattr(builder, 'output_schema', None) or self.graph.get_output_schema()
        else:
            logger.warning(f"No builder input schema found for graph_inout_schema, using graph input schema instead")
            input_cls = self.graph.get_input_schema()
            output_cls = self.graph.get_output_schema()

        return {
            "input_schema": input_cls.model_json_schema(), 
            "output_schema": output_cls.model_json_schema(),
            "code":0,
            "msg":""
        }

    async def astream(self, payload: Dict[str, Any], graph: CompiledStateGraph, run_config: RunnableConfig, ctx=Context, run_opt: Optional[RunOpt] = None) -> AsyncIterable[Any]:
        stream_runner = self._get_stream_runner()
        async for chunk in stream_runner.astream(payload, graph, run_config, ctx, run_opt):
            yield chunk


service = GraphService()
app = FastAPI()

# 添加CORS支持，允许Web前端跨域访问
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源
    allow_credentials=True,
    allow_methods=["*"],  # 允许所有方法
    allow_headers=["*"],  # 允许所有头部
)

# OpenAI 兼容接口处理器
openai_handler = OpenAIChatHandler(service)


# ========== Web应用相关代码 ==========

# 数据模型
class DishInfo(BaseModel):
    """菜品信息"""
    name: str
    main_ingredient: str
    main_ingredient_weight: str
    auxiliary_ingredient: str
    auxiliary_ingredient_weight: str
    cooking_method: str


class GenerateDishRequest(BaseModel):
    """生成菜品请求"""
    dish_info: DishInfo


# Web应用主页
@app.get("/", response_class=HTMLResponse)
async def web_index():
    """菜品应用研发工作台主页"""
    try:
        with open("src/templates/dish-rnd-web.html", "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        logger.error(f"读取Web页面失败: {e}")
        return "<h1>页面加载失败</h1><p>请刷新重试</p>"


# 社媒洞察API
@app.get("/api/insights/dianping")
async def get_dianping_insights(keyword: Optional[str] = "深海鱼 鳕鱼"):
    """获取大众点评餐饮洞察（包含菜品图片）"""
    try:
        ctx = new_context(method="search.web")
        client = SearchClient(ctx=ctx)
        
        # 1. 搜索网页内容
        response = client.search(
            query=f"{keyword} 菜品 做法",
            sites="dianping.com",
            count=10,
            need_summary=True
        )
        
        # 2. 搜索图片
        img_ctx = new_context(method="search.image")
        img_client = SearchClient(ctx=img_ctx)
        img_response = img_client.image_search(
            query=f"{keyword} 菜品 美食",
            count=10
        )
        
        # 3. 构建图片URL映射
        image_map = {}
        if img_response.image_items:
            for img_item in img_response.image_items:
                if img_item.image and img_item.image.url:
                    image_map[img_item.title] = img_item.image.url
        
        insights = []
        if response.web_items:
            for item in response.web_items:
                # 查找匹配的图片
                image_url = ""
                for img_title, img_url in image_map.items():
                    if item.title and any(word in img_title for word in item.title.split()[:3]):
                        image_url = img_url
                        break
                
                # 如果没找到匹配的，使用第一张图片
                if not image_url and img_response.image_items:
                    image_url = img_response.image_items[0].image.url if img_response.image_items[0].image else ""
                
                insights.append({
                    "keyword": item.title[:50] if item.title else "",
                    "description": item.snippet[:100] if item.snippet else "",
                    "source": item.site_name or "大众点评",
                    "url": item.url,
                    "image_url": image_url
                })
        
        return {"success": True, "data": insights}
    
    except Exception as e:
        logger.error(f"获取大众点评洞察失败: {e}")
        return {"success": False, "error": str(e)}


@app.get("/api/insights/xiaohongshu")
async def get_xiaohongshu_insights(keyword: Optional[str] = "家庭深海鱼"):
    """获取小红书家庭深海鱼洞察（包含菜品图片）"""
    try:
        ctx = new_context(method="search.web")
        client = SearchClient(ctx=ctx)
        
        # 1. 搜索网页内容
        response = client.search(
            query=f"{keyword} 菜谱 教程",
            sites="xiaohongshu.com",
            count=10,
            need_summary=True
        )
        
        # 2. 搜索图片
        img_ctx = new_context(method="search.image")
        img_client = SearchClient(ctx=img_ctx)
        img_response = img_client.image_search(
            query=f"{keyword} 菜品 家常菜",
            count=10
        )
        
        # 3. 构建图片URL映射
        image_map = {}
        if img_response.image_items:
            for img_item in img_response.image_items:
                if img_item.image and img_item.image.url:
                    image_map[img_item.title] = img_item.image.url
        
        insights = []
        if response.web_items:
            for item in response.web_items:
                # 查找匹配的图片
                image_url = ""
                for img_title, img_url in image_map.items():
                    if item.title and any(word in img_title for word in item.title.split()[:3]):
                        image_url = img_url
                        break
                
                # 如果没找到匹配的，使用第一张图片
                if not image_url and img_response.image_items:
                    image_url = img_response.image_items[0].image.url if img_response.image_items[0].image else ""
                
                insights.append({
                    "keyword": item.title[:50] if item.title else "",
                    "description": item.snippet[:100] if item.snippet else "",
                    "source": item.site_name or "小红书",
                    "url": item.url,
                    "image_url": image_url
                })
        
        return {"success": True, "data": insights}
    
    except Exception as e:
        logger.error(f"获取小红书洞察失败: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/dish/generate")
async def generate_dish(request: GenerateDishRequest):
    """生成菜品图片和卖点"""
    try:
        dish_info = request.dish_info
        
        # 1. 生成菜品图片
        ctx_img = new_context(method="generate")
        img_client = ImageGenerationClient(ctx=ctx_img)
        
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
                content = llm_response.content.strip()
                if content.startswith("```json"):
                    content = content[7:]
                if content.startswith("```"):
                    content = content[3:]
                if content.endswith("```"):
                    content = content[:-3]
                
                result = json.loads(content.strip())
                selling_points = result.get("selling_points", [])
            except json.JSONDecodeError:
                selling_points = [line.strip() for line in llm_response.content.split("\n") if line.strip()]
        
        return {
            "success": True,
            "data": {
                "dish_name": dish_info.name,
                "image_url": image_url,
                "selling_points": selling_points[:5]
            }
        }
    
    except Exception as e:
        logger.error(f"生成菜品失败: {e}")
        return {"success": False, "error": str(e)}


# ========== Web前端专用API ==========

@app.get("/api/web/insights/{platform}")
async def web_get_insights(platform: str):
    """Web前端专用：获取社媒洞察（简化版）"""
    try:
        # 调用已有的洞察API
        if platform == "dianping":
            result = await get_dianping_insights()
        elif platform == "xiaohongshu":
            result = await get_xiaohongshu_insights()
        else:
            return {"success": False, "error": "不支持的平台"}
        
        # 简化返回格式
        insights = []
        data = result.get("data", [])
        
        # data可能是列表或字典
        if isinstance(data, list):
            items = data
        elif isinstance(data, dict):
            items = data.get("results", [])
        else:
            items = []
        
        for item in items:
            if isinstance(item, dict):
                insights.append({
                    "keyword": item.get("title", "")[:30] or item.get("keyword", ""),
                    "description": item.get("summary", "")[:100] or item.get("description", ""),
                    "image_url": item.get("image_url", ""),
                    "source": item.get("source", ""),
                    "url": item.get("url", "")
                })
        
        return {"success": True, "insights": insights}
    
    except Exception as e:
        logger.error(f"获取Web洞察失败: {e}")
        return {"success": False, "error": str(e)}


@app.post("/api/web/dish/generate")
async def web_generate_dish(request: dict):
    """Web前端专用：生成菜品图片和卖点（简化版）"""
    try:
        # 构造请求
        dish_request = GenerateDishRequest(
            dish_info=DishInfo(
                name=request.get("dish_name", ""),
                main_ingredient=request.get("main_ingredient", "").split()[0] if request.get("main_ingredient") else "",
                main_ingredient_weight=request.get("main_ingredient", "").split()[1] if len(request.get("main_ingredient", "").split()) > 1 else "",
                auxiliary_ingredient=request.get("side_ingredient", "").split()[0] if request.get("side_ingredient") else "",
                auxiliary_ingredient_weight=request.get("side_ingredient", "").split()[1] if len(request.get("side_ingredient", "").split()) > 1 else "",
                cooking_method=request.get("cooking_method", "")
            )
        )
        
        # 调用已有的生成API
        result = await generate_dish(dish_request)
        
        # 简化返回格式
        if result.get("success"):
            data = result.get("data", {})
            return {
                "success": True,
                "image_url": data.get("image_url", ""),
                "selling_points": data.get("selling_points", [])
            }
        else:
            return result
    
    except Exception as e:
        logger.error(f"Web生成菜品失败: {e}")
        return {"success": False, "error": str(e)}


def get_web_html() -> str:
    """返回Web应用HTML"""
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
        
        .container {
            max-width: 1400px;
            margin: 0 auto;
            padding: 30px;
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 30px;
        }
        
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
        
        async function loadInsights(type) {
            currentTab = type;
            
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
        
        function refreshInsights() {
            loadInsights(currentTab);
        }
        
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
                    document.getElementById('resultSection').style.display = 'block';
                    document.getElementById('dishImage').src = data.data.image_url;
                    
                    const pointsList = document.getElementById('sellingPoints');
                    pointsList.innerHTML = data.data.selling_points.map(point => 
                        `<li>${point}</li>`
                    ).join('');
                    
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
        
        window.onload = function() {
            loadInsights('dianping');
        };
    </script>
</body>
</html>
    """


# ========== 原有API端点 ==========

HEADER_X_RUN_ID = "x-run-id"
@app.post("/run")
async def http_run(request: Request) -> Dict[str, Any]:
    global result
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = str(raw_body)
        raise HTTPException(status_code=400,
                            detail=f"Invalid JSON format: {body_text}, traceback: {traceback.format_exc()}, error: {e}")

    ctx = new_context(method="run", headers=request.headers)
    # 优先使用上游指定的 run_id，保证 cancel 能精确匹配
    upstream_run_id = request.headers.get(HEADER_X_RUN_ID)
    if upstream_run_id:
        ctx.run_id = upstream_run_id
    run_id = ctx.run_id
    request_context.set(ctx)

    logger.info(
        f"Received request for /run: "
        f"run_id={run_id}, "
        f"query={dict(request.query_params)}, "
        f"body={body_text}"
    )

    try:
        payload = await request.json()

        # 创建任务并记录 - 这是关键，让我们可以通过run_id取消任务
        task = asyncio.create_task(service.run(payload, ctx))
        service.running_tasks[run_id] = task

        try:
            result = await asyncio.wait_for(task, timeout=float(TIMEOUT_SECONDS))
        except asyncio.TimeoutError:
            logger.error(f"Run execution timeout after {TIMEOUT_SECONDS}s for run_id: {run_id}")
            task.cancel()
            try:
                result = await task
            except asyncio.CancelledError:
                return {
                    "status": "timeout",
                    "run_id": run_id,
                    "message": f"Execution timeout: exceeded {TIMEOUT_SECONDS} seconds"
                }

        if not result:
            result = {}
        if isinstance(result, dict):
            result["run_id"] = run_id
        return result

    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format, {extract_core_stack()}")

    except asyncio.CancelledError:
        logger.info(f"Request cancelled for run_id: {run_id}")
        result = {"status": "cancelled", "run_id": run_id, "message": "Execution was cancelled"}
        return result

    except Exception as e:
        # 使用错误分类器获取错误信息
        error_response = service.error_classifier.get_error_response(e, {"node_name": "http_run", "run_id": run_id})
        logger.error(
            f"Unexpected error in http_run: [{error_response['error_code']}] {error_response['error_message']}, "
            f"traceback: {traceback.format_exc()}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": error_response["error_code"],
                "error_message": error_response["error_message"],
                "stack_trace": extract_core_stack(),
            }
        )
    finally:
        cozeloop.flush()


HEADER_X_WORKFLOW_STREAM_MODE = "x-workflow-stream-mode"


def _register_task(run_id: str, task: asyncio.Task):
    service.running_tasks[run_id] = task


@app.post("/stream_run")
async def http_stream_run(request: Request):
    ctx = new_context(method="stream_run", headers=request.headers)
    # 优先使用上游指定的 run_id，保证 cancel 能精确匹配
    upstream_run_id = request.headers.get(HEADER_X_RUN_ID)
    if upstream_run_id:
        ctx.run_id = upstream_run_id
    workflow_stream_mode = request.headers.get(HEADER_X_WORKFLOW_STREAM_MODE, "").lower()
    workflow_debug = workflow_stream_mode == "debug"
    request_context.set(ctx)
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except Exception as e:
        body_text = str(raw_body)
        raise HTTPException(status_code=400,
                            detail=f"Invalid JSON format: {body_text}, traceback: {extract_core_stack()}, error: {e}")
    run_id = ctx.run_id
    is_agent = graph_helper.is_agent_proj()
    logger.info(
        f"Received request for /stream_run: "
        f"run_id={run_id}, "
        f"is_agent_project={is_agent}, "
        f"query={dict(request.query_params)}, "
        f"body={body_text}"
    )
    try:
        payload = await request.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_stream_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format:{extract_core_stack()}")

    if is_agent:
        stream_generator = agent_stream_handler(
            payload=payload,
            ctx=ctx,
            run_id=run_id,
            stream_sse_func=service.stream_sse,
            sse_event_func=service._sse_event,
            error_classifier=service.error_classifier,
            register_task_func=_register_task,
        )
    else:
        stream_generator = workflow_stream_handler(
            payload=payload,
            ctx=ctx,
            run_id=run_id,
            stream_sse_func=service.stream_sse,
            sse_event_func=service._sse_event,
            error_classifier=service.error_classifier,
            register_task_func=_register_task,
            run_opt=RunOpt(workflow_debug=workflow_debug),
        )

    response = StreamingResponse(stream_generator, media_type="text/event-stream")
    return response

@app.post("/cancel/{run_id}")
async def http_cancel(run_id: str, request: Request):
    """
    取消指定run_id的执行

    使用asyncio.Task.cancel()实现取消,这是Python标准的异步任务取消机制。
    LangGraph会在节点之间的await点检查CancelledError,实现优雅取消。
    """
    ctx = new_context(method="cancel", headers=request.headers)
    request_context.set(ctx)
    logger.info(f"Received cancel request for run_id: {run_id}")
    result = service.cancel_run(run_id, ctx)
    return result


@app.post(path="/node_run/{node_id}")
async def http_node_run(node_id: str, request: Request):
    raw_body = await request.body()
    try:
        body_text = raw_body.decode("utf-8")
    except UnicodeDecodeError:
        body_text = str(raw_body)
        raise HTTPException(status_code=400, detail=f"Invalid JSON format: {body_text}")
    ctx = new_context(method="node_run", headers=request.headers)
    request_context.set(ctx)
    logger.info(
        f"Received request for /node_run/{node_id}: "
        f"query={dict(request.query_params)}, "
        f"body={body_text}",
    )

    try:
        payload = await request.json()
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in http_node_run: {e}, traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=400, detail=f"Invalid JSON format:{extract_core_stack()}")
    try:
        return await service.run_node(node_id, payload, ctx)
    except KeyError:
        raise HTTPException(status_code=404,
                            detail=f"node_id '{node_id}' not found or input miss required fields, traceback: {extract_core_stack()}")
    except Exception as e:
        # 使用错误分类器获取错误信息
        error_response = service.error_classifier.get_error_response(e, {"node_name": node_id})
        logger.error(
            f"Unexpected error in http_node_run: [{error_response['error_code']}] {error_response['error_message']}, "
            f"traceback: {traceback.format_exc()}", exc_info=True
        )
        raise HTTPException(
            status_code=500,
            detail={
                "error_code": error_response["error_code"],
                "error_message": error_response["error_message"],
                "stack_trace": extract_core_stack(),
            }
        )
    finally:
        cozeloop.flush()


@app.post("/v1/chat/completions")
async def openai_chat_completions(request: Request):
    """OpenAI Chat Completions API 兼容接口"""
    ctx = new_context(method="openai_chat", headers=request.headers)
    request_context.set(ctx)

    logger.info(f"Received request for /v1/chat/completions: run_id={ctx.run_id}")

    try:
        payload = await request.json()
        return await openai_handler.handle(payload, ctx)
    except json.JSONDecodeError as e:
        logger.error(f"JSON decode error in openai_chat_completions: {e}")
        raise HTTPException(status_code=400, detail="Invalid JSON format")
    finally:
        cozeloop.flush()


@app.get("/health")
async def health_check():
    try:
        # 这里可以添加更多的健康检查逻辑
        return {
            "status": "ok",
            "message": "Service is running",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=str(e))


@app.get(path="/graph_parameter")
async def http_graph_inout_parameter(request: Request):
    return service.graph_inout_schema()

def parse_args():
    parser = argparse.ArgumentParser(description="Start FastAPI server")
    parser.add_argument("-m", type=str, default="http", help="Run mode, support http,flow,node")
    parser.add_argument("-n", type=str, default="", help="Node ID for single node run")
    parser.add_argument("-p", type=int, default=5000, help="HTTP server port")
    parser.add_argument("-i", type=str, default="", help="Input JSON string for flow/node mode")
    return parser.parse_args()


def parse_input(input_str: str) -> Dict[str, Any]:
    """Parse input string, support both JSON string and plain text"""
    if not input_str:
        return {"text": "你好"}

    # Try to parse as JSON first
    try:
        return json.loads(input_str)
    except json.JSONDecodeError:
        # If not valid JSON, treat as plain text
        return {"text": input_str}

def start_http_server(port):
    workers = 1
    reload = False
    if graph_helper.is_dev_env():
        reload = True

    logger.info(f"Start HTTP Server, Port: {port}, Workers: {workers}")
    uvicorn.run("main:app", host="0.0.0.0", port=port, reload=reload, workers=workers)

if __name__ == "__main__":
    args = parse_args()
    if args.m == "http":
        start_http_server(args.p)
    elif args.m == "flow":
        payload = parse_input(args.i)
        result = asyncio.run(service.run(payload))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.m == "node" and args.n:
        payload = parse_input(args.i)
        result = asyncio.run(service.run_node(args.n, payload))
        print(json.dumps(result, ensure_ascii=False, indent=2))
    elif args.m == "agent":
        agent_ctx = new_context(method="agent")
        for chunk in service.stream(
                {
                    "type": "query",
                    "session_id": "1",
                    "message": "你好",
                    "content": {
                        "query": {
                            "prompt": [
                                {
                                    "type": "text",
                                    "content": {"text": "现在几点了？请调用工具获取当前时间"},
                                }
                            ]
                        }
                    },
                },
                run_config={"configurable": {"session_id": "1"}},
                ctx=agent_ctx,
        ):
            print(chunk)
