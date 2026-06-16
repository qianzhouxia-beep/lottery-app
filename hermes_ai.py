"""
Hermes AI Layer - Self-Evolution Core
Uses DeepSeek to analyze lottery data and generate predictions
"""
import requests, json, time, io, sys
from datetime import datetime

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# ===== Config =====
with open(r'D:\AI\lottery-app\config.json', 'r') as f:
    CONFIG = json.load(f)

API_KEY = CONFIG['api_key']
BASE_URL = CONFIG['base_url']
MODEL = CONFIG['model']

# ===== API Helper =====
def call_deepseek(system, user, max_tokens=600, temperature=0.3):
    url = f'{BASE_URL}/chat/completions'
    headers = {
        'Authorization': f'Bearer {API_KEY}',
        'Content-Type': 'application/json'
    }
    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user}
        ],
        'max_tokens': max_tokens,
        'temperature': temperature
    }
    resp = requests.post(url, headers=headers, json=payload, timeout=30)
    if resp.status_code != 200:
        raise Exception(f'API Error {resp.status_code}: {resp.text}')
    return resp.json()['choices'][0]['message']['content']

# ===== Hermes AI Analysis =====
SYSTEM_PROMPT = '''你是一个专业的大乐透彩票预测专家。你擅长从历史数据中发现隐藏的规律和趋势。

你的分析维度：
1. 频率分析：哪些号码出现次数最多/最少
2. 区间分布：S区(1-12)、M1区(13-23)、M2区(24-29)、M3区(30-35)的活跃度
3. 和值趋势：近期和值大小分布
4. 冷热转换：热号是否开始转冷，冷号是否即将回补
5. 连号模式：是否有连号、同尾号等特征
6. 后区模式：后区(1-12)的大小、冷热分布

输出格式（必须严格遵循）：
{
  "analysis": {
    "hot_front": [号码列表，按热度排序],
    "cold_front": [号码列表],
    "hot_back": [号码列表],
    "cold_back": [号码列表],
    "zone_distribution": {"S":数量,"M1":数量,"M2":数量,"M3":数量},
    "sum_range": "low/mid/high",
    "trend": "描述近期主要趋势"
  },
  "prediction": {
    "front": [5个预测号码],
    "back": [2个预测号码],
    "reason": "简要说明预测逻辑（30字以内）"
  },
  "reverse": {
    "front": [5个反选号码（排除正选后从低频区间选）],
    "back": [2个反选号码],
    "reason": "反选逻辑（20字以内）"
  }
}
只输出JSON，不要其他文字。'''

def analyze_recent_data(history, n=30):
    """将最近n期的数据格式化为prompt"""
    recent = history[-n:]
    lines = []
    for d in recent:
        f = ','.join(str(x) for x in d['front'])
        b = ','.join(str(x) for x in d['back'])
        lines.append(f"{d['period']}:[{f}]+[{b}]")
    return '\n'.join(reversed(lines[-30:]))

def get_prediction(history, kind='dlt', n_history=30):
    """获取AI预测"""
    data_str = analyze_recent_data(history, n_history)
    
    user_prompt = f'''分析以下{n_history}期大乐透开奖数据，预测下一期：

{data_str}

输出JSON格式的分析和预测。'''

    raw = call_deepseek(SYSTEM_PROMPT, user_prompt, max_tokens=600, temperature=0.3)
    
    # Parse JSON
    try:
        result = json.loads(raw)
        return result
    except:
        return {'error': 'parse_failed', 'raw': raw}

def analyze_prediction_error(prediction, actual, kind='dlt'):
    """分析预测偏差，供模型自进化使用"""
    pred_front = set(prediction.get('front', []))
    pred_back = set(prediction.get('back', []))
    actual_front = set(actual['front'])
    actual_back = set(actual['back'])
    
    front_hit = len(pred_front & actual_front)
    back_hit = len(pred_back & actual_back)
    
    system = '''你是一个彩票预测分析师。分析预测与实际开奖的偏差，给出模型调整建议。
输出JSON格式：
{
  "front_accuracy": "high/medium/low",
  "back_accuracy": "high/medium/low", 
  "main_problem": "描述主要问题（20字以内）",
  "suggestion": "模型调整建议（30字以内）",
  "next_adjustment": {
    "increase_weight": ["建议提高权重的因素"],
    "decrease_weight": ["建议降低权重的因素"]
  }
}
只输出JSON。'''
    
    user = f'''预测：{prediction}
实际：{actual}
前区命中：{front_hit}/5，后区命中：{back_hit}/2
分析偏差并给出调整建议。'''
    
    try:
        raw = call_deepseek(system, user, max_tokens=400, temperature=0.1)
        return json.loads(raw)
    except:
        return {'error': 'parse_failed', 'raw': raw}

# ===== Feedback Loop: Self Evolution =====
def self_learn(history, prediction, actual, kind='dlt'):
    """完整的反馈学习闭环"""
    analysis = analyze_prediction_error(prediction, actual, kind)
    print(f'  [Self-Learn] {kind} front={analysis.get("front_accuracy","?")} back={analysis.get("back_accuracy","?")}')
    print(f'  [Self-Learn] 问题: {analysis.get("main_problem","?")}')
    print(f'  [Self-Learn] 建议: {analysis.get("suggestion","?")}')
    
    # Load or init learning log
    log_path = f'D:/AI/lottery-app/data/{kind}_learning_log.json'
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log = json.load(f)
    except:
        log = {'corrections': [], 'adjustments': []}
    
    log['corrections'].append({
        'timestamp': datetime.now().isoformat(),
        'period': actual.get('period'),
        'prediction': prediction,
        'actual': actual,
        'analysis': analysis
    })
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    return analysis

# ===== Batch prediction for backtesting =====
def backtest_ai(history, start_idx=50, n_test=30):
    """用AI对历史做回测（从start_idx开始，测试n_test期）"""
    results = []
    for i in range(start_idx, min(start_idx + n_test, len(history))):
        hist = history[:i]
        actual = history[i]
        
        pred = get_prediction(hist, n_history=30)
        if 'error' in pred:
            continue
        
        pred_front = set(pred.get('prediction', {}).get('front', []))
        pred_back = set(pred.get('prediction', {}).get('back', []))
        actual_front = set(actual['front'])
        actual_back = set(actual['back'])
        
        fh = len(pred_front & actual_front)
        bh = len(pred_back & actual_back)
        
        results.append({
            'period': actual['period'],
            'predicted_front': list(pred.get('prediction', {}).get('front', [])),
            'predicted_back': list(pred.get('prediction', {}).get('back', [])),
            'actual_front': actual['front'],
            'actual_back': actual['back'],
            'front_hits': fh,
            'back_hits': bh
        })
        print(f'  {actual["period"]}: pred={pred.get("prediction",{}).get("front",[])}+{pred.get("prediction",{}).get("back",[])} '
              f'actual={actual["front"]}+{actual["back"]} hits={fh}+{bh}')
        
        time.sleep(0.5)  # Rate limit
    
    avg_f = sum(r['front_hits'] for r in results) / len(results)
    avg_b = sum(r['back_hits'] for r in results) / len(results)
    print(f'\nAI Backtest: {len(results)} periods | Avg F={avg_f:.2f}/5 B={avg_b:.2f}/2')
    return results

if __name__ == '__main__':
    import sys
    
    with open(r'D:\AI\lottery-app\data\dlt_history_full.json', 'r', encoding='utf-8') as f:
        dlt = json.load(f)
    
    print(f'DLT loaded: {len(dlt)} periods, {dlt[0]["period"]} -> {dlt[-1]["period"]}')
    print('\n=== Test AI Prediction (latest 30 periods) ===')
    
    result = get_prediction(dlt[-50:], n_history=30)
    print(json.dumps(result, ensure_ascii=False, indent=2))