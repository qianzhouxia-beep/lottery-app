# Hermes v5 三向升级 🚀

## 已完成的三大升级

### 1. 🔧 架构修复 - 消除循环导入
**问题**: `api_server.py` ↔ `hermes_learner.py` 相互引用，`hermes_learner.py` 的 `predict()` 方法里写死了 `from .api_server import call_deepseek`

**解决**: 新增 `ai_client.py` 共享模块
- 读取 `config.json` 统一管理 API 配置
- 提供 `call_deepseek()`、`AI_SYSTEM_PROMPT`、`AI_CONFIG`
- 同时被 `api_server.py` 和 `hermes_learner.py` 导入，消除循环依赖
- 支持 `update_config()` 热更新模型/密钥

**改动文件**: `ai_client.py` (新增), `api_server.py` (移除本地 AI_CONFIG/AI_SYSTEM_PROMPT/call_deepseek 改为 import), `hermes_learner.py` (导入路径修复)

### 2. 🤖 XGBoost 机器学习引擎
**新增**: `hermes_xgb.py` - 本地机器学习引擎

**原理**:
- 对前区 1-35、后区 1-12 各号码训练二分类 XGBoost
- 每个号码提取 20+ 特征：频率(5/10/20/30期)、间隔、重复率、区间、奇偶、大小、同尾、连号、和值趋势
- 正样本=号码出现, 负样本=号码未出现
- 样本不平衡处理: 负类加权

**集成到 SelfLearningEngine**:
- `self._xgb` 懒初始化
- `predict()` hybrid 模式下 AI分数 + XGBoost分数融合
- `self_learn()` 每 5 期增量重训练
- 失败不阻塞主流程

**测试验证**:
- 517期 DLT 数据训练完成
- XGBoost top-5: [16, 8, 5, 34, 30], 分数 0.42-0.51

### 3. ⏰ 自动学习守护
**新增**: `auto_learner.py` - 自治学习闭环

**功能**:
- 后台线程每 30 分钟检查一次
- 检测是否开奖日+是否已过开奖时间
- 开奖后 10 分钟自动抓取最新数据
- 对比上次学习期号，新数据触发生成器 → 权重优化 + XGBoost 重训练
- 双品种同时守护 (DLT: 周一/三/六 20:25, SSQ: 周二/四/日 20:30)

**集成到 API Server**:
- `api_server.py` 启动时 `AutoLearnerManager().start_all()`

## 文件变更清单

| 文件 | 操作 | 说明 |
|------|------|------|
| `ai_client.py` | **新增** | 共享 AI 客户端，读取 config.json |
| `hermes_xgb.py` | **新增** | XGBoost 机器学习引擎 (19KB) |
| `auto_learner.py` | **新增** | 自动学习守护 (11KB) |
| `api_server.py` | **修改** | 移除本地 AI_CONFIG/call_deepseek，改为 import ai_client；启动时自动守护 |
| `hermes_learner.py` | **修改** | 修复循环导入；集成 XGBoost 训练与融合预测；扩展策略列表 |
| `hermes_deepseek.py` | **修改** | 移除冲突的 sys.stdout 重设 |

## 架构图 (升级后)

```
config.json → ai_client.py ──┬→ api_server.py (HTTP API)
                              └→ hermes_learner.py (SelfLearningEngine)
                                         │
                          ┌──────────────┤
                          ▼              ▼
                   hermes_xgb.py    AdaptiveHermesEngine
                   (XGBoost ML)     (统计权重引擎)
                          │
           ┌──────────────┘
           ▼
    auto_learner.py
    (后台守护 → 抓取 → 学习 → 优化 → 重训)
```

## 启动方式

```bash
# 方式1: 启动 API 服务器（含自动学习守护）
python api_server.py

# 方式2: 纯自动学习模式
python auto_learner.py --once --kind dlt    # 单次检查学习
python auto_learner.py --once --kind all    # 全部检查

# 方式3: 训练 XGBoost
python -c "from hermes_xgb import train_xgb; train_xgb('dlt')"
```
