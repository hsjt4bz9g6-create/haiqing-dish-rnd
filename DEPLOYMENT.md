# 🚀 Vercel + Railway 免费部署指南

## 📋 部署架构

```
用户浏览器
    ↓
前端（Vercel） - 静态HTML/CSS/JS
    ↓
后端API（Railway） - FastAPI Python
    ↓
AI服务（网络搜索、图片生成、LLM）
```

---

## 💰 费用说明

- ✅ **Vercel**: 完全免费（个人项目）
- ✅ **Railway**: 免费额度（每月$5额度，足够使用）
- ✅ **总计**: 完全免费

---

## 🚀 部署步骤

### 步骤1：部署后端到Railway（10分钟）

#### 1.1 注册Railway账号
- 访问：https://railway.app
- 使用GitHub账号登录（推荐）

#### 1.2 创建新项目
```bash
# 1. 点击 "New Project"
# 2. 选择 "Deploy from GitHub repo"
# 3. 选择你的仓库
```

#### 1.3 配置环境变量
在Railway项目设置中添加：
```
COZE_API_KEY=your_coze_api_key
```

#### 1.4 部署
```bash
# Railway会自动检测Python项目并部署
# 部署成功后会获得一个地址：
# https://your-project.up.railway.app
```

#### 1.5 测试后端
```bash
# 访问：https://your-project.up.railway.app
# 应该看到：{"message": "海青菜品研发API运行中"}
```

---

### 步骤2：部署前端到Vercel（5分钟）

#### 2.1 注册Vercel账号
- 访问：https://vercel.com
- 使用GitHub账号登录（推荐）

#### 2.2 导入项目
```bash
# 1. 点击 "New Project"
# 2. 选择 "Import Git Repository"
# 3. 选择你的仓库
```

#### 2.3 配置项目
```
Framework Preset: Other
Root Directory: vercel-frontend
Build Command: 留空
Output Directory: 留空
```

#### 2.4 修改API地址
在部署前，需要修改 `vercel-frontend/index.html`：
```javascript
// 找到这一行：
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : 'YOUR_RAILWAY_BACKEND_URL';

// 替换为：
const API_BASE_URL = window.location.hostname === 'localhost' 
    ? 'http://localhost:5000' 
    : 'https://your-project.up.railway.app';  // 你的Railway地址
```

#### 2.5 部署
```bash
# 点击 "Deploy"
# 等待1-2分钟
# 部署成功后会获得一个地址：
# https://your-project.vercel.app
```

---

## ✅ 部署完成！

### 访问地址
- **前端**: https://your-project.vercel.app
- **后端API**: https://your-project.up.railway.app

### 测试功能
1. 打开前端地址
2. 点击"刷新数据"测试社媒洞察
3. 填写菜品信息测试AI生成

---

## 🔧 本地开发

### 后端
```bash
cd railway-backend
pip install -r requirements.txt
python main.py
# 访问：http://localhost:8000
```

### 前端
```bash
cd vercel-frontend
# 用浏览器打开 index.html
# 或使用本地服务器：
python -m http.server 8080
# 访问：http://localhost:8080
```

---

## 📊 性能优化

### Vercel优化
- ✅ 自动CDN加速
- ✅ 自动HTTPS
- ✅ 全球边缘节点

### Railway优化
- ✅ 自动扩容
- ✅ 健康检查
- ✅ 日志监控

---

## 🛠️ 常见问题

### Q1: Railway部署失败？
**A**: 检查requirements.txt是否正确，确保所有依赖都已列出。

### Q2: 前端无法调用后端API？
**A**: 
1. 检查API_BASE_URL是否正确
2. 检查后端是否正常运行
3. 检查CORS配置

### Q3: AI生成超时？
**A**: Railway免费版有响应时间限制，如果超时可以：
- 优化代码，减少等待时间
- 升级Railway付费版

---

## 🎯 备选方案

如果Railway额度不够，可以考虑：

### 方案A: Render（免费）
- 完全免费
- 有休眠机制（首次访问需要等待）
- 网址：https://render.com

### 方案B: PythonAnywhere（免费）
- 完全免费
- 适合Python项目
- 网址：https://www.pythonanywhere.com

### 方案C: Fly.io（免费额度）
- 免费额度
- 更灵活
- 网址：https://fly.io

---

## 📞 技术支持

如有问题，可以：
1. 查看Railway日志
2. 查看Vercel部署日志
3. 检查API响应

---

## 🎉 完成！

恭喜！您已成功部署菜品应用研发工作台！

所有研发人员都可以通过Vercel地址访问使用。
