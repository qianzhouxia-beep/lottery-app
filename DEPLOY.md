# 🚀 Hermes v5 - 完整部署指南

## 目录
1. [准备工作](#准备工作)
2. [GitHub 仓库设置](#github-仓库设置)
3. [服务器部署（Linux VPS）](#服务器部署linux-vps)
4. [服务器部署（Windows Server）](#服务器部署windows-server)
5. [进阶：GitHub Actions 自动部署](#进阶github-actions-自动部署)
6. [日常运维](#日常运维)

---

## 准备工作

### 你能访问到的东西
- ✅ 本地代码：`D:\AI\lottery-app\`
- ✅ DeepSeek API Key：`sk-2e719532e4324760a47e887b6182993c`
- 需要：
  - 一个 GitHub 账号（免费）
  - 一台 VPS / 云服务器（或有公网 IP 的电脑）

---

## GitHub 仓库设置

> 把代码放到 GitHub，方便版本管理、云端备份、自动部署。

### 第一步：创建 GitHub 仓库

1. 打开 https://github.com/new
2. **Repository name**: `lottery-app`（或你喜欢的名字）
3. 选 **Private**（私密仓库，API密钥在代码里）
4. 不勾选任何初始化选项（Add README / .gitignore / license 都不要勾）
5. 点击 **Create repository**

### 第二步：创建 `.gitignore`

> 把数据文件、缓存、密钥排除在外，不上传到 GitHub。

```bash
cd D:\AI\lottery-app
```

创建 `.gitignore`：

```
__pycache__/
*.pyc
venv/
data/*.json
!data/.gitkeep
server.log
server.err
best_params_dlt.json
best_params_ssq.json
dlt_adaptive_params.json
*.egg-info/
```

> ⚠️ 注意：`config.json` **不要**加进 `.gitignore`——它包含 API Key。更好做法是另存一个 `config.example.json`。

创建 `config.example.json`（不含真实密钥的模板）：

```json
{
  "api_key": "sk-your-api-key-here",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "temperature": 0.3
}
```

> 把真实的 `config.json` 也加到 `.gitignore` 里，确保密钥不上传。

### 第三步：推送本地代码到 GitHub

在本地终端执行（Windows PowerShell）：

```powershell
cd D:\AI\lottery-app

# 初始化 Git
git init

# 添加 .gitignore
# （手动创建上面的 .gitignore 和 config.example.json）

# 暂存所有文件
git add .
git status   # 检查一下是不是想要的（没有 config.json 和 data/*.json）
git reset -- config.json   # 如果 git status 里还有 config.json，手动移除

# 首次提交
git commit -m "feat: Hermes v5 大乐透预测系统 - 自进化AI引擎"

# 关联远程仓库（替换成你的仓库地址）
git remote add origin https://github.com/你的用户名/lottery-app.git

# 推送
git push -u origin main
```

> **Windows 提示**：如果 `git push` 一直转圈，试 `git config --global http.postBuffer 524288000`

---

## 服务器部署（Linux VPS）

> 推荐系统：Ubuntu 22.04 / Debian 12 / CentOS 7+
> 最低配置：1核 1GB 内存（XGBoost 训练时需要约 500MB 额外内存）

### 1️⃣ 连接服务器

```bash
ssh root@你的服务器IP
```

### 2️⃣ 安装 Python 3.11+

```bash
# Ubuntu / Debian
apt update
apt install -y python3 python3-pip python3-venv git

# 可选：安装最新 Python
apt install -y software-properties-common
add-apt-repository ppa:deadsnakes/ppa -y
apt install -y python3.11 python3.11-venv python3.11-dev
```

### 3️⃣ 克隆代码

```bash
cd /opt
git clone https://github.com/你的用户名/lottery-app.git
cd lottery-app
```

### 4️⃣ 创建 config.json

> **千万注意**：不要在服务器上使用 `git clone` 下来的 `config.json`——因为你在 `.gitignore` 里排除了它。需要在服务器上手动创建。

```bash
nano config.json
```

粘贴以下内容（填入真实密钥）：

```json
{
  "api_key": "sk-2e719532e4324760a47e887b6182993c",
  "base_url": "https://api.deepseek.com/v1",
  "model": "deepseek-chat",
  "temperature": 0.3
}
```

### 5️⃣ 创建虚拟环境并安装依赖

```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt
```

### 6️⃣ 首次测试启动

```bash
python api_server.py
```

看到类似输出即为成功：
```
[AutoLearner] 双品种自动学习守护已启动
  大乐透: 周一、三、六 20:25+10min
  双色球: 周二、四、日 20:30+10min
[OK] Lottery API Server running at http://localhost:5123
```

按 `Ctrl+C` 停止（因为下一步我们要设为系统服务）。

### 7️⃣ 设为系统服务（开机自启）

创建 systemd 服务：

```bash
sudo nano /etc/systemd/system/lottery.service
```

粘贴：

```ini
[Unit]
Description=Hermes v5 Lottery API Server
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/lottery-app
Environment="PATH=/opt/lottery-app/venv/bin"
ExecStart=/opt/lottery-app/venv/bin/python /opt/lottery-app/api_server.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

启动并启用：

```bash
sudo systemctl daemon-reload
sudo systemctl enable lottery
sudo systemctl start lottery
sudo systemctl status lottery   # 查看状态
```

### 8️⃣ 配置 Nginx 反向代理（可选，推荐）

> 这样可以通过域名访问，而不是直接暴露端口。

```bash
apt install -y nginx
sudo nano /etc/nginx/sites-available/lottery
```

```nginx
server {
    listen 80;
    server_name your-domain.com;  # 改成你的域名
    
    location / {
        proxy_pass http://127.0.0.1:5123;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/lottery /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```

### 9️⃣ 防火墙配置

```bash
# 仅开放 80（Nginx）或 5123（直连 API）
ufw allow 80/tcp
ufw allow 5123/tcp   # 如果不用 Nginx
ufw enable
```

> ✅ 至此部署完成！访问 `http://你的服务器IP:5123` 或 `http://你的域名` 即可看到前端页面。

---

## API 端点速查

部署后可以访问的 API：

| 端点 | 说明 | 示例 |
|------|------|------|
| `/` | Web 前端页面 | `http://你的IP:5123/` |
| `/api/status` | 服务器状态 | `http://你的IP:5123/api/status` |
| `/api/config` | 查看 AI 配置 | `http://你的IP:5123/api/config` |
| `/api/latest?kind=dlt` | 最新一期 | `http://你的IP:5123/api/latest?kind=dlt` |
| `/api/history?kind=dlt&limit=10` | 历史数据 | `http://你的IP:5123/api/history?kind=dlt&limit=10` |
| `/api/predict?kind=dlt` | Hermes 统计预测 | `http://你的IP:5123/api/predict?kind=dlt` |
| `/api/predict_ai?kind=dlt` | AI + 统计预测 | `http://你的IP:5123/api/predict_ai?kind=dlt` |
| `/api/predict_selflearn?kind=dlt` | 自进化预测 | `http://你的IP:5123/api/predict_selflearn?kind=dlt` |
| `/api/learning_status?kind=dlt` | 学习状态 | `http://你的IP:5123/api/learning_status?kind=dlt` |

---

## 服务器部署（Windows Server）

> 如果服务器是 Windows，更简单——直接把本机那套搬过去。

### 1️⃣ 安装 Python

下载安装 Python 3.11+：https://www.python.org/downloads/
✅ 安装时勾选 **"Add Python to PATH"**

### 2️⃣ 安装 Git

下载安装 Git for Windows：https://git-scm.com/download/win

### 3️⃣ 克隆代码

```powershell
cd C:\
git clone https://github.com/你的用户名/lottery-app.git
cd lottery-app
```

### 4️⃣ 安装依赖

```powershell
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

### 5️⃣ 创建 config.json（同上，填入真实密钥）

### 6️⃣ 设为 Windows 服务

> 使用 NSSM（Non-Sucking Service Manager）让程序作为后台服务运行。

```powershell
# 下载 nssm
winget install nssm

# 注册为服务
nssm install LotteryService "C:\lottery-app\venv\Scripts\python.exe" "C:\lottery-app\api_server.py"
nssm set LotteryService AppDirectory C:\lottery-app
nssm start LotteryService
```

---

## 日常运维

### 查看服务日志

```bash
# Linux systemd
sudo journalctl -u lottery -f

# 应用日志直接看 stdout
sudo journalctl -u lottery --since "10 min ago"
```

### 更新代码

```bash
cd /opt/lottery-app
git pull
sudo systemctl restart lottery
```

### 检查学习状态

```bash
curl http://localhost:5123/api/learning_status?kind=dlt
# 或浏览器打开 http://你的IP:5123/api/learning_status?kind=dlt
```

### 换模型

编辑 `config.json` 改 `model` 字段，然后重启服务：

```json
{
  "model": "deepseek-chat"    # DeepSeek
  "model": "gpt-4o"          # 如果用 OpenAI 兼容的 API
  "model": "claude-3-opus"   # 如果用 Claude 兼容
}
```

```bash
sudo systemctl restart lottery
```

### 数据备份

```bash
# 备份到本地
tar -czf lottery_backup_$(date +%Y%m%d).tar.gz /opt/lottery-app/data/
```

---

## 🚨 常见问题

**Q: 服务器在海外，抓取 500.com 数据慢怎么办？**
A: 500.com 对海外 IP 可能访问慢。如果遇到问题，可以在服务器上配置 HTTP 代理抓取，或改 `data_fetcher.py` 用国内镜像站。

**Q: OOM (内存不足) 被杀掉了怎么办？**
A: XGBoost 训练比较吃内存。在 `hermes_xgb.py` 中可减少训练轮数：
```python
# 降低 n_estimators（默认 150）
front_model = xgb.XGBClassifier(n_estimators=80, ...)
```

**Q: API 调用超时？**
A: 检查 DeepSeek API Key 是否有效。在服务器上测试：
```bash
curl https://api.deepseek.com/v1/chat/completions \
  -H "Authorization: Bearer sk-2e719532e4324760a47e887b6182993c" \
  -H "Content-Type: application/json" \
  -d '{"model":"deepseek-chat","messages":[{"role":"user","content":"test"}]}'
```
