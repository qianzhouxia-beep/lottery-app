#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Auto Learner - 自动学习守护（Hermes v5 自治核心）
===============================================
在 API 服务器后台运行，自动完成：

1. 检测开奖时间 → 2. 抓取最新数据 → 3. 对比上次学习期
→ 4. 触发自学习 → 5. 优化权重 → 6. 下次预测直接使用学习成果

开奖安排：
  大乐透 (dlt): 周一、三、六 20:25
  双色球 (ssq): 周二、四、日 20:30
"""
import json, time, sys, io, os, threading
from pathlib import Path
from datetime import datetime, timedelta
from collections import defaultdict

# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

# ============================================================
# 开奖时间配置
# ============================================================

DRAW_SCHEDULE = {
    'dlt': {
        'label': '大乐透',
        'weekdays': [0, 2, 5],      # 周一(0)、周三(2)、周六(5)
        'draw_hour': 20,            # 北京时区
        'draw_minute': 25,
        'fetch_delay_min': 10,      # 开奖后等10分钟再抓取（确保数据已发布）
    },
    'ssq': {
        'label': '双色球',
        'weekdays': [1, 3, 6],      # 周二(1)、周四(3)、周日(6)
        'draw_hour': 20,
        'draw_minute': 30,
        'fetch_delay_min': 10,
    }
}

# ============================================================
# 学习记录
# ============================================================

class LearnTracker:
    """跟踪学习进度，避免重复学习"""
    
    def __init__(self, kind='dlt'):
        self.kind = kind
        self.track_path = DATA_DIR / f'{kind}_auto_learn_tracker.json'
        self.state = self._load()
        
        # 从系统时区推算开奖时间
        self.config = DRAW_SCHEDULE[kind]
    
    def _load(self):
        if self.track_path.exists():
            with open(self.track_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        return {
            'last_learned_period': None,
            'last_learned_time': None,
            'last_checked_time': None,
            'total_auto_learns': 0,
            'history': [],
        }
    
    def _save(self):
        with open(self.track_path, 'w', encoding='utf-8') as f:
            json.dump(self.state, f, ensure_ascii=False, indent=2)
    
    def is_draw_day(self):
        """检查今天是否开奖日"""
        today = datetime.now().weekday()
        return today in self.config['weekdays']
    
    def is_after_draw(self):
        """检查是否已过开奖时间（含延迟）"""
        now = datetime.now()
        delay = self.config['fetch_delay_min']
        draw_time = now.replace(hour=self.config['draw_hour'], 
                                minute=self.config['draw_minute'] + delay, 
                                second=0, microsecond=0)
        return now >= draw_time
    
    def should_check(self):
        """判断是否应该检查新数据"""
        # 已经检查过的就不重复检查（避免每5分钟重复触发）
        now = datetime.now()
        if self.state.get('last_checked_time'):
            last = datetime.fromisoformat(self.state['last_checked_time'])
            if (now - last).total_seconds() < 3600:  # 1小时内不重复检查
                return False
        return self.is_draw_day() and self.is_after_draw()
    
    def mark_checked(self):
        self.state['last_checked_time'] = datetime.now().isoformat()
        self._save()
    
    def mark_learned(self, period, front_hits, back_hits):
        self.state['last_learned_period'] = period
        self.state['last_learned_time'] = datetime.now().isoformat()
        self.state['total_auto_learns'] += 1
        self.state['history'].append({
            'period': period,
            'time': datetime.now().isoformat(),
            'front_hits': front_hits,
            'back_hits': back_hits,
        })
        if len(self.state['history']) > 50:
            self.state['history'] = self.state['history'][-50:]
        self._save()
    
    def get_status(self):
        return {
            'last_learned_period': self.state['last_learned_period'],
            'last_learned_time': self.state['last_learned_time'],
            'total_auto_learns': self.state['total_auto_learns'],
            'is_draw_day': self.is_draw_day(),
            'has_checked_today': self.state.get('last_checked_time', ''),
        }


# ============================================================
# 自动学习核心
# ============================================================

class AutoLearner:
    """
    自动学习核心
    
    使用方式:
      learner = AutoLearner('dlt')
      learner.start()    # 启动后台线程
    """
    
    def __init__(self, kind='dlt'):
        self.kind = kind
        self.config = DRAW_SCHEDULE[kind]
        self.tracker = LearnTracker(kind)
        self._running = False
        self._thread = None
        self._log = []
    
    def log(self, msg):
        timestamp = datetime.now().strftime('%H:%M:%S')
        entry = f'[{timestamp}] [{self.config["label"]}] {msg}'
        self._log.append(entry)
        if len(self._log) > 100:
            self._log = self._log[-100:]
        print(entry)
    
    def fetch_and_learn(self):
        """
        核心方法：抓取最新数据并在需要时触发学习
        返回是否执行了学习
        """
        try:
            # 1. 加载数据模块
            from data_fetcher import update_dlt, update_ssq
            from hermes_learner import SelfLearningEngine, load_history
            
            # 2. 获取最新数据
            if self.kind == 'dlt':
                update_dlt()
            else:
                update_ssq()
            
            history = load_history(self.kind)
            if not history:
                self.log('无历史数据')
                return False
            
            latest_period = history[-1].get('period', '')
            latest = history[-1]
            
            # 3. 如果和上次学习的期号相同 → 跳过
            if self.tracker.state['last_learned_period'] == latest_period:
                self.log(f'已学习过第{latest_period}期，跳过')
                return False
            
            # 4. 加载学习引擎
            engine = SelfLearningEngine(self.kind)
            
            # 5. 查找匹配的预测记录
            prediction_record = None
            for r in reversed(engine.records['records']):
                if r.get('period') == latest_period:
                    prediction_record = {
                        'prediction': r.get('prediction', {}),
                        'reverse': r.get('reverse', {}),
                        'strategy': r.get('strategy', 'hybrid'),
                    }
                    break
            
            if not prediction_record and engine.records['records']:
                # 用最新的预测记录试试
                last = engine.records['records'][-1]
                prediction_record = {
                    'prediction': last.get('prediction', {}),
                    'reverse': last.get('reverse', {}),
                    'strategy': last.get('strategy', 'hybrid'),
                }
            
            if not prediction_record:
                prediction_record = {
                    'prediction': {'front': [], 'back': []},
                    'reverse': {'front': [], 'back': []},
                    'strategy': 'hybrid',
                }
            
            front = latest.get('front', [])
            back = latest.get('back', [])
            
            if not front or not back:
                self.log(f'第{latest_period}期数据不完整')
                return False
            
            # 6. 计算命中率
            pred_f = set(prediction_record.get('prediction', {}).get('front', []))
            pred_b = set(prediction_record.get('prediction', {}).get('back', []))
            fh = len(pred_f & set(front))
            bh = len(pred_b & set(back))
            
            # 7. 执行学习（静默模式）
            actual = {'period': latest_period, 'front': front, 'back': back}
            result = engine.self_learn(prediction_record, actual, verbose=False)
            
            # 8. 记录
            self.tracker.mark_learned(latest_period, fh, bh)
            
            # 9. 显示结果
            self.log(f'第{latest_period}期: 抓取+学习完成 | '
                    f'前区{fh}/5 后区{bh}/2 | '
                    f'权重已优化 | '
                    f'教训{result.get("lessons", 0)}条')
            
            return True
            
        except Exception as e:
            self.log(f'自动学习失败: {e}')
            import traceback
            self.log(traceback.format_exc()[-200:])
            return False
    
    def check_and_learn(self):
        """判断是否需要学习 → 是则执行"""
        if not self.tracker.should_check():
            return
        
        self.tracker.mark_checked()
        self.log('开奖日已过，检查并学习...')
        self.fetch_and_learn()
    
    def _run_loop(self):
        """后台循环（每 30 分钟检查一次）"""
        self.log(f'自动学习守护已启动，每30分钟检查开奖状态')
        self.log(f'开奖日: {self.config["weekdays"]} 开奖时间: {self.config["draw_hour"]}:{self.config["draw_minute"]:02d}')
        
        while self._running:
            try:
                self.check_and_learn()
            except Exception as e:
                self.log(f'检查异常: {e}')
            
            # 每 1800 秒 = 30 分钟检查一次
            for _ in range(180):
                if not self._running:
                    break
                time.sleep(10)
    
    def start(self):
        """启动后台学习线程"""
        if self._running:
            return
        
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, 
                                        name=f'AutoLearner-{self.kind}',
                                        daemon=True)
        self._thread.start()
        self.log('后台线程已启动')
    
    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
    
    def get_logs(self, n=20):
        return self._log[-n:]
    
    def get_status(self):
        return {
            'kind': self.kind,
            'running': self._running,
            'tracker': self.tracker.get_status(),
        }


# ============================================================
# 双品种管理器
# ============================================================

class AutoLearnerManager:
    """同时管理大乐透和双色球的自动学习"""
    
    def __init__(self):
        self.dlt = AutoLearner('dlt')
        self.ssq = AutoLearner('ssq')
    
    def start_all(self):
        self.dlt.start()
        self.ssq.start()
        print('[AutoLearner] 双品种自动学习守护已启动')
        sched = DRAW_SCHEDULE
        print(f'  大乐透: 周{["一","三","六"]} 20:25+10min')
        print(f'  双色球: 周{["二","四","日"]} 20:30+10min')
    
    def stop_all(self):
        self.dlt.stop()
        self.ssq.stop()
    
    def get_status(self):
        return {
            'dlt': self.dlt.get_status(),
            'ssq': self.ssq.get_status(),
        }
    
    def get_logs(self):
        return self.dlt.get_logs() + [''] + self.ssq.get_logs()


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='自动学习守护')
    parser.add_argument('--once', action='store_true', help='只执行一次检查')
    parser.add_argument('--kind', default='dlt', choices=['dlt', 'ssq', 'all'])
    
    args = parser.parse_args()
    
    if args.once:
        if args.kind == 'all':
            for k in ['dlt', 'ssq']:
                al = AutoLearner(k)
                al.check_and_learn()
        else:
            al = AutoLearner(args.kind)
            al.check_and_learn()
    else:
        print('Hermes v5 自动学习守护')
        print('=' * 40)
        
        manager = AutoLearnerManager()
        manager.start_all()
        
        try:
            while True:
                time.sleep(30)
        except KeyboardInterrupt:
            print('\n正在停止...')
            manager.stop_all()
            print('已停止')
