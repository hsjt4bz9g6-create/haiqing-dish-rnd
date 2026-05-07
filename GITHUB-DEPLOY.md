# 🚀 GitHub + Railway + Vercel 完整部署指南

## 📋 前提条件

✅ GitHub账号（如果没有，请先注册：https://github.com/signup）

---

## 🎯 部署流程概览

```
1. 创建GitHub仓库
2. 推送代码到GitHub
3. 部署后端到Railway
4. 部署前端到Vercel
5. 修改前端API地址
6. 完成！
```

---

## 第一步：创建GitHub仓库（5分钟）

### 1.1 登录GitHub
访问：https://github.com/login

### 1.2 创建新仓库
1. 点击右上角 "+" → "New repository"
2. 填写仓库信息：
   - **Repository name**: `haiqing-dish-rnd`
   - **Description**: 大连海青水产菜品应用研发平台
   - **Public** 或 **Private**（任选）
   - ✅ 勾选 "Add a README file"
3. 点击 "Create repository"

### 1.3 获取仓库地址
创建后，复制仓库地址（例如）：
```
https://github.com/你的用户名/haiqing-dish-rnd.git
```

---

## 第二步：推送代码到GitHub（5分钟）

### 2.1 在本地初始化Git
在项目根目录执行：

```bash
# 初始化Git仓库
git init

# 添加所有文件
git add .

# 提交
git commit -m "feat: 海青菜品应用研发平台"

# 添加远程仓库
git remote add origin https://github.com/你的用户名/haiqing-dish-rnd.git

# 推送到GitHub
git push -u origin main
```

### 2.2 验证推送成功
访问您的GitHub仓库，应该能看到所有文件。

---

## 第三步：部署后端到Railway（5分钟）

### 3.1 登录Railway
访问：https://railway.app
点击 "Login with GitHub"

### 3.2 创建新项目
1. 点击 "New Project"
2. 选择 "Deploy from GitHub repo"
3. 选择您的仓库 `haiqing-dish-rnd`
4. **Root Directory** 设置为：`/railway-backend`
5. 点击 "Deploy"

### 3.3 等待部署完成
- Railway会自动安装依赖并部署
- 通常需要2-3分钟

### 3.4 获取后端地址
部署完成后，点击 "Settings" → "Domains"
- 点击 "Generate Domain"
- 获得地址：`https://xxx.up.railway.app`
- **复制这个地址**，后面要用！

### 3.5 测试后端
访问：`https://xxx.up.railway.app/`
应该看到：`{"message": "海青菜品研发API运行中"}`

---

## 第四步：部署前端到Vercel（5分钟）

### 4.1 登录Vercel
访问：https://vercel.com
点击 "Continue with GitHub"

### 4.2 导入项目
1. 点击 "New Project"
2. 选择您的仓库 `haiqing-dish-rnd`
3. **Root Directory** 设置为：`/vercel-frontend`
4. Framework Preset: "Other"
5. 点击 "Deploy"

### 4.3 等待部署完成
- Vercel会自动部署静态文件
- 通常需要1-2分钟

### 4.4 获取前端地址
部署完成后，Vercel会自动分配地址：
- 例如：`https://haiqing-dish-rnd.vercel.app`

---

## 第五步：修改前端API地址（2分钟）

### 5.1 在GitHub上修改文件
1. 访问您的GitHub仓库
2. 找到文件：`vercel-frontend/index.html`
3. 点击编辑（铅笔图标）
4. 搜索 `API_BASE_URL`
5. 修改为您的Railway后端地址：

```javascript
const API_BASE_URL = 'https://xxx.up.railway.app';  // 改成您的后端地址
```

6. 点击 "Commit changes"

### 5.2 同样修改product.html
重复上述步骤，修改 `vercel-frontend/product.html`

### 5.3 Vercel自动部署
Vercel会自动检测到更新并重新部署（约1分钟）

---

## 第六步：完成！🎉

### 访问您的应用
- **前端主页**：https://haiqing-dish-rnd.vercel.app
- **产品研发页**：https://haiqing-dish-rnd.vercel.app/product.html
- **后端API**：https://xxx.up.railway.app

### 所有研发人员都可以访问！
将前端地址分享给团队成员，所有人都能使用！

---

## 📊 费用说明

| 服务 | 费用 | 说明 |
|------|------|------|
| GitHub | ✅ 免费 | 公开仓库免费 |
| Railway | ✅ 免费 | 每月$5额度，足够使用 |
| Vercel | ✅ 免费 | 个人项目免费 |
| **总计** | ✅ **完全免费** | 无需任何费用 |

---

## 🔧 常见问题

### Q1: Railway部署失败？
**解决**：
- 检查 `railway-backend/requirements.txt` 是否完整
- 查看Railway日志，找到具体错误信息

### Q2: 前端无法连接后端？
**解决**：
- 检查 `API_BASE_URL` 是否正确
- 确保后端已成功部署

### Q3: Vercel部署失败？
**解决**：
- 确保Root Directory设置为 `/vercel-frontend`
- 检查HTML文件语法

### Q4: 想要自定义域名？
**解决**：
- Vercel支持免费绑定自定义域名
- 在Vercel项目设置中添加域名

---

## 🎯 部署时间预估

| 步骤 | 时间 |
|------|------|
| 创建GitHub仓库 | 5分钟 |
| 推送代码 | 5分钟 |
| 部署Railway | 5分钟 |
| 部署Vercel | 5分钟 |
| 修改API地址 | 2分钟 |
| **总计** | **约22分钟** |

---

## ✅ 部署检查清单

- [ ] GitHub仓库已创建
- [ ] 代码已推送到GitHub
- [ ] Railway后端已部署
- [ ] 后端API可以访问
- [ ] Vercel前端已部署
- [ ] 前端API地址已修改
- [ ] 网站可以正常使用

---

## 🆘 需要帮助？

如果遇到问题：
1. 检查Railway和Vercel的部署日志
2. 确认所有步骤是否正确执行
3. 重新阅读相关步骤

---

**祝您部署顺利！** 🚀
