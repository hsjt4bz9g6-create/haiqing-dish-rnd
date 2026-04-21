import os
import json
import time
from datetime import datetime, timedelta
from typing import List, Dict, Any
import requests
from jinja2 import Template
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context
from coze_coding_dev_sdk import DocumentGenerationClient, PDFConfig
from coze_workload_identity import Client

from graphs.state import WeeklyReportInput, WeeklyReportOutput


def extract_text(field_value: Any) -> str:
    """从飞书字段值中提取文本"""
    if not field_value:
        return ""
    if isinstance(field_value, str):
        return field_value
    if isinstance(field_value, list):
        texts = []
        for item in field_value:
            if isinstance(item, dict) and "text" in item:
                texts.append(item["text"])
        return " | ".join(texts) if texts else str(field_value)
    return str(field_value)


def timestamp_to_date(ts: Any) -> str:
    """时间戳转日期"""
    if not ts:
        return ""
    try:
        if isinstance(ts, (int, float)):
            return datetime.fromtimestamp(ts/1000).strftime('%Y-%m-%d')
        return str(ts)
    except:
        return str(ts)


def get_access_token() -> str:
    """获取飞书访问令牌"""
    client = Client()
    access_token = client.get_integration_credential("integration-feishu-base")
    return access_token


def get_webhook_url() -> str:
    """获取飞书机器人webhook URL"""
    client = Client()
    wechat_bot_credential = client.get_integration_credential("integration-feishu-message")
    webhook_url = json.loads(wechat_bot_credential)["webhook_url"]
    return webhook_url


def weekly_report_node(
    state: WeeklyReportInput,
    config: RunnableConfig,
    runtime: Runtime[Context]
) -> WeeklyReportOutput:
    """
    title: 研发任务周报生成
    desc: 自动生成研发任务周报PDF，包含本周完成情况、进行中任务和下周计划，并推送到飞书群
    integrations: 飞书多维表格、飞书消息、文档生成
    """
    ctx = runtime.context
    
    # 配置参数
    app_token = state.app_token
    table_id = state.table_id
    base_url = "https://open.larkoffice.com/open-apis"
    access_token = get_access_token()
    
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json; charset=utf-8",
    }
    
    # 计算本周和下周的时间范围
    today = datetime.now()
    week_start = today - timedelta(days=today.weekday() + 1)
    week_end = week_start + timedelta(days=6)
    next_week_start = week_start + timedelta(days=7)
    next_week_end = next_week_start + timedelta(days=6)
    
    # 查询所有任务
    search_url = f"{base_url}/bitable/v1/apps/{app_token}/tables/{table_id}/records/search"
    search_body = {
        "automatic_fields": False,
        "view_id": "",
        "field_names": ["任务名称", "出口/内销", "分类", "备注", "开始时间", "状态", "结束时间"],
        "page_size": 500
    }
    
    resp = requests.post(search_url, headers=headers, json=search_body, timeout=30)
    result = resp.json()
    
    if result.get("code") != 0:
        return WeeklyReportOutput(
            success=False,
            message=f"查询任务失败: {result}",
            pdf_url=""
        )
    
    records = result.get("data", {}).get("items", [])
    
    # 分类任务
    completed_tasks: List[Dict[str, Any]] = []
    in_progress_tasks: List[Dict[str, Any]] = []
    next_week_tasks: List[Dict[str, Any]] = []
    
    week_start_ts = int(week_start.timestamp() * 1000)
    week_end_ts = int(week_end.timestamp() * 1000) + 86400000
    next_week_start_ts = int(next_week_start.timestamp() * 1000)
    next_week_end_ts = int(next_week_end.timestamp() * 1000) + 86400000
    
    for record in records:
        fields = record.get("fields", {})
        task_name = extract_text(fields.get("任务名称"))
        category = extract_text(fields.get("分类"))
        market = extract_text(fields.get("出口/内销"))
        status = extract_text(fields.get("状态"))
        remark = extract_text(fields.get("备注"))
        start_time = fields.get("开始时间")
        end_time = fields.get("结束时间")
        
        task_info = {
            "name": task_name,
            "category": category,
            "market": market,
            "status": status,
            "remark": remark,
            "start_date": timestamp_to_date(start_time),
            "end_date": timestamp_to_date(end_time)
        }
        
        # 本周完成的任务
        if status == "完成" and end_time:
            if week_start_ts <= end_time <= week_end_ts:
                completed_tasks.append(task_info)
        
        # 进行中的任务
        if status in ["进行中", "待开始"]:
            in_progress_tasks.append(task_info)
        
        # 下周计划任务
        if start_time and next_week_start_ts <= start_time <= next_week_end_ts:
            next_week_tasks.append(task_info)
    
    # 生成Markdown周报
    report_date = today.strftime('%Y年%m月%d日')
    week_num = today.isocalendar()[1]
    
    markdown_content = f"""# 研发任务周报

**报告日期：** {report_date}  
**报告周期：** 第{week_num}周（{week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}）

---

## 一、本周工作总结

### 1.1 本周完成任务（共{len(completed_tasks)}项）

"""
    
    if completed_tasks:
        by_category: Dict[str, List[Dict[str, Any]]] = {}
        for task in completed_tasks:
            cat = task["category"] or "其他"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(task)
        
        for category, tasks in sorted(by_category.items()):
            markdown_content += f"#### {category}\n\n"
            for i, task in enumerate(tasks, 1):
                markdown_content += f"{i}. **{task['name']}**\n"
                if task['remark']:
                    markdown_content += f"   - 备注：{task['remark']}\n"
                markdown_content += f"   - 市场：{task['market']} | 完成日期：{task['end_date']}\n\n"
    else:
        markdown_content += "*本周暂无完成任务*\n\n"
    
    markdown_content += f"""### 1.2 进行中任务（共{len(in_progress_tasks)}项）

"""
    
    if in_progress_tasks:
        by_category = {}
        for task in in_progress_tasks:
            cat = task["category"] or "其他"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(task)
        
        for category, tasks in sorted(by_category.items()):
            markdown_content += f"#### {category}\n\n"
            for i, task in enumerate(tasks, 1):
                status_icon = "🟢" if task["status"] == "进行中" else "🟡"
                markdown_content += f"{i}. {status_icon} **{task['name']}**\n"
                markdown_content += f"   - 状态：{task['status']} | 市场：{task['market']}\n"
                if task['remark']:
                    markdown_content += f"   - 备注：{task['remark']}\n"
                markdown_content += "\n"
    else:
        markdown_content += "*暂无进行中任务*\n\n"
    
    markdown_content += f"""---

## 二、下周工作计划

### 2.1 下周计划任务（共{len(next_week_tasks)}项）

**计划周期：** {next_week_start.strftime('%Y-%m-%d')} ~ {next_week_end.strftime('%Y-%m-%d')}

"""
    
    if next_week_tasks:
        by_category = {}
        for task in next_week_tasks:
            cat = task["category"] or "其他"
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(task)
        
        for category, tasks in sorted(by_category.items()):
            markdown_content += f"#### {category}\n\n"
            for i, task in enumerate(tasks, 1):
                markdown_content += f"{i}. **{task['name']}**\n"
                markdown_content += f"   - 计划开始：{task['start_date']} | 市场：{task['market']}\n"
                if task['remark']:
                    markdown_content += f"   - 备注：{task['remark']}\n"
                markdown_content += "\n"
    else:
        markdown_content += "*下周暂无计划任务*\n\n"
    
    # 统计数据
    export_count = sum(1 for t in completed_tasks if t["market"] == "出口")
    domestic_count = sum(1 for t in completed_tasks if t["market"] == "内销")
    
    markdown_content += f"""---

## 三、工作要点与建议

### 3.1 本周重点工作回顾

- 本周共完成 **{len(completed_tasks)}** 项研发任务
- 其中出口业务 **{export_count}** 项，内销业务 **{domestic_count}** 项
- 进行中任务 **{len(in_progress_tasks)}** 项，需持续跟进

### 3.2 下周重点工作提示

"""
    
    if next_week_tasks:
        markdown_content += f"- 下周计划启动 **{len(next_week_tasks)}** 项新任务\n"
        markdown_content += "- 建议提前做好资源准备和人员安排\n"
    else:
        markdown_content += "- 建议从进行中任务中筛选优先级高的项目推进\n"
    
    markdown_content += f"""
---

**报告生成时间：** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}  
**报告生成方式：** AI自动生成

---
*本报告由智能助手自动生成，如有疑问请联系研发部门负责人。*
"""
    
    # 生成PDF
    pdf_config = PDFConfig(page_size="A4", top_margin=72, bottom_margin=72, left_margin=72, right_margin=72)
    doc_client = DocumentGenerationClient(pdf_config=pdf_config)
    
    pdf_url = doc_client.create_pdf_from_markdown(markdown_content, "weekly_report")
    
    # 推送到飞书群
    webhook_url = get_webhook_url()
    
    payload = {
        "msg_type": "interactive",
        "card": {
            "header": {
                "title": {
                    "tag": "plain_text",
                    "content": f"📊 研发任务周报 - 第{week_num}周"
                },
                "template": "blue"
            },
            "elements": [
                {
                    "tag": "markdown",
                    "content": f"""**报告周期：** {week_start.strftime('%Y-%m-%d')} ~ {week_end.strftime('%Y-%m-%d')}

**本周完成：** {len(completed_tasks)} 项任务
**进行中：** {len(in_progress_tasks)} 项任务  
**下周计划：** {len(next_week_tasks)} 项任务

请点击下方按钮下载完整周报PDF文件。"""
                },
                {
                    "tag": "action",
                    "actions": [
                        {
                            "tag": "button",
                            "text": {
                                "content": "📥 下载周报PDF",
                                "tag": "plain_text"
                            },
                            "type": "primary",
                            "url": pdf_url
                        },
                        {
                            "tag": "button",
                            "text": {
                                "content": "📊 查看任务表格",
                                "tag": "plain_text"
                            },
                            "type": "default",
                            "url": f"https://feishu.cn/base/{app_token}?table={table_id}"
                        }
                    ]
                },
                {
                    "tag": "note",
                    "elements": [
                        {
                            "tag": "plain_text",
                            "content": f"📅 生成时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 由AI自动生成"
                        }
                    ]
                }
            ]
        }
    }
    
    response = requests.post(webhook_url, json=payload, timeout=30)
    push_result = response.json()
    
    push_success = push_result.get("StatusCode") == 0 or push_result.get("code") == 0
    
    return WeeklyReportOutput(
        success=True,
        message=f"周报生成成功！本周完成{len(completed_tasks)}项，进行中{len(in_progress_tasks)}项，下周计划{len(next_week_tasks)}项",
        pdf_url=pdf_url,
        completed_count=len(completed_tasks),
        in_progress_count=len(in_progress_tasks),
        next_week_count=len(next_week_tasks),
        push_success=push_success
    )
