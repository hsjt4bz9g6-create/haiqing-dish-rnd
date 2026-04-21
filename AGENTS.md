# 项目概述
- **名称**: 海青水产智能体工作流
- **功能**: 基于AI的深海鱼产品研发、市场分析和内容创作智能体，支持飞书多维表格数据录入

## 节点清单

| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| market_analysis | `nodes/market_analysis_node.py` | agent | 市场趋势分析、竞品调研 | - | `config/market_analysis_cfg.json` |
| product_rnd | `nodes/product_rnd_node.py` | agent | 产品研发建议、工艺优化 | - | `config/product_rnd_cfg.json` |
| dish_application | `nodes/dish_application_node.py` | agent | 菜品应用方案、烹饪建议 | - | `config/dish_application_cfg.json` |
| content_creation | `nodes/content_creation_node.py` | agent | 社媒内容创作、文案撰写 | - | `config/content_creation_cfg.json` |
| report_generation | `nodes/report_generation_node.py` | agent | 报告整合生成 | - | `config/report_generation_cfg.json` |
| feishu_bitable_input | `nodes/feishu_bitable_input_node.py` | task | 飞书多维表格录入 | - | - |
| social_media_crawl | `nodes/social_media_crawl_node.py` | task | 社媒爆款内容抓取 | - | - |
| weekly_report | `nodes/weekly_report_node.py` | task | 研发任务周报生成 | - | - |

**类型说明**: task(task节点) / agent(大模型) / condition(条件分支) / looparray(列表循环) / loopcond(条件循环)

## 工作流设计

### 工作流程图
```
市场分析 (market_analysis)
    ↓
    ├→ 产品研发 (product_rnd)
    └→ 菜品应用 (dish_application)
         ↓
    内容创作 (content_creation)
         ↓
    报告生成 (report_generation)
         ↓
    飞书多维表格录入 (feishu_bitable_input)
         ↓
       END
```

### 数据流转
1. **输入**: 任务类型、产品信息（名称、类型、加工方式、目标市场）
2. **市场分析**: 搜索市场趋势、社媒热点、竞品信息 → 分析结果
3. **产品研发**: 基于市场趋势提供研发建议
4. **菜品应用**: 设计烹饪方案和客户定制化方案
5. **内容创作**: 创作抖音、小红书、视频号内容
6. **报告生成**: 整合所有分析结果生成最终报告
7. **飞书多维表格录入**: 将数据结构化存入飞书多维表格

## 飞书多维表格配置

### 使用前配置

#### 1. 创建飞书多维表格
在飞书中创建一个多维表格，表格名称建议：`🦐 海青水产产品分析数据库`

#### 2. 创建数据表（推荐5张表）

**产品基础信息表**：
- 产品名称（文本）
- 产品类型（文本）
- 加工方式（文本）
- 目标市场（文本）
- 创建时间（日期）
- 产品ID（文本）

**市场分析表**：
- 产品ID（文本）
- 市场趋势（文本）
- 竞品分析（文本）
- 市场机会（文本）
- 分析时间（日期）

**产品研发表**：
- 产品ID（文本）
- 食材特性分析（文本）
- 工艺优化建议（文本）
- 风味搭配方案（文本）
- 包装设计建议（文本）
- 创新产品方向（文本）

**菜品应用表**：
- 产品ID（文本）
- 烹饪特性（文本）
- 餐饮应用方案（文本）
- 零售应用方案（文本）
- 烹饪建议（文本）

**社媒内容表**：
- 产品ID（文本）
- 抖音内容（文本）
- 小红书内容（文本）
- 视频号内容（文本）
- 视觉化建议（文本）

#### 3. 配置环境变量
将多维表格的 `app_token` 配置到环境变量：

```bash
export FEISHU_APP_TOKEN="your_app_token_here"
```

或在工作流调用时传入：
```python
os.environ["FEISHU_APP_TOKEN"] = "your_app_token_here"
```

**如何获取 app_token**：
- 打开飞书多维表格
- 查看URL：`https://feishu.cn/base/XXXXX`
- `XXXXX` 部分即为 `app_token`

## 技能使用
- 节点 `market_analysis` 使用技能：大语言模型、网络搜索
- 节点 `product_rnd` 使用技能：大语言模型（带thinking模式）
- 节点 `dish_application` 使用技能：大语言模型
- 节点 `content_creation` 使用技能：大语言模型
- 节点 `report_generation` 使用技能：大语言模型
- 节点 `feishu_bitable_input` 使用技能：飞书多维表格
- 节点 `social_media_crawl` 使用技能：飞书多维表格、飞书消息
- 节点 `weekly_report` 使用技能：飞书多维表格、飞书消息、文档生成

## 研发任务周报功能

### 功能说明
每周自动生成研发任务周报PDF，汇报给老板，内容包括：
- 本周完成任务总结
- 进行中任务进展
- 下周工作计划
- 工作要点与建议

### 配置信息
- **飞书多维表格**: `XqpUbfoHIa4LjcsgS3Ccr1uJnjg`
- **任务表ID**: `tblXZEsOcRXTT6Hp`
- **定时任务**: 每周日上午12点自动生成

### 手动触发方式
```python
from graphs.nodes.weekly_report_node import weekly_report_node
from graphs.state import WeeklyReportInput
from langchain_core.runnables import RunnableConfig
from langgraph.runtime import Runtime
from coze_coding_utils.runtime_ctx.context import Context

# 准备输入
input_data = WeeklyReportInput(
    app_token="XqpUbfoHIa4LjcsgS3Ccr1uJnjg",
    table_id="tblXZEsOcRXTT6Hp"
)

# 执行节点
result = weekly_report_node(input_data, RunnableConfig(), Runtime[Context]())
print(f"PDF链接: {result.pdf_url}")
```

### 输出格式
- **格式**: PDF文档
- **内容**: Markdown转PDF，包含图表和表格
- **推送**: 自动推送到飞书群

## 业务场景
本工作流专为大连海青水产设计，覆盖三个核心业务方向：

1. **产品研发**: 深海鱼预包装RTC产品（鳕鱼、三文鱼、虾等）
   - 深加工工艺：调理腌制、裹粉、裹面包糠
   - 产品形态：生冻、预炸
   - 目标市场：餐饮、零售

2. **菜品应用研发**: 深海鱼烹饪应用
   - 销售支持
   - 客户演示推广
   - 烹饪方式建议

3. **社媒传播**: 数字化可视化资产
   - 抖音、视频号、小红书内容发布
   - 产品介绍
   - 研发工作展示

## 使用方法

### 测试运行
```python
import os
from graphs.graph import main_graph

# 配置飞书多维表格app_token
os.environ["FEISHU_APP_TOKEN"] = "your_app_token_here"

# 准备输入
input_data = {
    "task_type": "产品研发",
    "product_name": "香酥鳕鱼块",
    "product_type": "鳕鱼",
    "processing_method": "裹粉预炸",
    "target_market": "餐饮"
}

# 执行工作流
result = main_graph.invoke(input_data)
print(result["final_report"])
```

### 查看结果
执行完成后，在飞书多维表格中可以查看：
- 产品基础信息
- 市场分析结果
- 产品研发建议
- 菜品应用方案
- 社媒内容草稿

所有数据按产品ID关联，可随时查看和编辑。

### 配置调整
- 修改 `config/` 目录下的配置文件可调整大模型参数和提示词
- 修改 `src/graphs/state.py` 可调整数据结构
- 修改各节点文件可调整具体业务逻辑
- 修改 `src/tools/feishu_bitable_tool.py` 可调整多维表格操作逻辑
