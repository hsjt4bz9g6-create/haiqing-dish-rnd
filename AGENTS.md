# 项目概述
- **名称**: 海青水产智能体工作流
- **功能**: 基于AI的深海鱼产品研发、市场分析和内容创作智能体

## 节点清单

| 节点名 | 文件位置 | 类型 | 功能描述 | 分支逻辑 | 配置文件 |
|-------|---------|------|---------|---------|---------|
| market_analysis | `nodes/market_analysis_node.py` | agent | 市场趋势分析、竞品调研 | - | `config/market_analysis_cfg.json` |
| product_rnd | `nodes/product_rnd_node.py` | agent | 产品研发建议、工艺优化 | - | `config/product_rnd_cfg.json` |
| dish_application | `nodes/dish_application_node.py` | agent | 菜品应用方案、烹饪建议 | - | `config/dish_application_cfg.json` |
| content_creation | `nodes/content_creation_node.py` | agent | 社媒内容创作、文案撰写 | - | `config/content_creation_cfg.json` |
| report_generation | `nodes/report_generation_node.py` | agent | 报告整合生成 | - | `config/report_generation_cfg.json` |
| feishu_push | `nodes/feishu_push_node.py` | task | 飞书消息推送 | - | - |

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
    飞书推送 (feishu_push)
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
7. **飞书推送**: 将报告推送到飞书群组

## 技能使用
- 节点 `market_analysis` 使用技能：大语言模型、网络搜索
- 节点 `product_rnd` 使用技能：大语言模型（带thinking模式）
- 节点 `dish_application` 使用技能：大语言模型
- 节点 `content_creation` 使用技能：大语言模型
- 节点 `report_generation` 使用技能：大语言模型
- 节点 `feishu_push` 使用技能：飞书消息

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
from graphs.graph import main_graph

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

### 配置调整
- 修改 `config/` 目录下的配置文件可调整大模型参数和提示词
- 修改 `src/graphs/state.py` 可调整数据结构
- 修改各节点文件可调整具体业务逻辑
