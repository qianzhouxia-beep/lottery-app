#!/bin/bash
# Hermes v5 大乐透预测服务器 - Linux 启动脚本
set -e

cd "$(dirname "$0")"

echo "================================================"
echo "  Hermes v5 Lottery Predictor"
echo "================================================"

# 检查 Python
if ! command -v python3 &> /dev/null; then
    echo "[错误] 未找到 python3，请先安装 Python 3.11+"
    exit 1
fi

# 检查/创建虚拟环境
if [ ! -d "venv" ]; then
    echo "[安装] 创建 Python 虚拟环境..."
    python3 -m venv venv
    source venv/bin/activate
    echo "[安装] 安装依赖..."
    pip install -r requirements.txt
else
    source venv/bin/activate
fi

echo "[启动] 启动 Hermes v5 服务器..."
exec python3 api_server.py
