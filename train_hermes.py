"""
Hermes v4 Training Analysis v3 - Full English Names
Avoids encoding issues with Chinese characters
"""
import json, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from collections import defaultdict
import itertools
import math

# ===== Load Data =====
with open(r'D:\AI\lottery-app\data\dlt_history.json', 'r', encoding='utf-8') as f:
    DLT = json.load(f)
with open(r'D:\AI\lottery-app\data\ssq_history.json', 'r', encoding='utf-8') as f:
    SSQ = json.load(f)

print(f'DLT: {len(DLT)} periods | SSQ: {len(SSQ)} periods')
print(f'DLT range: {DLT[0]["period"]} -> {DLT[-1]["period"]}')

# ===== DLT Prize Tier =====
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

# ===== Engine Helpers =====
def hot_cold(data, key='front', n=15):
    freq = defaultdict(float)
    for draw in data[-n:]:
        for num in draw[key]:
            freq[num] += 1.0
    total = sum(freq.values()) or 1
    return {num: c/total for num, c in freq.items()}

def repeat_prob(data, key='front', n=20):
    reprob = defaultdict(float)
    for i in range(len(data)-1, max(0, len(data)-n-1), -1):
        prev = set(data[i]['front'])
        curr = set(data[i-1]['front']) if i > 0 else set()
        for num in curr:
            if num in prev:
                reprob[num] += 1.0
    total = len(data[-n:])
    return {num: c/(total or 1) for num, c in reprob.items()}

def calc_zone_dist(data, key='front'):
    zones = defaultdict(int)
    for draw in data[-10:]:
        for num in draw[key]:
            if num <= 12: z = 'S'
            elif num <= 23: z = 'M1'
            elif num <= 29: z = 'M2'
            elif num <= 34: z = 'M3'
            else: z = 'L'
            zones[z] += 1
    return zones

# ===== Individual Engines =====
def engine_freq(data, key='front', n=15):
    return sorted(hot_cold(data, key, n).items(), key=lambda x: -x[1])

def engine_repeat(data, key='front', n=20):
    return sorted(repeat_prob(data, key, n).items(), key=lambda x: -x[1])

def engine_zone(data, key='front'):
    dist = calc_zone_dist(data, key)
    total = sum(dist.values()) or 1
    zone_nums = defaultdict(float)
    if key == 'front':
        zone_ranges = {'S': range(1,13), 'M1': range(13,24), 'M2': range(24,30), 'M3': range(30,35)}
    else:
        zone_ranges = {'S': range(1,7), 'M1': range(7,13)}
    for z, nums in zone_ranges.items():
        pct = dist.get(z, 0) / total
        for num in nums:
            zone_nums[num] = pct
    return sorted(zone_nums.items(), key=lambda x: -x[1])

# ===== Combined Predictor (tunable weights) =====
def combined_predict(history, params, n=5):
    ef = engine_freq(history, 'front', 15)
    er = engine_repeat(history, 'front', 20)
    ez = engine_zone(history, 'front')

    scores = defaultdict(float)
    for num in range(1, 36):
        f_score = next((s for i,s in ef if i==num), 0.0)
        r_score = next((s for i,s in er if i==num), 0.0)
        z_score = next((s for i,s in ez if i==num), 0.0)
        scores[num] = (
            f_score * params.get('w_freq', 1.0) +
            r_score * params.get('w_repeat', 0.5) +
            z_score * params.get('w_zone', 0.3) +
            (0.3 if num >= 25 else 0.0) * params.get('w_large', 0.3)
        )

    back_scores = {}
    eb = engine_freq(history, 'back', 15)
    for num in range(1, 13):
        b_score = next((s for i,s in eb if i==num), 0.0)
        back_scores[num] = b_score * params.get('w_back', 3.0)

    front_top = sorted(scores.items(), key=lambda x: -x[1])[:n]
    back_top = sorted(back_scores.items(), key=lambda x: -x[1])[:2]
    return [x[0] for x in front_top], [x[0] for x in back_top]

# ===== Backtest =====
def backtest_full(predict_fn, history, params, start_idx=10):
    front_hits, back_hits, prizes = [], [], []
    prize_tiers = defaultdict(int)
    for i in range(start_idx, len(history)):
        hist = history[:i]
        actual = history[i]
        fp, bp = predict_fn(hist, params)
        fh = len(set(fp) & set(actual['front']))
        bh = len(set(bp) & set(actual['back']))
        tier = dlt_prize(fh, bh)
        front_hits.append(fh)
        back_hits.append(bh)
        prizes.append(tier)
        prize_tiers[tier] += 1
    n = len(front_hits)
    exp_f, exp_b = 5.0/35.0, 2.0/12.0
    any_prize = sum(1 for p in prizes if p > 0)
    r = {
        'n': n,
        'avg_front': sum(front_hits)/n,
        'avg_back': sum(back_hits)/n,
        'front_hits': front_hits,
        'back_hits': back_hits,
        'any_prize': any_prize,
        'prize_rate': any_prize/n,
        'exp_front': exp_f,
        'exp_back': exp_b,
        'front_lift': (sum(front_hits)/n - exp_f)/exp_f*100,
        'back_lift': (sum(back_hits)/n - exp_b)/exp_b*100,
        'prize_tiers': dict(prize_tiers),
        'params': params,
    }
    return r

def print_result(label, r):
    print(f'{label}: F={r["avg_front"]:.3f}/5 (exp={r["exp_front"]:.3f} lift={r["front_lift"]:+.1f}%) | '
          f'B={r["avg_back"]:.3f}/2 (exp={r["exp_back"]:.3f} lift={r["back_lift"]:+.1f}%) | '
          f'Prize={r["any_prize"]}/{r["n"]} ({r["prize_rate"]*100:.1f}%)')

# ===== Individual Engine Evaluation =====
print('\n===== Individual Engine Evaluation (DLT, 21 test periods) =====')

configs = [
    ('[E1] Pure Frequency',      {'w_freq':1.0,'w_repeat':0,'w_zone':0,'w_large':0,'w_back':1.0}),
    ('[E2] Repeat Probability',   {'w_freq':0,'w_repeat':1.0,'w_zone':0,'w_large':0,'w_back':1.0}),
    ('[E3] Zone Distribution',    {'w_freq':0,'w_repeat':0,'w_zone':1.0,'w_large':0,'w_back':1.0}),
    ('[E4] Large Number (>25)',  {'w_freq':0,'w_repeat':0,'w_zone':0,'w_large':1.0,'w_back':1.0}),
    ('[Hermes v4] Default',      {'w_freq':2.0,'w_repeat':0.5,'w_zone':0.3,'w_large':0.3,'w_back':3.0}),
]
for label, params in configs:
    r = backtest_full(combined_predict, DLT, params, 10)
    print_result(label, r)

# ===== Grid Search Best Combination =====
print('\n===== Grid Search Best Engine Combination =====')

best_f = None
best_prize = None
all_results = []

for wf in [0, 1.0, 2.0, 3.0]:
    for wr in [0, 0.3, 0.5, 0.8]:
        for wz in [0, 0.2, 0.3]:
            for wl in [0, 0.2, 0.3]:
                params = {'w_freq':wf,'w_repeat':wr,'w_zone':wz,'w_large':wl,'w_back':3.0}
                r = backtest_full(combined_predict, DLT, params, 10)
                all_results.append(r)
                if best_f is None or r['avg_front'] > best_f['avg_front']:
                    best_f = r
                if best_prize is None or r['any_prize'] > best_prize['any_prize']:
                    best_prize = r

print_result('[BEST by Front Hits]', best_f)
print(f'  Params: freq={best_f["params"]["w_freq"]} repeat={best_f["params"]["w_repeat"]} '
      f'zone={best_f["params"]["w_zone"]} large={best_f["params"]["w_large"]}')
print_result('[BEST by Prize Rate]', best_prize)
print(f'  Prize tiers: {best_prize["prize_tiers"]}')

# ===== Honest Summary =====
print('\n===== Key Findings =====')
print(f'Random baseline: F=0.143/draw B=0.167/draw')
print(f'Best model:     F={best_f["avg_front"]:.3f}/draw ({best_f["front_lift"]:+.1f}% vs random) | '
      f'B={best_f["avg_back"]:.3f}/draw ({best_f["back_lift"]:+.1f}% vs random)')
print(f'Best prize rate: {best_prize["any_prize"]}/{best_prize["n"]}={best_prize["prize_rate"]*100:.1f}% '
      f'(vs random exp ~{5*2/420*100:.1f}% per draw)')

# ===== Per-period detail =====
print('\n===== Per-Period Hits Detail =====')
for i, (fh, bh) in enumerate(zip(best_f['front_hits'], best_f['back_hits'])):
    idx = 10 + i
    period = DLT[idx]['period']
    actual = DLT[idx]
    print(f'  {period}: F={fh}/5 {actual["front"]} | B={bh}/2 {actual["back"]}')

# ===== Save best params =====
saveable = {
    'w_freq': best_f['params']['w_freq'],
    'w_repeat': best_f['params']['w_repeat'],
    'w_zone': best_f['params']['w_zone'],
    'w_large': best_f['params']['w_large'],
    'w_back': 3.0,
    'description': f'DLT trained params, F={best_f["avg_front"]:.3f}/5 B={best_f["avg_back"]:.3f}/2'
}
with open(r'D:\AI\lottery-app\best_params_dlt.json', 'w', encoding='utf-8') as f:
    json.dump(saveable, f, indent=2, ensure_ascii=False)
print(f'\nSaved best params to best_params_dlt.json')