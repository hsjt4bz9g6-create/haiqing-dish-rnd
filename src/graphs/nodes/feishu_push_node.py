"""
飞书推送节点
"""
import json
import requests
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from graphs.state import FeishuPushInput, FeishuPushOutput


def get_webhook_url() -> str:
    """获取飞书webhook URL"""
    from coze_workload_identity import Client
    client = Client()
    credential = client.get_integration_credential("integration-feishu-message")
    webhook_url = json.loads(credential)["webhook_url"]
    return webhook_url


def feishu_push_node(
    state: FeishuPushInput, 
    config: RunnableConfig, 
    runtime: Runtime[Context]
) -> FeishuPushOutput:
    """
    title: 飞书消息推送
    desc: 将报告推送到飞书群组
    integrations: 飞书消息
    """
    ctx = runtime.context
    
    try:
        # 获取webhook URL
        webhook_url = get_webhook_url()
        
        # 构造飞书富文本消息
        payload = {
            "msg_type": "post",
            "content": {
                "post": {
                    "zh_cn": {
                        "title": "🦐 海青水产智能体工作流分析报告",
                        "content": [
                            [
                                {
                                    "tag": "text",
                                    "text": state.final_report[:4000]  # 飞书消息长度限制
                                }
                            ]
                        ]
                    }
                }
            }
        }
        
        # 发送请求
        response = requests.post(webhook_url, json=payload, timeout=30)
        result = response.json()
        
        # 检查结果
        if result.get("StatusCode") == 0 or result.get("code") == 0:
            return FeishuPushOutput(
                push_status="成功",
                push_message="报告已成功推送到飞书"
            )
        else:
            return FeishuPushOutput(
                push_status="失败",
                push_message=f"推送失败: {result}"
            )
    
    except Exception as e:
        return FeishuPushOutput(
            push_status="失败",
            push_message=f"推送异常: {str(e)}"
        )
