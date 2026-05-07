# 海青菜品研发API

## 部署说明
这是一个FastAPI后端，用于提供菜品研发和社媒洞察API。

## 本地运行
```bash
pip install -r requirements.txt
python main.py
```

## API端点
- GET / - 健康检查
- GET /api/web/insights/{platform} - 获取社媒洞察
- POST /api/web/dish/generate - 生成菜品图片和卖点
