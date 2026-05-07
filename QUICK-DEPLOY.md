# 🚀 海青菜品研发平台 - 快速部署指南

## ⚠️ 问题说明
您在沙箱外部无法访问 `localhost:5000`，需要部署到公网才能让所有研发人员访问。

---

## 🌟 方案1：Cloudflare Tunnel（最快，5分钟）

### 优势
- ✅ 完全免费
- ✅ 无需注册
- ✅ 立即获得公网地址
- ✅ 自动HTTPS

### 步骤

#### 在沙箱内执行：
```bash
# 1. 下载cloudflared
curl -L https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64 -o cloudflared
chmod +x cloudflared

# 2. 启动隧道
./cloudflared tunnel --url http://localhost:5000

# 3. 获得公网地址
# 示例输出：
# Your quick Tunnel has been created! Visit it at:
# https://philippines-above-english-traffic.trycloudflare.com
```

#### 访问地址：
```
https://xxxx-xxxx-xxxx.trycloudflare.com
```

**所有研发人员都可以通过这个地址访问！**

---

## 🌟 方案2：Railway + Vercel（推荐，15分钟）

### 优势
- ✅ 完全免费
- ✅ 永久地址
- ✅ 自动部署
- ✅ 更稳定

### 步骤

#### 步骤1：部署后端到Railway

1. **访问** https://railway.app
2. **登录** 使用GitHub账号
3. **创建项目** 点击 "New Project"
4. **选择** "Deploy from GitHub repo"
5. **选择目录** `railway-backend`
6. **等待部署** 约2分钟
7. **获得地址** `https://your-app.up.railway.app`

#### 步骤2：部署前端到Vercel

1. **访问** https://vercel.com
2. **登录** 使用GitHub账号
3. **导入项目** 点击 "New Project"
4. **选择目录** `vercel-frontend`
5. **点击部署** 约1分钟
6. **获得地址** `https://your-app.vercel.app`

#### 步骤3：修改API地址

在 `vercel-frontend/index.html` 中修改：
```javascript
// 找到这一行（约第340行）
const API_BASE_URL = 'http://localhost:5000';

// 改为
const API_BASE_URL = 'https://your-app.up.railway.app';
```

---

## 🌟 方案3：ngrok（需要注册）

### 步骤

1. **注册** https://ngrok.com
2. **获取token** 在Dashboard获取authtoken
3. **配置**
   ```bash
   ngrok config add-authtoken <your-token>
   ```
4. **启动**
   ```bash
   ngrok http 5000
   ```
5. **获得地址** `https://xxxx.ngrok.io`

---

## 📊 方案对比

| 方案 | 时间 | 稳定性 | 是否需要注册 | 推荐度 |
|------|------|--------|-------------|--------|
| **Cloudflare Tunnel** | 5分钟 | ⭐⭐⭐⭐ | ❌ 不需要 | ⭐⭐⭐⭐⭐ |
| **Railway + Vercel** | 15分钟 | ⭐⭐⭐⭐⭐ | ✅ 需要 | ⭐⭐⭐⭐⭐ |
| **ngrok** | 10分钟 | ⭐⭐⭐⭐ | ✅ 需要 | ⭐⭐⭐⭐ |

---

## ✅ 我的推荐

### 如果您希望立即访问：
👉 **使用方案1（Cloudflare Tunnel）**，5分钟内获得公网地址

### 如果您希望长期使用：
👉 **使用方案2（Railway + Vercel）**，完全免费且永久可用

---

## 📝 详细部署文档

完整的部署步骤请查看：`DEPLOYMENT.md`

---

## 💡 需要帮助？

如果您需要我帮您部署，请告诉我：
1. 您选择哪个方案？
2. 您有GitHub账号吗？（方案2需要）

我会为您提供详细的指导！
