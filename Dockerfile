FROM python:3.11-slim

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制项目文件
COPY . .

# Zeabur 通过 $PORT 环境变量注入端口，无需 EXPOSE
# 服务器已自动读取 PORT 或 ZEABUR_PORT

# 启动服务
CMD ["python", "api_server.py"]
