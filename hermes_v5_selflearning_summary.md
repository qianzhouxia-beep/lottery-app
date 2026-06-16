# Hermes v5 Self-Learning System - 完成总结

## 目标
为 Hermes 大乐透彩票预测系统构建真正的自主学习闭环，实现：
1. **统计引擎**自动调参（每次开奖后滚动优化权重）
2. **AI 层**注入历史教训（让 DeepSeek 记住上次错在哪）
3. **元学习**自动切换最优策略

## 关键决策
- 统计引擎使用滚动窗口网格搜索（720 组参数组合，20 期测试期）
- AI 教训通过扩展 system prompt 注入，不修改大模型权重
- 元学习跟踪各策略的滚动平均命中率，自动切换
- API 层面的 POST endpoint 用于导入实际开奖结果

## 实现的文件
- `D:\AI\lottery-app\hermes_learner.py` — 核心学习引擎（AdaptiveHermesEngine, LessonMiner, MetaLearner, SelfLearningEngine）
- `D:\AI\lottery-app\self_learn_cli.py` — CLI 管理工具（status/predict/learn/backtest/optimize/interactive）
- `D:\AI\lottery-app\api_server.py`（修改）— 新增 4 个自学习 API 端点
- `D:\AI\lottery-app\start.bat`（更新）— 启动时自动优化权重

## 数据结构
- `data/dlt_adaptive_params.json` — 自适应统计引擎权重
- `data/dlt_lessons.json` — 教训笔记（含类型、期号、具体教训、错误记录）
- `data/dlt_meta.json` — 元学习状态（各策略表现、当前策略）
- `data/dlt_prediction_records.json` — 预测记录历史

## 回测结果
20 期回测（纯统计引擎）：
- 前10期: 前区 0.400/5 后区 0.300/2
- 后10期: 前区 0.700/5 后区 0.200/2
- 改进: 前区 +0.300 (+75%), 后区 -0.100

权重优化网格搜索结果：最优组合为 freq=1.5, repeat=0.3, zone=0, large=0, back=2.0
结论：纯频率+重复模型在数据集上表现最佳，区间和大号权重被优化到零。

## 学习流程
1. `GET /api/predict_selflearn` — 用最新权重+AI教训注入生成预测
2. 开奖后 `POST /api/self_learn` — 传入实际号码 → 触发 complete learning loop
3. 下一次 `predict_selflearn` — 自动使用新权重+新教训
