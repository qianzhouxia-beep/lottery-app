"""
Hermes AI 回测 - 用 DeepSeek 分析历史数据做预测
测试最近 30 期，看 AI 比随机强多少
"""
import json, time, io, sys
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import requests

# Config
with open(r'D:\AI\lottery-app\config.json', 'r') as f:
    CONFIG = json.load(f)

API_KEY = CONFIG['api_key']
BASE_URL = CONFIG['base_url']
MODEL = CONFIG['model']

SYSTEM_PROMPT = '''你是一个专业的大乐透彩票预测专家。
输出JSON格式：
{
  "analysis": {"hot_front":[...],"cold_front":[...],"hot_back":[...],"cold_back":[...],"zone_distribution":{"S":...,"M1":...,"M2":...,"M3":...},"sum_range":"...","trend":"..."},
  "prediction": {"front":[5个号],"back":[2个号],"reason":"..."},
  "reverse": {"front":[5个号],"back":[2个号],"reason":"..."}
}
只输出JSON。'''

def call_ai(system, user, max_tokens=600):
    resp = requests.post(f'{BASE_URL}/chat/completions',
        headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
        json={'model': MODEL, 'messages': [{'role':'system','content':system}, {'role':'user','content':user}], 'max_tokens': max_tokens, 'temperature': 0.3},
        timeout=30)
    return resp.json()['choices'][0]['message']['content']

def analyze_recent(history, n=30):
    lines = []
    for d in history[-n:]:
        f = ','.join(str(x) for x in d['front'])
        b = ','.join(str(x) for x in d['back'])
        lines.append(f"{d['period']}:[{f}]+[{b}]")
    return '\n'.join(reversed(lines[-n:]))

def dlt_prize(front_hits, back_hits):
    if front_hits == 5 and back_hits == 2: return 1
    if front_hits == 5 and back_hits == 1: return 2
    if front_hits == 5: return 3
    if front_hits == 4 and back_hits == 2: return 4
    if front_hits == 4 and back_hits == 1: return 5
    if front_hits == 3 and back_hits == 2: return 6
    if front_hits == 3: return 7
    if front_hits == 2 and back_hits == 2: return 8
    if front_hits == 2 and back_hits == 1: return 9
    if front_hits == 1 and back_hits == 2: return 9
    if front_hits == 0 and back_hits == 2: return 9
    return 0

print('Loading data...')
with open(r'D:\AI\lottery-app\data\dlt_history_full.json', 'r', encoding='utf-8') as f:
    dlt = json.load(f)
print(f'DLT: {len(dlt)} periods, {dlt[0]["period"]} -> {dlt[-1]["period"]}')

# Backtest: use first 486 periods (training), test on last 30
test_start = len(dlt) - 30  # last 30 periods
print(f'\n===== AI Backtest: {test_start} periods training, 30 periods test =====')

results = []
for i in range(test_start, len(dlt)):
    hist = dlt[:i]
    actual = dlt[i]
    
    data_str = analyze_recent(hist, 30)
    user = f'分析以下30期大乐透数据，预测下一期：\n{data_str}\n\n输出JSON。'
    
    try:
        raw = call_ai(SYSTEM_PROMPT, user)
        result = json.loads(raw)
        
        pred_front = set(result.get('prediction', {}).get('front', []))
        pred_back = set(result.get('prediction', {}).get('back', []))
        actual_front = set(actual['front'])
        actual_back = set(actual['back'])
        
        fh = len(pred_front & actual_front)
        bh = len(pred_back & actual_back)
        tier = dlt_prize(fh, bh)
        
        results.append({
            'period': actual['period'],
            'pred_f': list(pred_front),
            'pred_b': list(pred_back),
            'actual_f': actual['front'],
            'actual_b': actual['back'],
            'fh': fh, 'bh': bh, 'tier': tier
        })
        
        tier_str = f'T{tier}' if tier > 0 else '—'
        print(f'  {actual["period"]}: pred={list(pred_front)}+{list(pred_back)} '
              f'actual={actual["front"]}+{actual["back"]} '
              f'hits={fh}+{bh} prize={tier_str}')
        
        time.sleep(0.8)  # Rate limit
    
    except Exception as e:
        print(f'  Error at {actual["period"]}: {e}')
        continue

# Summary
avg_f = sum(r['fh'] for r in results) / len(results)
avg_b = sum(r['bh'] for r in results) / len(results)
any_prize = sum(1 for r in results if r['tier'] > 0)
prize_rate = any_prize / len(results)

print(f'\n===== AI Backtest Results =====')
print(f'Total tested: {len(results)} periods')
print(f'Avg front hits: {avg_f:.2f}/5 (random baseline: 0.71/5)')
print(f'Avg back hits:  {avg_b:.2f}/2 (random baseline: 0.33/2)')
print(f'Any prize:      {any_prize}/{len(results)} = {prize_rate*100:.1f}% (random ~2.4%)')

# Prize distribution
prize_dist = {}
for r in results:
    t = r['tier']
    prize_dist[t] = prize_dist.get(t, 0) + 1
print(f'Prize distribution: {prize_dist}')

# Save
with open(r'D:\AI\lottery-app\data\ai_backtest_results.json', 'w', encoding='utf-8') as f:
    json.dump(results, f, ensure_ascii=False, indent=2)
print('\nResults saved to data/ai_backtest_results.json')