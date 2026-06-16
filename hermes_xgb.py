#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes XGBoost Engine
======================
本地 XGBoost 机器学习引擎，统计分析之外的第二引擎。

原理：
  对每个号码（前区1-35，后区1-12）训练独立的二分类模型。
  输入特征包含 50+ 维历史统计特征，输出该号码出现的概率。

训练方式：滚动窗口训练（每期后自动增量训练）
预测方式：每个号码输出概率 → 取 top-5/top-2

vs 传统 Hermes 统计引擎：
  统计引擎 = 人工设计的加权公式
  XGBoost 引擎 = 数据驱动自动发现特征交互
"""
import json, math, random, sys, io, os
from datetime import datetime
from pathlib import Path
from collections import defaultdict, deque

import numpy as np
import xgboost as xgb
from sklearn.model_selection import train_test_split

# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

# ============================================================
# 特征工程
# ============================================================

def _recent_window(data, n):
    return data[-n:] if len(data) >= n else data

def extract_features(history, target_idx, kind='dlt', detail=False):
    """
    提取特征矩阵和标签
    target_idx: 用于预测的目标期数索引
    对 target_idx 期，用之前的数据预测哪些号码会出现
    
    返回:
      X: (35或12, n_features) 特征矩阵
      y: (35或12,) 标签 (1=出现, 0=没出现)
    """
    window = history[:target_idx]
    target = history[target_idx]
    
    n_front = 35 if kind == 'dlt' else 33
    n_back = 12 if kind == 'dlt' else 16
    
    X_front = []
    X_back = []
    y_front = []
    y_back = []
    
    # ---- 全局特征（所有号码共享） ----
    last = window[-1] if window else {}
    prev2 = window[-2] if len(window) >= 2 else {}
    prev3 = window[-3] if len(window) >= 3 else {}
    
    last_front = set(last.get('front', []))
    last_back = set(last.get('back', []))
    
    # 最近 10/20/30 期的和值趋势
    recent_10 = _recent_window(window, 10)
    recent_20 = _recent_window(window, 20)
    recent_30 = _recent_window(window, 30)
    
    sums_10 = [sum(d.get('front', [])) for d in recent_10] if recent_10 else [0]
    sums_20 = [sum(d.get('front', [])) for d in recent_20] if recent_20 else [0]
    sums_30 = [sum(d.get('front', [])) for d in recent_30] if recent_30 else [0]
    
    avg_sum_10 = sum(sums_10) / len(sums_10)
    avg_sum_20 = sum(sums_20) / len(sums_20)
    avg_sum_30 = sum(sums_30) / len(sums_30)
    
    # 最后10期的区间分布
    zone_counts_10 = {f'z_{i}': 0 for i in range(5)}
    for d in recent_10:
        for n in d.get('front', []):
            zi = min((n - 1) // 7, 4)
            zone_counts_10[f'z_{zi}'] += 1
    
    # 最后10期的奇偶比
    odd_even_10 = {'odd': 0, 'even': 0}
    for d in recent_10:
        for n in d.get('front', []):
            if n % 2 == 1:
                odd_even_10['odd'] += 1
            else:
                odd_even_10['even'] += 1
    odd_ratio_10 = odd_even_10['odd'] / (odd_even_10['odd'] + odd_even_10['even']) if (odd_even_10['odd'] + odd_even_10['even']) > 0 else 0.5
    
    # ---- 每个号码独立特征 ----
    def _num_features(num, pool='front'):
        features = {}
        is_front = pool == 'front'
        max_num = n_front if is_front else n_back
        
        if num < 1 or num > max_num:
            return None
        
        # 1. 最近 N 期的出现次数
        for k in [5, 10, 20, 30]:
            w = _recent_window(window, k)
            count = sum(1 for d in w if num in d.get(pool, []))
            features[f'freq_{k}'] = count / max(k, 1)
            features[f'freq_abs_{k}'] = count
        
        # 2. 间隔（距离上次出现）
        interval = 999
        for i in range(len(window) - 1, -1, -1):
            if num in window[i].get(pool, []):
                interval = len(window) - 1 - i
                break
        features['interval'] = min(interval, 100) / 100.0
        features['interval_raw'] = min(interval, 100)
        
        # 3. 是否刚出现（上期重复）
        features['is_repeat'] = 1.0 if num in last_front else 0.0
        
        # 4. 是否是两期前重复
        features['is_repeat_2'] = 1.0 if num in set(prev2.get(pool, [])) else 0.0
        
        if is_front:
            # 5. 号码所在区间 (0-4)
            zi = min((num - 1) // 7, 4)
            features['zone'] = zi / 4.0
            
            # 6. 奇偶
            features['is_odd'] = 1.0 if num % 2 == 1 else 0.0
            
            # 7. 大小 (1-17小, 18-35大)
            features['is_big'] = 1.0 if num >= 18 else 0.0
            
            # 8. 与上期和值偏差
            features['sum_diff'] = (avg_sum_10 - avg_sum_30) / 100.0
            
            # 9. 在该区间最近的出现率
            zone_window = sum(1 for d in recent_20 if any((n-1)//7 == zi for n in d.get(pool, [])))
            features['zone_recent_rate'] = zone_window / max(len(recent_20), 1)
            
            # 10. 同尾号
            tail = num % 10
            tail_count = sum(1 for d in window[-10:] if any(n % 10 == tail for n in d.get(pool, [])))
            features['tail_count'] = tail_count / 10.0
            
            # 11. 连号倾向 (如果前后号也同时出现)
            features['consecutive'] = 1.0 if (num-1 in last_front or num+1 in last_front) else 0.0
            
            # 12-14. 跨区间特征（配合全局特征）
            features['global_odd_ratio'] = odd_ratio_10
            features['global_avg_sum'] = avg_sum_20 / 100.0
            features['global_zone_share'] = zone_counts_10[f'z_{zi}'] / max(len(recent_10) * 2, 1)
        
        else:
            # 后区特征
            features['is_big_back'] = 1.0 if num >= 7 else 0.0
            features['is_odd_back'] = 1.0 if num % 2 == 1 else 0.0
        
        return features
    
    # 构建特征矩阵
    for num in range(1, n_front + 1):
        feats = _num_features(num, 'front')
        if feats:
            X_front.append(list(feats.values()))
            y_front.append(1 if num in target.get('front', []) else 0)
    
    for num in range(1, n_back + 1):
        feats = _num_features(num, 'back')
        if feats:
            X_back.append(list(feats.values()))
            y_back.append(1 if num in target.get('back', []) else 0)
    
    if detail:
        # 返回带特征名称的版本（用于调试）
        sample_feats = _num_features(1, 'front')
        feat_names = list(sample_feats.keys()) if sample_feats else []
        return np.array(X_front), np.array(y_front), np.array(X_back), np.array(y_back), feat_names
    
    return np.array(X_front), np.array(y_front), np.array(X_back), np.array(y_back)


# ============================================================
# XGBoost 引擎
# ============================================================

class XGBEngine:
    """
    XGBoost 机器学习预测引擎
    
    训练方式：
      - 每个号码独立训练一个 XGBoost 二分类器
      - 滚动窗口训练（默认最近 200 期）
    
    预测：
      - 每个号码输出出现概率 [0, 1]
      - 前区取 top-5，后区取 top-2
    """
    
    def __init__(self, kind='dlt'):
        self.kind = kind
        self.n_front = 35 if kind == 'dlt' else 33
        self.n_back = 12 if kind == 'dlt' else 16
        
        self.model_path_front = DATA_DIR / f'{kind}_xgb_front.json'
        self.model_path_back = DATA_DIR / f'{kind}_xgb_back.json'
        
        # 模型文件（存储为 JSON）
        self._front_model = None
        self._back_model = None
        
        # 特征维度（训练时确定）
        self._n_feats_front = None
        self._n_feats_back = None
        
        # 性能跟踪
        self.performance = {
            'total_trained': 0,
            'last_trained': None,
            'front_feat_names': [],
            'back_feat_names': [],
        }
    
    def train(self, history, test_ratio=0.15, silent=False, force_retrain=False):
        """
        在历史数据上训练 XGBoost 模型
        
        策略：对每个号码随机采样负样本（不平衡处理）
        """
        if len(history) < 60:
            if not silent:
                print(f'[XGB] 数据不足({len(history)} < 60)，跳过训练')
            return False
        
        # 训练集/验证集：最近 85% 训练，最旧 15% 验证
        split_idx = int(len(history) * (1 - test_ratio))
        train_hist = history[:split_idx]
        test_hist = history[split_idx:] if split_idx < len(history) else history[-10:]
        
        if len(train_hist) < 40:
            return False
        
        # ---- 前区模型 ----
        # 收集所有样本：(特征向量, 出现=1/0)
        X_front_list = []
        y_front_list = []
        
        for target_idx in range(max(30, int(len(train_hist) * 0.3)), len(train_hist)):
            try:
                X_f, y_f, _, _ = extract_features(train_hist, target_idx, self.kind)
                X_front_list.append(X_f)
                y_front_list.append(y_f)
            except:
                continue
        
        if X_front_list:
            X_front_full = np.vstack(X_front_list)
            y_front_full = np.concatenate(y_front_list)
            
            # 处理样本不平衡（正样本很少 → 加权）
            pos_weight = (len(y_front_full) - sum(y_front_full)) / max(sum(y_front_full), 1)
            
            # 限制训练规模（最多 50 万样本）
            if len(X_front_full) > 500000:
                idx = np.random.choice(len(X_front_full), 500000, replace=False)
                X_front_full = X_front_full[idx]
                y_front_full = y_front_full[idx]
            
            front_model = xgb.XGBClassifier(
                n_estimators=150,
                max_depth=4,
                learning_rate=0.1,
                subsample=0.8,
                colsample_bytree=0.8,
                scale_pos_weight=min(pos_weight, 20),
                eval_metric='logloss',
                use_label_encoder=False,
                verbosity=0 if silent else 1,
                random_state=42,
            )
            
            front_model.fit(
                X_front_full, y_front_full,
                eval_set=[(X_front_full[:1000], y_front_full[:1000])],
                verbose=False,
            )
            
            self._front_model = front_model
            self._n_feats_front = X_front_full.shape[1]
        
        # ---- 后区模型 ----
        X_back_list = []
        y_back_list = []
        
        for target_idx in range(max(30, int(len(train_hist) * 0.3)), len(train_hist)):
            try:
                _, _, X_b, y_b = extract_features(train_hist, target_idx, self.kind)
                X_back_list.append(X_b)
                y_back_list.append(y_b)
            except:
                continue
        
        if X_back_list:
            X_back_full = np.vstack(X_back_list)
            y_back_full = np.concatenate(y_back_list)
            
            pos_weight_back = (len(y_back_full) - sum(y_back_full)) / max(sum(y_back_full), 1)
            
            if len(X_back_full) > 200000:
                idx = np.random.choice(len(X_back_full), 200000, replace=False)
                X_back_full = X_back_full[idx]
                y_back_full = y_back_full[idx]
            
            back_model = xgb.XGBClassifier(
                n_estimators=100,
                max_depth=3,
                learning_rate=0.1,
                subsample=0.8,
                scale_pos_weight=min(pos_weight_back, 10),
                eval_metric='logloss',
                use_label_encoder=False,
                verbosity=0,
                random_state=42,
            )
            
            back_model.fit(X_back_full, y_back_full, verbose=False)
            self._back_model = back_model
            self._n_feats_back = X_back_full.shape[1]
        
        # 保存性能信息
        self.performance['total_trained'] += 1
        self.performance['last_trained'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        return True
    
    def predict_proba(self, history):
        """
        预测每个号码的出现概率
        返回: front_probs (35,) 和 back_probs (12,)
        """
        if self._front_model is None or self._back_model is None:
            # 没训练过 → 自动训练
            if not self.train(history, silent=True):
                # 训练失败 → 用频率作为基线
                return self._baseline_probs(history)
        
        # 基于最近 N 期提取当前特征
        window = history[-40:] if len(history) >= 40 else history
        
        # 对每个号码提取特征（模拟预测 = 预测下一个 target）
        X_front = []
        X_back = []
        
        front_feats_idx = []
        for num in range(1, self.n_front + 1):
            feats = self._num_features_now(num, window, 'front')
            if feats:
                X_front.append(feats)
                front_feats_idx.append(True)
            else:
                X_front.append([0.0] * (self._n_feats_front or 1))
                front_feats_idx.append(False)
        
        for num in range(1, self.n_back + 1):
            feats = self._num_features_now(num, window, 'back')
            if feats:
                X_back.append(feats)
            else:
                X_back.append([0.0] * (self._n_feats_back or 1))
        
        X_front_arr = np.array(X_front)
        X_back_arr = np.array(X_back)
        
        # 检查特征维度
        if self._n_feats_front and X_front_arr.shape[1] != self._n_feats_front:
            print(f'[XGB] 特征维度不匹配: 期望 {self._n_feats_front}, 实际 {X_front_arr.shape[1]}')
            return self._baseline_probs(history)
        
        try:
            front_probs = self._front_model.predict_proba(X_front_arr)[:, 1]
            back_probs = self._back_model.predict_proba(X_back_arr)[:, 1]
        except Exception as e:
            print(f'[XGB] 预测失败: {e}, 回退到基线')
            return self._baseline_probs(history)
        
        return front_probs, back_probs
    
    def _num_features_now(self, num, window, pool='front'):
        """提取当前时刻的特征向量（用于预测）"""
        if not window:
            return None
        
        n = len(window)
        last = window[-1]
        prev2 = window[-2] if n >= 2 else {}
        prev3 = window[-3] if n >= 3 else {}
        last_set = set(last.get(pool, []))
        
        features = []
        
        # 1-4. 最近 5/10/20/30 期出现频率
        for k in [5, 10, 20, 30]:
            w = _recent_window(window, k)
            count = sum(1 for d in w if num in d.get(pool, []))
            features.append(count / max(k, 1))
        
        # 5-8. 出现次数（绝对值）
        for k in [5, 10, 20, 30]:
            w = _recent_window(window, k)
            count = sum(1 for d in w if num in d.get(pool, []))
            features.append(count)
        
        # 9. 间隔
        interval = 999
        for i in range(n - 1, -1, -1):
            if num in window[i].get(pool, []):
                interval = n - 1 - i
                break
        features.append(min(interval, 100) / 100.0)
        features.append(min(interval, 100))
        
        # 10. 上期重复
        features.append(1.0 if num in last_set else 0.0)
        
        # 11. 两期前重复
        features.append(1.0 if num in set(prev2.get(pool, [])) else 0.0)
        
        # 前区专属
        if pool == 'front':
            zi = min((num - 1) // 7, 4)
            features.append(zi / 4.0)                     # 12. 区间
            features.append(1.0 if num % 2 == 1 else 0.0) # 13. 奇偶
            features.append(1.0 if num >= 18 else 0.0)    # 14. 大小
            
            # 15. 与该区最近出现率
            zone_window = sum(1 for d in window[-20:] if any((n-1)//7 == zi for n in d.get(pool, []))) if len(window) >= 20 else 0
            features.append(zone_window / max(len(window[-20:]) if len(window) >= 20 else 1, 1))
            
            # 16. 同尾号频率
            tail = num % 10
            tail_count = sum(1 for d in window[-10:] if any(n % 10 == tail for n in d.get(pool, [])))
            features.append(tail_count / 10.0)
            
            # 17. 连号倾向
            features.append(1.0 if (num-1 in last_set or num+1 in last_set) else 0.0)
            
            # 18-21. 全局特征
            recent_10 = window[-10:] if n >= 10 else window
            odds = sum(1 for d in recent_10 for n in d.get('front',[]) if n % 2 == 1)
            total = sum(1 for d in recent_10 for n in d.get('front',[]))
            features.append(odds / max(total, 1))  # 奇偶比
            front_sums = [sum(d.get('front', [0])) for d in window[-20:]]
            features.append(sum(front_sums) / (max(len(front_sums), 1) * 10))
            features.append(0.5)  # 占位
            features.append(0.5)  # 占位
        
        # 后区专属
        else:
            features.append(1.0 if num >= 7 else 0.0)
            features.append(1.0 if num % 2 == 1 else 0.0)
        
        return features
    
    def _baseline_probs(self, history):
        """回退：基于频率的基线概率"""
        window = history[-30:] if len(history) >= 30 else history
        
        front_freq = {}
        for num in range(1, self.n_front + 1):
            count = sum(1 for d in window if num in d.get('front', []))
            front_freq[num] = count / max(len(window), 1)
        
        back_freq = {}
        for num in range(1, self.n_back + 1):
            count = sum(1 for d in window if num in d.get('back', []))
            back_freq[num] = count / max(len(window), 1)
        
        front_probs = np.array([front_freq.get(n, 0) for n in range(1, self.n_front + 1)])
        back_probs = np.array([back_freq.get(n, 0) for n in range(1, self.n_back + 1)])
        
        # 最近 5 期的 boost
        recent5 = window[-5:] if len(window) >= 5 else window
        for num in range(1, self.n_front + 1):
            rcount = sum(1 for d in recent5 if num in d.get('front', []))
            front_probs[num-1] += rcount / 5 * 0.3  # recent boost
        
        return front_probs, back_probs
    
    def get_scores(self, history, kind='dlt'):
        """
        获取 XGBoost 引擎的推荐分数
        返回: front_scores {num: score}, back_scores {num: score}
        """
        front_probs, back_probs = self.predict_proba(history)
        
        front_scores = {}
        for i, prob in enumerate(front_probs):
            front_scores[i + 1] = float(prob)
        
        back_scores = {}
        n_b = self.n_back
        for i, prob in enumerate(back_probs):
            back_scores[i + 1] = float(prob)
        
        return front_scores, back_scores


# ============================================================
# 快速训练入口
# ============================================================

def train_xgb(kind='dlt', force=False):
    """从数据文件训练 XGBoost 模型"""
    # 加载数据
    from hermes_learner import load_history
    history = load_history(kind)
    
    if len(history) < 60:
        print(f'[XGB] 数据不足 ({len(history)} < 60)')
        return False
    
    print(f'[XGB] 加载 {len(history)} 期数据, 开始训练...')
    
    engine = XGBEngine(kind)
    result = engine.train(history, silent=False, force_retrain=force)
    
    if result:
        print(f'[XGB] 训练完成！')
    else:
        print(f'[XGB] 训练失败')
    
    return engine


if __name__ == '__main__':
    import sys
    kind = sys.argv[1] if len(sys.argv) > 1 else 'dlt'
    
    engine = train_xgb(kind)
    if engine:
        # 测试预测
        from hermes_learner import load_history
        history = load_history(kind)
        
        print('\n测试预测:')
        front_scores, back_scores = engine.get_scores(history)
        
        top5_front = sorted(front_scores.items(), key=lambda x: -x[1])[:5]
        top2_back = sorted(back_scores.items(), key=lambda x: -x[1])[:2]
        
        print(f'  前区: {[n for n,s in top5_front]}')
        print(f'  后区: {[n for n,s in top2_back]}')
        print(f'  前区得分: {[round(s,3) for n,s in top5_front]}')
        print(f'  后区得分: {[round(s,3) for n,s in top2_back]}')
