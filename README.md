# 彩票预测系统

基于 Hermes v4 五引擎融合模型的彩票预测工具，支持大乐透和双色球。

## 快速开始

**方式一：一键启动（推荐）**
```bash
双击 start.bat
```

**方式二：手动启动**
```bash
# 1. 更新数据
python data_fetcher.py

# 2. 启动 API 服务器
python api_server.py

# 3. 打开浏览器访问
# http://localhost:5123
```

## 功能概览

| 功能 | 说明 |
|------|------|
| 🎰 最新开奖 | 实时抓取500.com数据 |
| 📊 趋势分析 | 区间形态、冷热号码统计 |
| 🎯 智能预测 | Hermes v4 五引擎融合预测 |
| 📜 历史记录 | 最近30期完整数据 |
| 🔄 数据更新 | 一键更新最新开奖 |

## API 接口

```
GET /api/latest?kind=dlt    # 最新开奖
GET /api/latest?kind=ssq    # 最新开奖(双色球)
GET /api/trend?kind=dlt     # 趋势分析
GET /api/trend?kind=ssq     # 趋势分析(双色球)
GET /api/predict?kind=dlt  # 生成预测
GET /api/predict?kind=ssq  # 生成预测(双色球)
GET /api/history?kind=dlt&limit=30  # 历史记录
GET /api/review?kind=dlt&period=26063  # 复盘指定期号
GET /api/status             # 数据状态
```

## 项目结构

```
lottery-app/
├── data_fetcher.py    # 数据抓取器（500.com）
├── api_server.py      # API 服务器
├── data/              # 开奖数据存储
│   ├── dlt_history.json
│   └── ssq_history.json
├── web/
│   └── index.html     # Web 前端
├── start.bat          # 一键启动
└── README.md
```

## 数据来源

- 大乐透: https://datachart.500.com/dlt/zoushi/jbzs_foreback.shtml
- 双色球: https://datachart.500.com/ssq/zoushi/jbzs_redblue.shtml

## 技术栈

- 后端: Python 3 (内置http.server)
- 前端: HTML5 + CSS3 + Vanilla JS
- 数据: 500.com 历史走势图表

## 模型说明 (Hermes v4)

五引擎融合：
1. **区间形态引擎** - 分析前区5区、后区3区的分布规律
2. **马尔可夫转移** - 号码从上一期到下一期的转移概率
3. **贝叶斯冷热** - 基于历史频率的冷热号评分
4. **配对关联** - 号码间的共现关系
5. **±2邻位补偿** - 热门号码的邻近号补偿

---

⚠️ 预测仅供参考，请理性购彩
