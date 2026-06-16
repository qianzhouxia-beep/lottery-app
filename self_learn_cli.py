#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Hermes v5 Self-Learning CLI
============================
交互式自主学习命令行工具

用法:
  python self_learn_cli.py status         查看当前学习状态
  python self_learn_cli.py predict        生成预测（含自学习上下文）
  python self_learn_cli.py learn <期号> <前区> <后区>   导入开奖结果并学习
  python self_learn_cli.py backtest       回测自适应学习效果
  python self_learn_cli.py optimize       手动触发权重优化
"""

import sys, io, json, os
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stdin = io.TextIOWrapper(sys.stdin.buffer, encoding='utf-8')

from pathlib import Path
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'

# ============================================================
# 工具函数
# ============================================================

def print_banner(text):
    """打印分隔线"""
    print()
    print('=' * 55)
    print(f'  {text}')
    print('=' * 55)

def print_json(data, indent=2):
    """打印格式化的 JSON"""
    print(json.dumps(data, ensure_ascii=False, indent=indent))

# ============================================================
# 命令实现
# ============================================================

def cmd_status(kind='dlt'):
    """查看学习状态"""
    from hermes_learner import SelfLearningEngine
    
    print_banner(f'【{("大乐透" if kind=="dlt" else "双色球")}】学习状态')
    
    engine = SelfLearningEngine(kind)
    status = engine.get_learning_status()
    
    print(f'\n📊 累计预测: {status["total_predictions"]} 期')
    print(f'📚 积累教训: {status["lessons_count"]} 条')
    print(f'📝 近期错误记录: {status["recent_errors"]} 条')
    
    perf = status['performance']
    print(f'\n📈 预测表现:')
    print(f'  前区平均: {perf["avg_front"]}/5')
    print(f'  后区平均: {perf["avg_back"]}/2')
    print(f'  综合命中率(有任意命中): {perf["any_hit_rate"]}%')
    
    print(f'\n⚙️  统计引擎权重:')
    w = status['stats_params']
    print(f'  频率权重: {w["w_freq"]}  重复权重: {w["w_repeat"]}')
    print(f'  区间权重: {w["w_zone"]}  大号权重: {w["w_large"]}')
    print(f'  后区权重: {w["w_back"]}')
    print(f'  AI前区影响: {w["w_ai_front"]}  AI后区影响: {w["w_ai_back"]}')
    
    meta = status['meta']
    print(f'\n🎯 元学习 (当前策略: {meta["current_strategy"]}):')
    for s, p in meta.items():
        if isinstance(p, dict) and 'total' in p:
            print(f'  {s}: 共{p["total"]}期 平均F={p["avg_front"]}/5 B={p["avg_back"]}/2')
    
    # 最新教训
    print('\n📖 最近教训:')
    lessons_path = DATA_DIR / f'{kind}_lessons.json'
    if lessons_path.exists():
        with open(lessons_path, 'r', encoding='utf-8') as f:
            lessons = json.load(f)
        recent = lessons.get('lessons', [])[-3:]
        for l in recent:
            print(f'  • [{l["type"]}] {l["lesson"]}')
    
    print()


def cmd_predict(kind='dlt'):
    """生成带自学习上下文的预测"""
    from hermes_learner import SelfLearningEngine, load_history
    from api_server import call_deepseek, AI_SYSTEM_PROMPT
    
    print_banner(f'【{("大乐透" if kind=="dlt" else "双色球")}】Hermes v5 自学习预测')
    
    history = load_history(kind)
    print(f'📊 历史数据: {len(history)} 期')
    
    engine = SelfLearningEngine(kind)
    
    # 显示学习上下文
    perf = engine.lessons.get_performance_summary()
    if perf['total'] > 0:
        print(f'📈 学习记录: 共{perf["total"]}期 | 前区{perf["avg_front"]}/5 | 后区{perf["avg_back"]}/2')
    
    recent_lessons = engine.lessons.lessons['lessons'][-3:]
    if recent_lessons:
        print(f'📖 历史教训 ({len(recent_lessons)}条):')
        for l in recent_lessons:
            print(f'  • [{l["type"]}] {l["lesson"]}')
    
    print(f'⚙️  当前引擎权重: ')
    w = engine.stats.params
    print(f'  频率{w["w_freq"]} 重复{w["w_repeat"]} 区间{w["w_zone"]} 大号{w["w_large"]} 后区{w["w_back"]}')
    
    print(f'\n🤖 正在调用 AI（含教训注入）...')
    
    result = engine.predict(
        history,
        strategy='hybrid',
        call_ai_func=lambda s, u: call_deepseek(s, u)
    )
    
    if 'error' in result:
        print(f'\n❌ 错误: {result["error"]}')
        return
    
    print(f'\n✅ 预测完成!')
    print(f'  期号: {result.get("for_period", "?")}')
    print(f'  模型: {result.get("model", "?")}')
    print(f'  策略: {result.get("strategy", "?")}')
    
    pred = result.get('prediction', {})
    rev = result.get('reverse', {})
    
    print(f'\n🎯 正选: {pred.get("front", [])} + {pred.get("back", [])}')
    print(f'  理由: {pred.get("reason", "")}')
    print(f'\n🔄 反选: {rev.get("front", [])} + {rev.get("back", [])}')
    print(f'  理由: {rev.get("reason", "")}')
    
    analysis = result.get('analysis', {})
    if analysis:
        print(f'\n📊 AI分析:')
        hf = analysis.get('hot_front', [])
        cf = analysis.get('cold_front', [])
        hb = analysis.get('hot_back', [])
        cb = analysis.get('cold_back', [])
        if hf: print(f'  热号(前区): {hf[:8]}')
        if cf: print(f'  冷号(前区): {cf[:5]}')
        if hb: print(f'  热号(后区): {hb[:5]}')
        if cb: print(f'  冷号(后区): {cb[:3]}')
    
    # 保存预测记录
    records_path = DATA_DIR / f'{kind}_prediction_records.json'
    print(f'\n💾 预测已记录至: {records_path}')
    print(f'\n💡 开奖后导入实际结果:')
    print(f'  python self_learn_cli.py learn {result.get("for_period", "?")} 03 15 20 29 31 01 12')


def cmd_learn(kind, period, front_str, back_str):
    """导入开奖结果并触发学习"""
    from hermes_learner import SelfLearningEngine, load_history
    from api_server import call_deepseek
    
    print_banner(f'【{("大乐透" if kind=="dlt" else "双色球")}】第{period}期 - 自我学习')
    
    # 解析号码
    try:
        front = [int(x) for x in front_str.replace(',', ' ').split()]
        back = [int(x) for x in back_str.replace(',', ' ').split()]
    except:
        print('❌ 号码格式错误，请用空格或逗号分隔')
        return
    
    print(f'📥 实际开奖: 前区{front} 后区{back}')
    
    engine = SelfLearningEngine(kind)
    
    # 查找对应的预测记录
    prediction_record = None
    for r in reversed(engine.records['records']):
        if r.get('period') == period:
            prediction_record = {
                'prediction': r.get('prediction', {}),
                'reverse': r.get('reverse', {}),
                'strategy': r.get('strategy', 'hybrid'),
            }
            break
    
    if prediction_record:
        print(f'📤 预测记录: 正选{prediction_record["prediction"]} 反选{prediction_record["reverse"]}')
        fh = len(set(prediction_record['prediction'].get('front', [])) & set(front))
        bh = len(set(prediction_record['prediction'].get('back', [])) & set(back))
        print(f'🎯 命中: 前区{fh}/5 后区{bh}/2')
    else:
        print('⚠️  未找到对应的预测记录，使用空记录继续学习')
        prediction_record = {
            'prediction': {'front': [], 'back': []},
            'reverse': {'front': [], 'back': []},
            'strategy': 'hybrid',
        }
    
    print('\n🧠 正在学习...')
    
    actual = {'period': period, 'front': front, 'back': back}
    result = engine.self_learn(prediction_record, actual, verbose=True)
    
    print(f'\n✅ 学习完成!')
    print(f'  权重已优化: {result.get("weights_optimized", False)}')
    print(f'  策略已切换: {result.get("strategy_switched", False)}')
    
    w = engine.stats.params
    print(f'  新权重: freq={w["w_freq"]} repeat={w["w_repeat"]} zone={w["w_zone"]} '
          f'large={w["w_large"]} back={w["w_back"]}')
    
    print(f'\n💡 下次预测时将自动使用优化后的权重和新的教训笔记!')


def cmd_backtest(kind='dlt', n_test=20):
    """回测自适应学习效果"""
    from hermes_learner import backtest_adaptive, load_history
    
    print_banner(f'【{("大乐透" if kind=="dlt" else "双色球")}】自适应学习回测')
    
    history = load_history(kind)
    
    if len(history) < n_test + 30:
        print(f'❌ 数据不足: 需要至少 {n_test + 30} 期，当前 {len(history)} 期')
        return
    
    start_idx = len(history) - n_test - 10
    print(f'📊 使用 {start_idx} 期训练 + {n_test} 期回测')
    print(f'⏳ 回测中（不调用 AI，纯统计引擎）...')
    
    results = backtest_adaptive(history, start_idx=start_idx, n_test=n_test, verbose=True)
    
    # 保存结果
    output = DATA_DIR / f'{kind}_adaptive_backtest.json'
    with open(output, 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=2)
    print(f'\n📁 回测结果已保存: {output}')


def cmd_optimize(kind='dlt'):
    """手动触发权重优化"""
    from hermes_learner import AdaptiveHermesEngine, load_history
    
    print_banner(f'【{("大乐透" if kind=="dlt" else "双色球")}】手动权重优化')
    
    history = load_history(kind)
    print(f'📊 历史数据: {len(history)} 期')
    
    if len(history) < 35:
        print(f'❌ 数据不足: 需要至少 35 期')
        return
    
    engine = AdaptiveHermesEngine(kind)
    print('⏳ 正在网格搜索最优权重...')
    
    new_params = engine.optimize_weights(history, window=30, verbose=True)
    
    print(f'\n✅ 优化完成!')
    print(f'  新权重: freq={new_params["w_freq"]} repeat={new_params["w_repeat"]} '
          f'zone={new_params["w_zone"]} large={new_params["w_large"]} '
          f'back={new_params["w_back"]}')
    print(f'  AI权重: front={new_params["w_ai_front"]} back={new_params["w_ai_back"]}')
    print(f'  已保存至: {engine.params_path}')


# ============================================================
# 交互模式
# ============================================================

def interactive_mode():
    """交互式模式"""
    print_banner('Hermes v5 自学习系统 - 交互模式')
    print('命令: status / predict / learn / optimize / backtest / quit')
    
    kind = 'dlt'
    
    while True:
        try:
            cmd = input(f'\n[{kind}] > ').strip().lower()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        
        if not cmd:
            continue
        
        if cmd in ('q', 'quit', 'exit'):
            break
        
        elif cmd.startswith('kind '):
            kind = cmd.split()[1]
            print(f'切换到 {("大乐透" if kind=="dlt" else "双色球")}')
        
        elif cmd == 'status':
            cmd_status(kind)
        
        elif cmd == 'predict':
            cmd_predict(kind)
        
        elif cmd.startswith('learn '):
            parts = cmd.split(maxsplit=3)
            if len(parts) >= 4:
                cmd_learn(kind, parts[1], parts[2], parts[3])
            else:
                print('用法: learn 期号 前区号码 后区号码')
                print('示例: learn 26066 03 15 20 29 31 01 12')
        
        elif cmd == 'optimize':
            cmd_optimize(kind)
        
        elif cmd == 'backtest':
            cmd_backtest(kind, 20)
        
        else:
            print('未知命令。可用: status / predict / learn / optimize / backtest / quit')


# ============================================================
# 入口
# ============================================================

if __name__ == '__main__':
    if len(sys.argv) < 2:
        interactive_mode()
        sys.exit(0)
    
    cmd = sys.argv[1]
    kind = sys.argv[2] if len(sys.argv) > 2 and sys.argv[2] in ('dlt', 'ssq') else 'dlt'
    
    if cmd == 'status':
        cmd_status(kind)
    elif cmd == 'predict':
        cmd_predict(kind)
    elif cmd == 'learn' and len(sys.argv) >= 5:
        period = sys.argv[2] if sys.argv[2] in ('dlt', 'ssq') else sys.argv[2]
        front_str = sys.argv[3]
        back_str = sys.argv[4]
        cmd_kind = 'dlt'
        cmd_learn(cmd_kind, period, front_str, back_str)
    elif cmd == 'learn' and len(sys.argv) >= 5:
        idx = 2
        if sys.argv[2] in ('dlt', 'ssq'):
            cmd_kind = sys.argv[2]
            idx = 3
        else:
            cmd_kind = 'dlt'
            idx = 2
        if len(sys.argv) >= idx + 3:
            cmd_learn(cmd_kind, sys.argv[idx], sys.argv[idx+1], sys.argv[idx+2])
    elif cmd == 'backtest':
        cmd_backtest(kind)
    elif cmd == 'optimize':
        cmd_optimize(kind)
    elif cmd == 'interactive':
        interactive_mode()
    else:
        print(f'用法: python {sys.argv[0]} <命令> [参数...]')
        print(f'命令: status / predict / learn / backtest / optimize / interactive')
        print()
        print(f'示例:')
        print(f'  python {sys.argv[0]} status')
        print(f'  python {sys.argv[0]} predict')
        print(f'  python {sys.argv[0]} learn 26066 03 15 20 29 31 01 12')
        print(f'  python {sys.argv[0]} optimize')
        print(f'  python {sys.argv[0]} backtest')
        print(f'  python {sys.argv[0]} interactive')
