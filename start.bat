@echo off
chcp 65001 >nul
title Hermes v5 - Self-Learning Lottery System
cd /d "%~dp0"

echo ========================================
echo   Hermes v5 · 自适应彩票预测系统
echo   ─────────────────────────────
echo   自学习引擎已加载
echo ========================================
echo.

echo [1/4] 更新数据...
python data_fetcher.py
if errorlevel 1 (
    echo 数据获取完成（可跳过）
)

echo [2/4] 优化统计引擎权重...
python self_learn_cli.py optimize >nul 2>&1
echo        OK

echo [3/4] 启动 API 服务 (端口 5123)...
start "HermesAPI" /min python api_server.py

echo [4/4] 打开浏览器...
timeout /t 3 /nobreak >nul
start http://localhost:5123/

echo.
echo ========================================
echo   ✅ 系统已就绪！
echo ========================================
echo.
echo   📊 前端界面:  http://localhost:5123
echo   🤖 AI预测:    http://localhost:5123/api/predict_ai?kind=dlt
echo   🧠 自学习:    http://localhost:5123/api/predict_selflearn?kind=dlt
echo   📈 学习状态:  http://localhost:5123/api/learning_status?kind=dlt
echo.
echo   🎯 导入开奖结果触发学习:
echo      python self_learn_cli.py learn 期号 前区号码 后区号码
echo.
echo   ❌ 关闭: 关掉 HermesAPI 窗口
echo.
pause
