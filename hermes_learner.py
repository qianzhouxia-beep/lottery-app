#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes Self-Learning Engine v5
===============================
真正的自主学习闭环系统

学习流程：
  预测 → 记录 → 等开奖 → 导入实际结果 → 自我修正 → 下次更好
                                                    ↑
                               ← 持续反馈循环 ←┘

学习机制：
  1. 统计引擎：每期后自动滚动调参（Grid Search on rolling window）
  2. AI 层：将历史预测偏差提炼为"教训"，注入下次 prompt
  3. 元学习：跟踪各策略表现，自动选择最优策略
"""
import json, time, os, random, math
from datetime import datetime
from pathlib import Path
from collections import defaultdict
from itertools import combinations

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

# ============================================================
# 数据加载
# ============================================================

def load_history(kind='dlt'):
    """加载历史开奖数据"""
    fname = f'{kind}_history_full.json'
    path = DATA_DIR / fname
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    path = DATA_DIR / f'{kind}_history.json'
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ============================================================
# 统计引擎 - Hermes v5 Adaptive
# ============================================================

class AdaptiveHermesEngine:
    """
    自适应 Hermes 统计引擎
    - 每次开奖后自动调参
    - 滚动窗口优化权重
    """
    
    ZONES_FRONT = [(1,7), (8,14), (15,21), (22,28), (29,35)]
    ZONES_BACK = [(1,4), (5,8), (9,12)]
    
    # 默认权重
    DEFAULT_PARAMS = {
        'w_freq': 2.0,
        'w_repeat': 0.5,
        'w_zone': 0.3,
        'w_large': 0.3,
        'w_back': 3.0,
        'w_ai_front': 0.4,    # AI 置信度对前区的影响权重
        'w_ai_back': 0.4,     # AI 置信度对后区的影响权重
    }
    
    def __init__(self, kind='dlt'):
        self.kind = kind
        self.params_path = DATA_DIR / f'{kind}_adaptive_params.json'
        self.params = self._load_params()
    
    def _load_params(self):
        """加载当前最优参数"""
        if self.params_path.exists():
            with open(self.params_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return dict(self.DEFAULT_PARAMS)
    
    def _save_params(self):
        """保存参数"""
        with open(self.params_path, 'w', encoding='utf-8') as f:
            json.dump(self.params, f, ensure_ascii=False, indent=2)
    
    def zone_stats(self, nums, zones):
        """计算区间分布"""
        return [sum(1 for n in nums if z1 <= n <= z2) for z1, z2 in zones]
    
    def hot_cold(self, data, key='front', n=15):
        """频率分析"""
        freq = defaultdict(float)
        for draw in data[-n:]:
            for num in draw.get(key, []):
                freq[num] += 1.0
        total = sum(freq.values()) or 1
        return {num: c/total for num, c in freq.items()}
    
    def avg_diff(self, data, key='front'):
        """平均差值"""
        diffs = []
        for i in range(1, min(len(data), 10)):
            d1 = sum(data[-i].get(key, []))
            d2 = sum(data[-i-1].get(key, []))
            diffs.append(abs(d1 - d2))
        return sum(diffs) / len(diffs) if diffs else 0
    
    def predict(self, history, n=2, ai_front_scores=None, ai_back_scores=None):
        """
        使用自适应权重生成预测
        - ai_front_scores: dict {号码: 置信度(0-0.5)} 由 AI 层提供
        - ai_back_scores: 同上
        """
        if len(history) < 10:
            return None
        
        recent = history[-10:]
        last = history[-1]
        p = self.params  # 当前最优权重
        
        # 区间统计
        last_front = last.get('front', [])
        last_fz = self.zone_stats(last_front, self.ZONES_FRONT)
        
        hf = self.hot_cold(history[-15:], 'front')
        hb = self.hot_cold(history[-15:], 'back')
        
        prev2 = history[-2].get('front', []) if len(history) >= 2 else []
        prev3 = history[-3].get('front', []) if len(history) >= 3 else []
        
        avg_diff_val = self.avg_diff(history[-10:], 'front')
        
        # 和值趋势
        sums = [sum(d.get('front', [])) for d in history[-10:]]
        sum_trend = sums[-1] - sums[-2] if len(sums) >= 2 else 0
        avg_sum = sum(sums) / len(sums)
        
        candidates = {}
        for num in range(1, 36):
            score = 0.0
            
            # 引擎1: 区间形态 (Zone)
            for i, (z1, z2) in enumerate(self.ZONES_FRONT):
                if z1 <= num <= z2:
                    score += p['w_zone'] * (0.3 if last_fz[i] > 0 else -0.1)
                    break
            
            # 引擎2: 频率热度 (Frequency)
            freq = hf.get(num, 0)
            score += p['w_freq'] * freq
            
            # 引擎3: 重复概率 (Repeat)
            repeat_score = 0.0
            if num in prev2: repeat_score += 0.5
            if num in prev3: repeat_score += 0.3  # 前3期也出现
            score += p['w_repeat'] * repeat_score
            
            # 引擎4: 大号/小号补偿 (Large/Small)
            if avg_sum > 110:
                if num <= 90: score += p['w_large'] * 0.3
            elif avg_sum < 75:
                if num >= 25: score += p['w_large'] * 0.3
            else:
                score += p['w_large'] * 0.15  # 中和时给均匀加权
            
            # AI 置信度提升
            if ai_front_scores and num in ai_front_scores:
                score += p['w_ai_front'] * ai_front_scores[num]
            
            candidates[num] = score
        
        sorted_nums = sorted(candidates.items(), key=lambda x: -x[1])
        
        results = []
        for strategy in ['normal', 'reverse']:
            if strategy == 'normal':
                chosen = sorted_nums[:5]
            else:
                # 反选：从最低分中选，但避开正选号码
                exclude = set(x[0] for x in sorted_nums[:10])  # 排除前10高分
                reverse_candidates = [(n, s) for n, s in sorted_nums if n not in exclude]
                if len(reverse_candidates) < 5:
                    reverse_candidates = sorted_nums[-15:]
                chosen = reverse_candidates[:5]
            
            front = sorted([n for n, s in chosen])
            
            # 后区选择
            if ai_back_scores:
                hb_scores = {}
                for n in range(1, 13):
                    hb_scores[n] = hb.get(n, 0) * p['w_back'] + ai_back_scores.get(n, 0) * p['w_ai_back']
            else:
                hb_scores = {n: hb.get(n, 0) * p['w_back'] for n in range(1, 13)}
            
            hb_sorted = sorted(hb_scores.items(), key=lambda x: -x[1])
            
            if strategy == 'normal':
                back = [n for n, s in hb_sorted[:2]]
            else:
                back = [n for n, s in hb_sorted[-3:]]  # 后区反选：最低分
                if len(back) > 2: back = back[:2]
            
            back.sort()
            results.append({
                'type': 'normal' if strategy == 'normal' else 'reverse',
                'front': front,
                'back': back,
                'sum': sum(front),
            })
        
        return results
    
    def optimize_weights(self, history, window=30, verbose=True):
        """
        滚动窗口网格搜索 - 核心学习机制
        用最近 window 期数据跑网格搜索，找到最优权重
        """
        if len(history) < window + 5:
            if verbose: print(f'  [优化] 数据不足，跳过调参 ({len(history)} < {window+5})')
            return self.params
        
        # 定义搜索空间
        search_space = {
            'w_freq': [1.0, 1.5, 2.0, 2.5, 3.0],
            'w_repeat': [0.0, 0.3, 0.5, 0.8],
            'w_zone': [0.0, 0.2, 0.3, 0.5],
            'w_large': [0.0, 0.2, 0.3],
            'w_back': [2.0, 3.0, 4.0],
        }
        
        best_f_score = -1
        best_params = dict(self.params)
        total_combos = 1
        for k, v in search_space.items():
            total_combos *= len(v)
        
        # 测试用的最近 window 期数据
        test_data = history[-window:]
        test_start = max(5, len(test_data) // 3)  # 留出测试期
        
        count = 0
        for wf in search_space['w_freq']:
            for wr in search_space['w_repeat']:
                for wz in search_space['w_zone']:
                    for wl in search_space['w_large']:
                        for wb in search_space['w_back']:
                            test_params = {
                                'w_freq': wf, 'w_repeat': wr, 'w_zone': wz,
                                'w_large': wl, 'w_back': wb,
                                'w_ai_front': self.params.get('w_ai_front', 0.4),
                                'w_ai_back': self.params.get('w_ai_back', 0.4),
                            }
                            count += 1
                            
                            # 在测试期上评价参数
                            total_fh = 0
                            total_bh = 0
                            n_test = 0
                            
                            for i in range(test_start, len(test_data)):
                                hist = test_data[:i]
                                actual = test_data[i]
                                
                                # 临时替换参数做预测
                                old_params = dict(self.params)
                                self.params = test_params
                                preds = self.predict(hist, n=1)
                                self.params = old_params
                                
                                if not preds:
                                    continue
                                
                                pred_front = set(preds[0]['front'])
                                pred_back = set(preds[0]['back'])
                                actual_front = set(actual.get('front', []))
                                actual_back = set(actual.get('back', []))
                                
                                total_fh += len(pred_front & actual_front)
                                total_bh += len(pred_back & actual_back)
                                n_test += 1
                            
                            if n_test == 0:
                                continue
                            
                            avg_fh = total_fh / n_test
                            avg_bh = total_bh / n_test
                            f_score = avg_fh * 3 + avg_bh * 2  # 综合评分
                            
                            if f_score > best_f_score:
                                best_f_score = f_score
                                best_params = dict(test_params)
        
        if verbose:
            print(f'  [优化] 搜索 {count} 组参数 → 最佳: '
                  f'F={best_params["w_freq"]} R={best_params["w_repeat"]} '
                  f'Z={best_params["w_zone"]} L={best_params["w_large"]} '
                  f'B={best_params["w_back"]} (score={best_f_score:.2f})')
        
        self.params = best_params
        self._save_params()
        return best_params


# ============================================================
# 教训提取器 - Lesson Miner
# ============================================================

class LessonMiner:
    """
    从历史预测偏差中提炼可用的"教训"
    每次 self_learn 后更新 lessons，供下次 AI prompt 注入
    """
    
    def __init__(self, kind='dlt'):
        self.kind = kind
        self.lessons_path = DATA_DIR / f'{kind}_lessons.json'
        self.lessons = self._load_lessons()
    
    def _load_lessons(self):
        """加载已存储的教训"""
        if self.lessons_path.exists():
            with open(self.lessons_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'lessons': [],          # 教训列表 [{period, error_type, lesson_text, weight}]
            'recent_errors': [],     # 最近错误速览
            'last_updated': None,
        }
    
    def _save_lessons(self):
        with open(self.lessons_path, 'w', encoding='utf-8') as f:
            json.dump(self.lessons, f, ensure_ascii=False, indent=2)
    
    def extract(self, prediction, actual, kind_label='大乐透'):
        """
        分析单次预测偏差，提炼教训
        prediction: { 'prediction': {front:[], back:[]}, 'reverse': {front:[], back:[]} }
        actual: {front:[], back:[], period:''}
        """
        pred_f = set(prediction.get('prediction', {}).get('front', []))
        pred_b = set(prediction.get('prediction', {}).get('back', []))
        rev_f = set(prediction.get('reverse', {}).get('front', []))
        rev_b = set(prediction.get('reverse', {}).get('back', []))
        actual_f = set(actual.get('front', []))
        actual_b = set(actual.get('back', []))
        
        period = actual.get('period', '?')
        
        fh = len(pred_f & actual_f)
        bh = len(pred_b & actual_b)
        rev_fh = len(rev_f & actual_f)
        rev_bh = len(rev_b & actual_b)
        
        lessons = []
        
        # 1. 正选全错 → 严重教训
        if fh == 0:
            # 分析实际号码的特征
            act_sum = sum(actual_f)
            act_zones = self._zone_summary(actual_f)
            lessons.append({
                'period': period,
                'type': '完全错失',
                'lesson': f'第{period}期正选全部错误，实际号码{actual_f}，和值{act_sum}，区间分布{act_zones}',
            })
        
        # 2. 反选命中 > 正选 → 说明方向错了
        if rev_fh > fh:
            lessons.append({
                'period': period,
                'type': '方向反了',
                'lesson': f'第{period}期反选命中({rev_fh}/{rev_bh})多于正选({fh}/{bh})，说明趋势判断方向相反，下次应更重视冷号',
            })
        
        # 3. 前区偏差分析
        if fh <= 1:
            # 实际号码中哪些在正选候选池但没入选
            all_pred = pred_f | rev_f
            missed = actual_f - all_pred
            if len(missed) >= 2:
                lessons.append({
                    'period': period,
                    'type': '遗漏模式',
                    'lesson': f'第{period}期完全未预见号码{missed}，检查是否忽略了连号/同尾模式',
                })
        
        # 4. 后区偏差分析
        if bh == 0 and rev_bh == 0:
            lessons.append({
                'period': period,
                'type': '后区全错',
                'lesson': f'第{period}期后区全部错误(实际{actual_b})，后区{list(actual_b)[0] if actual_b else "?"}近期需重点关注',
            })
        
        # 记录
        error_summary = {
            'period': period,
            'front_hits': fh,
            'back_hits': bh,
            'reverse_front_hits': rev_fh,
            'reverse_back_hits': rev_bh,
            'predicted': {'front': list(pred_f), 'back': list(pred_b)},
            'actual': {'front': list(actual_f), 'back': list(actual_b)},
        }
        
        # 更新 lessons 列表
        for l in lessons:
            self.lessons['lessons'].append(l)
        
        self.lessons['recent_errors'].append(error_summary)
        
        # 只保留最近 30 条 lessons 和 20 条错误记录
        if len(self.lessons['lessons']) > 30:
            self.lessons['lessons'] = self.lessons['lessons'][-30:]
        if len(self.lessons['recent_errors']) > 20:
            self.lessons['recent_errors'] = self.lessons['recent_errors'][-20:]
        
        self.lessons['last_updated'] = datetime.now().isoformat()
        self._save_lessons()
        
        return lessons
    
    def _zone_summary(self, nums):
        """号码区间摘要"""
        zones = {'S': 0, 'M1': 0, 'M2': 0, 'M3': 0, 'L': 0}
        for n in nums:
            if n <= 12: zones['S'] += 1
            elif n <= 23: zones['M1'] += 1
            elif n <= 29: zones['M2'] += 1
            elif n <= 34: zones['M3'] += 1
            else: zones['L'] += 1
        return '-'.join(f'{k}{v}' for k,v in zones.items() if v > 0)
    
    def get_prompt_injection(self, max_lessons=5):
        """生成供 AI prompt 注入的教训文本"""
        if not self.lessons['lessons']:
            return ''
        
        # 取最近 max_lessons 条
        recent = self.lessons['lessons'][-max_lessons:]
        
        lines = ['\n📚 近期学习笔记（来自历史预测偏差分析，务必参考）：']
        for l in recent:
            lines.append(f'  • {l["lesson"]}')
        
        # 加入统计摘要
        if self.lessons['recent_errors']:
            last_n = self.lessons['recent_errors'][-10:]
            hit_summary = defaultdict(int)
            zero_summary = 0
            for e in last_n:
                hit_summary[e['front_hits']] += 1
                if e['front_hits'] == 0:
                    zero_summary += 1
            
            lines.append(f'\n📊 最近{len(last_n)}期预测统计：')
            lines.append(f'  前区命中分布(0~5次): ' + 
                        ', '.join(f'{k}期:{v}次' for k,v in sorted(hit_summary.items())))
            if zero_summary > 0:
                lines.append(f'  警告：{zero_summary}期前区完全未命中，请特别注意冷门号码！')
        
        lines.append('')
        return '\n'.join(lines)
    
    def get_performance_summary(self):
        """获取性能摘要"""
        if not self.lessons['recent_errors']:
            return {'total': 0, 'avg_front': 0, 'avg_back': 0, 'any_hit_rate': 0}
        
        errors = self.lessons['recent_errors']
        total = len(errors)
        avg_f = sum(e['front_hits'] for e in errors) / total
        avg_b = sum(e['back_hits'] for e in errors) / total
        any_hit = sum(1 for e in errors if e['front_hits'] > 0 or e['back_hits'] > 0)
        any_hit_rate = round(any_hit / total * 100, 1) if total > 0 else 0
        return {
            'total': total,
            'avg_front': round(avg_f, 3),
            'avg_back': round(avg_b, 3),
            'any_hit_rate': any_hit_rate,
        }


# ============================================================
# 元学习器 - MetaLearner
# ============================================================

class MetaLearner:
    """
    元学习层：跟踪各策略表现，自动切换最优方案
    策略列表：
      - pure_stats: 纯 Hermes 统计引擎
      - ai_only: 纯 AI 预测
      - hybrid: AI 排名 + 统计引擎融合（当前方案）
    """
    
    STRATEGIES = ['pure_stats', 'hybrid', 'xgb', 'hybrid_xgb']
    
    def __init__(self, kind='dlt'):
        self.kind = kind
        self.meta_path = DATA_DIR / f'{kind}_meta.json'
        self.meta = self._load_meta()
    
    def _load_meta(self):
        if self.meta_path.exists():
            with open(self.meta_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'strategy_performance': {s: {'total': 0, 'front_hits': 0, 'back_hits': 0, 'runs': []} 
                                     for s in self.STRATEGIES},
            'current_strategy': 'hybrid',
            'last_switched': None,
        }
    
    def _save_meta(self):
        with open(self.meta_path, 'w', encoding='utf-8') as f:
            json.dump(self.meta, f, ensure_ascii=False, indent=2)
    
    def record_result(self, strategy, front_hits, back_hits, period=None):
        """记录某策略在某期的表现"""
        if strategy not in self.meta['strategy_performance']:
            return
        
        perf = self.meta['strategy_performance'][strategy]
        perf['total'] += 1
        perf['front_hits'] += front_hits
        perf['back_hits'] += back_hits
        perf['runs'].append({
            'period': period or '?',
            'front_hits': front_hits,
            'back_hits': back_hits,
        })
        # 只保留最近 50 期记录
        perf['runs'] = perf['runs'][-50:]
        self._save_meta()
    
    def get_best_strategy(self, window=10):
        """
        获取最近 window 期内表现最佳的策略
        """
        best_score = -1
        best_strat = self.meta.get('current_strategy', 'hybrid')
        
        for strat, perf in self.meta['strategy_performance'].items():
            recent = perf['runs'][-window:]
            if not recent:
                continue
            
            avg_f = sum(r['front_hits'] for r in recent) / len(recent)
            avg_b = sum(r['back_hits'] for r in recent) / len(recent)
            score = avg_f * 3 + avg_b * 2  # 综合评分
            
            if score > best_score:
                best_score = score
                best_strat = strat
        
        return best_strat, best_score
    
    def evaluate_and_switch(self, min_recent=5):
        """
        评估并决定是否切换策略
        """
        best_strat, best_score = self.get_best_strategy()
        current = self.meta.get('current_strategy', 'hybrid')
        
        # 当前策略最近表现
        curr_perf = self.meta['strategy_performance'].get(current, {})
        curr_recent = curr_perf.get('runs', [])[-min_recent:]
        if len(curr_recent) < min_recent:
            return current, False  # 样本太少，不切换
        
        curr_avg_f = sum(r['front_hits'] for r in curr_recent) / len(curr_recent)
        curr_avg_b = sum(r['back_hits'] for r in curr_recent) / len(curr_recent)
        curr_score = curr_avg_f * 3 + curr_avg_b * 2
        
        # 如果最优策略明显更好（>20%），切换
        if best_strat != current and best_score > curr_score * 1.2:
            self.meta['current_strategy'] = best_strat
            self.meta['last_switched'] = datetime.now().isoformat()
            self._save_meta()
            return best_strat, True
        
        return current, False
    
    def get_status(self):
        """获取元学习状态"""
        status = {
            'current_strategy': self.meta.get('current_strategy', 'hybrid'),
            'last_switched': self.meta.get('last_switched'),
        }
        for s in self.STRATEGIES:
            p = self.meta['strategy_performance'][s]
            if p['total'] > 0:
                avg_f = p['front_hits'] / p['total']
                avg_b = p['back_hits'] / p['total']
                status[s] = {
                    'total': p['total'],
                    'avg_front': round(avg_f, 3),
                    'avg_back': round(avg_b, 3),
                }
        return status


# ============================================================
# 主学习引擎 - SelfLearningEngine
# ============================================================

class SelfLearningEngine:
    """
    Hermes v5 自主学习引擎 - 完整的 self-learning 闭环
    
    使用方式:
      engine = SelfLearningEngine('dlt')
      
      # 预测
      result = engine.predict(history)
      
      # 开奖后反馈学习
      engine.self_learn(prediction_record, actual_result)
    """
    
    def __init__(self, kind='dlt'):
        self.kind = kind
        self.kind_label = '大乐透' if kind == 'dlt' else '双色球'
        self.stats = AdaptiveHermesEngine(kind)
        self.lessons = LessonMiner(kind)
        self.meta = MetaLearner(kind)
        
        # XGBoost 机器学习引擎（懒初始化，首次训练约 30 秒）
        self._xgb = None
        self._xgb_trained = False
        
        # 加载预测记录
        self.records_path = DATA_DIR / f'{kind}_prediction_records.json'
        self.records = self._load_records()
    
    def _load_records(self):
        if self.records_path.exists():
            with open(self.records_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {'records': []}
    
    def _save_records(self):
        with open(self.records_path, 'w', encoding='utf-8') as f:
            json.dump(self.records, f, ensure_ascii=False, indent=2)
    
    def build_ai_prompt(self, history, n_history=30):
        """
        构建增强版的 AI prompt，包含：
        1. 历史数据
        2. 教训笔记注入
        3. 当前自适应权重的提示
        """
        # 基础数据
        lines = []
        for d in history[-n_history:]:
            f = ','.join(str(x) for x in d.get('front', []))
            b = ','.join(str(x) for x in d.get('back', []))
            lines.append(f"{d.get('period','?')}:[{f}]+[{b}]")
        data_str = '\n'.join(reversed(lines))
        
        # 注入教训笔记
        lesson_text = self.lessons.get_prompt_injection(max_lessons=5)
        
        # 性能摘要
        perf = self.lessons.get_performance_summary()
        
        prompt = f'''分析最近{n_history}期{self.kind_label}数据，预测下一期：

{data_str}

{lesson_text}

当前模型最近{perf['total']}期平均命中率：前区{perf['avg_front']}/5，后区{perf['avg_back']}/2，综合命中率{perf['any_hit_rate']}%。
注意：请从这些历史错误中学习，避免重复相同的错误判断。

输出严格JSON格式：
{{
  "analysis": {{
    "hot_front": [按热度排序的前区号码(最多10个)],
    "cold_front": [冷门号码(最多5个)],
    "hot_back": [后区热号(最多5个)],
    "cold_back": [后区冷号(最多3个)],
    "zone_distribution": {{"S":1-12区数量,"M1":13-23区数量,"M2":24-29区数量,"M3":30-35区数量}},
    "sum_range": "low/mid/high",
    "trend": "近期趋势描述（15字以内）"
  }},
  "ranked_front": [{{"num":号码,"confidence":置信度(0-1)}}, ...], // 35个号码全部列出，按置信度降序
  "ranked_back": [{{"num":号码,"confidence":置信度(0-1)}}, ...],   // 12个号码全部列出，按置信度降序
  "prediction": {{
    "front": [5个正选前区号],
    "back": [2个正选后区号],
    "reason": "预测逻辑（20字以内）"
  }},
  "reverse": {{
    "front": [5个反选前区号（必须与正选完全不同）],
    "back": [2个反选后区号（必须与正选完全不同）],
    "reason": "反选逻辑（20字以内）"
  }}
}}
只输出JSON，不要其他文字。'''

        return prompt
    
    def predict(self, history, strategy=None, call_ai_func=None, **kwargs):
        """
        执行一次完整预测（含自学习上下文）
        
        参数:
          history: 历史数据列表
          strategy: 可选 'pure_stats' | 'hybrid' | None(自动选)
          call_ai_func: 外部 AI 调用函数，格式 func(system_prompt, user_prompt) -> str
          **kwargs: 透传给 AI 预测的额外参数
        
        返回:
          { 'prediction': {...}, 'reverse': {...}, 'ranked_front': [...],
            'model': '...', 'strategy': '...', 'for_period': '...' }
        """
        if len(history) < 10:
            return {'error': '历史数据不足'}
        
        next_period = str(int(history[-1].get('period', 0)) + 1)
        
        # 如果未指定策略，由元学习器决定
        if strategy is None:
            best_strat, _ = self.meta.get_best_strategy()
            strategy = best_strat
            # 如果混合策略但 AI 不可用，回退
            if strategy == 'hybrid' and call_ai_func is None:
                strategy = 'pure_stats'
        
        result = {
            'for_period': next_period,
            'strategy': strategy,
            'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
        
        if strategy == 'pure_stats' or call_ai_func is None:
            # 纯统计引擎预测
            preds = self.stats.predict(history, n=2)
            if not preds:
                return {'error': '统计引擎预测失败'}
            
            result.update({
                'model': 'Hermes v5 Adaptive Stats',
                'analysis': {'summary': '纯统计引擎预测，AI未参与'},
                'ranked_front': [],
                'ranked_back': [],
                'prediction': {
                    'front': preds[0]['front'],
                    'back': preds[0]['back'],
                    'reason': f'Hermes v5 自适应统计引擎 (权重: freq={self.stats.params["w_freq"]})' if len(preds) > 0 else '预测',
                },
                'reverse': preds[1] if len(preds) > 1 else {
                    'front': sorted(random.sample(range(1, 36), 5)),
                    'back': [1, 2],
                }
            })
        
        else:
            # hybrid: AI排名 + 统计引擎融合（含 XGBoost 辅助）
            from ai_client import call_deepseek, AI_SYSTEM_PROMPT
            
            # ===== XGBoost 引擎（如果已训练）=====
            xgb_front_boost = {}
            xgb_back_boost = {}
            if self._xgb and self._xgb_trained:
                try:
                    xf, xb = self._xgb.get_scores(history)
                    # XGBoost 分数缩放到 0-0.3 范围
                    max_xf = max(xf.values()) if xf else 0.5
                    max_xb = max(xb.values()) if xb else 0.5
                    for n in xf:
                        xgb_front_boost[n] = (xf[n] / max(max_xf, 0.01)) * 0.3
                    for n in xb:
                        xgb_back_boost[n] = (xb[n] / max(max_xb, 0.01)) * 0.3
                except Exception:
                    pass  # XGBoost 失败不阻塞主流程
            
            # 构建带教训注入的 prompt
            user_prompt = self.build_ai_prompt(history, n_history=30)
            
            # 注入教训笔记的增强版 system prompt
            system_prompt_with_lessons = AI_SYSTEM_PROMPT  # base prompt
            
            raw = None
            ai_available = True
            for attempt in range(3):
                try:
                    raw = call_ai_func or call_deepseek(system_prompt_with_lessons, user_prompt)
                    break
                except Exception as e:
                    if attempt == 2:
                        ai_available = False
                    else:
                        time.sleep(2)
            
            ai_data = {}
            if raw and ai_available:
                try:
                    ai_data = json.loads(raw) if isinstance(raw, str) else raw
                except:
                    ai_available = False
            
            if not ai_available:
                result['model'] = 'Hermes v5 (AI offline, stats fallback)'
                result['analysis'] = {'summary': 'AI服务不可用，使用统计引擎'}
                preds = self.stats.predict(history, n=2)
                if preds:
                    result['prediction'] = {'front': preds[0]['front'], 'back': preds[0]['back'], 'reason': '统计引擎(备选)'}
                    result['reverse'] = preds[1] if len(preds) > 1 else {'front': [], 'back': []}
            else:
                # AI 成功，构建置信度分数
                ranked_f = ai_data.get('ranked_front', [])
                ranked_b = ai_data.get('ranked_back', [])
                ai_analysis = ai_data.get('analysis', {})
                
                ai_front_scores = {}
                for item in ranked_f:
                    num = item.get('num')
                    conf = item.get('confidence', 0.5)
                    if num:
                        ai_front_scores[num] = conf * 0.5
                
                ai_back_scores = {}
                for item in ranked_b:
                    num = item.get('num')
                    conf = item.get('confidence', 0.5)
                    if num:
                        ai_back_scores[num] = conf * 0.5
                
                # 填充所有号码（未出现的给0）
                for n in range(1, 36):
                    if n not in ai_front_scores:
                        ai_front_scores[n] = 0.0
                for n in range(1, 13):
                    if n not in ai_back_scores:
                        ai_back_scores[n] = 0.0
                
                # 融合 AI + XGBoost 分数
                fused_front = {}
                for n in range(1, 36):
                    fused_front[n] = ai_front_scores.get(n, 0) + xgb_front_boost.get(n, 0)
                fused_back = {}
                for n in range(1, 13):
                    fused_back[n] = ai_back_scores.get(n, 0) + xgb_back_boost.get(n, 0)
                
                # 统计引擎用自适应权重 + AI+XGBoost boost
                preds = self.stats.predict(history, n=2, 
                    ai_front_scores=fused_front, ai_back_scores=fused_back)
                
                ranked_front_display = [
                    {'num': n, 'confidence': round(ai_front_scores.get(n, 0), 2)}
                    for n in sorted(range(1, 36), key=lambda x: -ai_front_scores.get(x, 0))
                ]
                ranked_back_display = [
                    {'num': n, 'confidence': round(ai_back_scores.get(n, 0), 2)}
                    for n in sorted(range(1, 13), key=lambda x: -ai_back_scores.get(x, 0))
                ]
                
                # 标记 XGBoost 参与
                xgb_label = ' + XGBoost' if (xgb_front_boost and max(xgb_front_boost.values()) > 0.01) else ''
                result.update({
                    'model': f'Hermes v5 (Adaptive + AI with Memory{xgb_label})',
                    'analysis': ai_analysis,
                    'ranked_front': ranked_front_display,
                    'ranked_back': ranked_back_display,
                    'prediction': {
                        'front': preds[0]['front'] if preds else [],
                        'back': preds[0]['back'] if preds else [],
                        'reason': 'AI排名(含历史教训参考) + 自适应Hermes统计引擎融合',
                    },
                    'reverse': preds[1] if preds and len(preds) > 1 else {
                        'front': sorted(random.sample(range(1, 36), 5)),
                        'back': [2, 9],
                    }
                }) if preds else result
        
        # 记录本次预测
        self.records['records'].append({
            'period': next_period,
            'timestamp': result['generated_at'],
            'strategy': strategy,
            'model': result.get('model', ''),
            'prediction': {
                'front': result.get('prediction', {}).get('front', []),
                'back': result.get('prediction', {}).get('back', []),
            },
            'reverse': {
                'front': result.get('reverse', {}).get('front', []),
                'back': result.get('reverse', {}).get('back', []),
            }
        })
        if len(self.records['records']) > 100:
            self.records['records'] = self.records['records'][-100:]
        self._save_records()
        
        return result
    
    def self_learn(self, prediction_record, actual, verbose=True):
        """
        核心学习方法：开奖后反馈学习
        
        参数:
          prediction_record: dict - 之前的预测结果（含 prediction 和 reverse）
          actual: dict - 实际开奖结果 {period, front:[], back:[]}
        
        执行:
          1. 记录偏差
          2. 提取教训
          3. 优化统计权重
          4. 记录策略表现
        """
        if verbose:
            print(f'\n{"="*50}')
            print(f'[Self-Learn] 开始学习 - {self.kind_label} 第{actual.get("period","?")}期')
            print(f'{"="*50}')
        
        # 1. 计算命中率
        pred_f = set(prediction_record.get('prediction', {}).get('front', []))
        pred_b = set(prediction_record.get('prediction', {}).get('back', []))
        actual_f = set(actual.get('front', []))
        actual_b = set(actual.get('back', []))
        fh = len(pred_f & actual_f)
        bh = len(pred_b & actual_b)
        
        if verbose:
            print(f'  预测: {list(pred_f)}+{list(pred_b)}')
            print(f'  实际: {list(actual_f)}+{list(actual_b)}')
            print(f'  命中: 前区{fh}/5  后区{bh}/2')
        
        # 2. 提取教训
        lessons = self.lessons.extract(prediction_record, actual, self.kind_label)
        if lessons:
            if verbose:
                print(f'  [教训] 提取 {len(lessons)} 条教训:')
                for l in lessons:
                    print(f'    • [{l["type"]}] {l["lesson"]}')
        
        # 3. 优化统计权重（滚动窗口调参）
        history = load_history(self.kind)
        if len(history) >= 35:
            if verbose:
                print(f'  [优化] 开始滚动调参（基于最近30期数据）...')
            self.stats.optimize_weights(history, window=30, verbose=verbose)
        else:
            if verbose:
                print(f'  [优化] 数据不足({len(history)}期)，跳过调参')
        
        # 4. 训练 XGBoost 引擎
        if len(history) >= 60:
            if not self._xgb_trained:
                # 第一次训练
                try:
                    from hermes_xgb import XGBEngine
                    self._xgb = XGBEngine(self.kind)
                    self._xgb_trained = self._xgb.train(history, silent=not verbose)
                    if verbose:
                        print(f'  [XGB] {"训练完成" if self._xgb_trained else "训练失败"}')
                except Exception as e:
                    if verbose:
                        print(f'  [XGB] 训练异常: {e}')
            else:
                # 增量重训练（每学习 5 期重训练一次）
                total = self.meta.meta.get('strategy_performance', {}).get('hybrid', {}).get('total', 0)
                if total % 5 == 0 and self._xgb:
                    try:
                        self._xgb_trained = self._xgb.train(history, silent=not verbose)
                        if verbose:
                            print(f'  [XGB] 增量重训练完成')
                    except:
                        pass
        
        # 5. 记录策略表现
        strategy = prediction_record.get('strategy', 'hybrid')
        self.meta.record_result(strategy, fh, bh, actual.get('period'))
        
        # 6. 评估是否需要切换策略
        new_strat, switched = self.meta.evaluate_and_switch()
        if switched and verbose:
            print(f'  [元学习] 切换策略: {strategy} → {new_strat}')
        
        if verbose:
            perf = self.lessons.get_performance_summary()
            print(f'  [累计] 共{perf["total"]}期 | 前区平均{perf["avg_front"]}/5 | 后区平均{perf["avg_back"]}/2 | 综合命中率{perf["any_hit_rate"]}%')
            print(f'  [元学习] 当前策略: {self.meta.get_status()["current_strategy"]}')
            print(f'{"="*50}\n')
        
        return {
            'front_hits': fh,
            'back_hits': bh,
            'lessons': len(lessons),
            'weights_optimized': True,
            'strategy_switched': switched,
        }
    
    def get_learning_status(self):
        """获取完整学习状态"""
        return {
            'stats_params': self.stats.params,
            'weights_path': str(self.stats.params_path),
            'lessons_count': len(self.lessons.lessons['lessons']),
            'recent_errors': len(self.lessons.lessons['recent_errors']),
            'performance': self.lessons.get_performance_summary(),
            'meta': self.meta.get_status(),
            'total_predictions': len(self.records['records']),
        }


# ============================================================
# 回测验证
# ============================================================

def backtest_adaptive(history, start_idx=50, n_test=20, verbose=True):
    """
    回测自适应学习系统的性能
    - 模拟开奖后自动学习
    - 看经过学习后命中率是否提升
    """
    engine = SelfLearningEngine('dlt')
    call_history = []
    
    results = []
    
    for i in range(start_idx, min(start_idx + n_test, len(history))):
        hist = history[:i]
        actual = history[i]
        
        if verbose:
            print(f'\n--- 回测第{actual["period"]}期 (训练数据: {len(hist)}期) ---')
        
        # 预测（纯统计，避免 API 调用开销）
        preds = engine.stats.predict(hist, n=2)
        if not preds:
            continue
        
        prediction_record = {
            'prediction': {'front': preds[0]['front'], 'back': preds[0]['back']},
            'reverse': {'front': preds[1]['front'] if len(preds) > 1 else [], 'back': preds[1]['back'] if len(preds) > 1 else []},
        }
        
        pred_f = set(preds[0]['front'])
        pred_b = set(preds[0]['back'])
        actual_f = set(actual.get('front', []))
        actual_b = set(actual.get('back', []))
        fh = len(pred_f & actual_f)
        bh = len(pred_b & actual_b)
        
        results.append({
            'period': actual['period'],
            'index': i,
            'front': list(pred_f),
            'back': list(pred_b),
            'actual_front': list(actual_f),
            'actual_back': list(actual_b),
            'front_hits': fh,
            'back_hits': bh,
        })
        
        if verbose:
            print(f'  预测:{list(pred_f)}+{list(pred_b)} 实际:{list(actual_f)}+{list(actual_b)} 命中:{fh}+{bh}')
        
        # 学习（自动调参）
        engine.self_learn(prediction_record, actual, verbose=False)
    
    # 汇总：比较训练早期 vs 后期的性能
    n = len(results)
    if n >= 10:
        early = results[:n//2]
        late = results[n//2:]
        early_f = sum(r['front_hits'] for r in early) / len(early)
        early_b = sum(r['back_hits'] for r in early) / len(early)
        late_f = sum(r['front_hits'] for r in late) / len(late)
        late_b = sum(r['back_hits'] for r in late) / len(late)
        
        print(f'\n{"="*50}')
        print(f'[回测结果] {n}期 | 自适应学习效果')
        print(f'{"="*50}')
        print(f'  前{n//2}期: 前区{early_f:.3f}/5 后区{early_b:.3f}/2')
        print(f'  后{n//2}期: 前区{late_f:.3f}/5 后区{late_b:.3f}/2')
        print(f'  改进: 前区{late_f-early_f:+.3f} 后区{late_b-early_b:+.3f}')
    
    return results


if __name__ == '__main__':
    import sys
    
    print('Hermes Self-Learning Engine v5')
    print('=' * 50)
    
    dlt = load_history('dlt')
    print(f'大乐透数据: {len(dlt)} 期')
    
    # 测试回测
    if len(sys.argv) > 1 and sys.argv[1] == 'backtest':
        print('\n开始回测...')
        results = backtest_adaptive(dlt, start_idx=max(30, len(dlt)-40), n_test=30)
        
        # 保存回测结果
        output = DATA_DIR / 'adaptive_backtest_results.json'
        with open(output, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        print(f'\n回测结果保存至: {output}')
    
    else:
        # 显示学习状态
        engine = SelfLearningEngine('dlt')
        status = engine.get_learning_status()
        print(f'\n学习状态:')
        print(f'  统计引擎权重: {status["stats_params"]}')
        print(f'  积累教训: {status["lessons_count"]} 条')
        print(f'  累计预测: {status["total_predictions"]} 期')
        perf = status['performance']
        print(f'  平均表现: F={perf["avg_front"]}/5 B={perf["avg_back"]}/2')
        meta = status['meta']
        print(f'  当前策略: {meta["current_strategy"]}')
