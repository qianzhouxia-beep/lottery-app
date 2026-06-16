"""
Hermes DeepSeek Integration
Self-evolution AI layer with feedback loop
"""
import json, time, io, sys, requests
from datetime import datetime

# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

# Config
with open(r'D:\AI\lottery-app\config.json', 'r') as f:
    CONFIG = json.load(f)
API_KEY = CONFIG['api_key']
BASE_URL = CONFIG['base_url']
MODEL = CONFIG['model']

def call_ai(system, user, max_tokens=600, temperature=0.3):
    try:
        resp = requests.post(f'{BASE_URL}/chat/completions',
            headers={'Authorization': f'Bearer {API_KEY}', 'Content-Type': 'application/json'},
            json={'model': MODEL,
                  'messages': [{'role':'system','content':system}, {'role':'user','content':user}],
                  'max_tokens': max_tokens, 'temperature': 0  # 固定输出，同一输入永远同一结果},
            timeout=25)
        if resp.status_code != 200:
            return {'error': f'HTTP {resp.status_code}', 'detail': resp.text[:100]}
        return json.loads(resp.json()['choices'][0]['message']['content'])
    except Exception as e:
        return {'error': str(e)}

SYSTEM_PROMPT = '''你是一个专业的大乐透彩票预测专家。

输出严格JSON格式（不带任何其他文字）：
{
  "analysis": {
    "hot_front": [按热度排序的前区号码],
    "cold_front": [低频号码],
    "hot_back": [后区热号],
    "cold_back": [后区冷号],
    "zone_distribution": {"S":1-12区数量,"M1":13-23区数量,"M2":24-29区数量,"M3":30-35区数量},
    "sum_range": "low/mid/high",
    "trend": "近期趋势描述（15字以内）"
  },
  "ranked_front": [{"num":号码,"confidence":置信度(0-1)},...],  // 按置信度降序排列的前区12个候选
  "ranked_back": [{"num":号码,"confidence":置信度(0-1)},...],    // 按置信度降序排列的后区6个候选
  "prediction": {
    "front": [5个正选前区号],
    "back": [2个正选后区号],
    "reason": "预测逻辑（20字以内）"
  },
  "reverse": {
    "front": [5个反选前区号（必须与正选完全不同）],
    "back": [2个反选后区号（必须与正选完全不同）],
    "reason": "反选逻辑（20字以内）"
  }
}'''

def build_prompt(history, n=30):
    lines = []
    for d in history[-n:]:
        f = ','.join(str(x) for x in d['front'])
        b = ','.join(str(x) for x in d['back'])
        lines.append(f"{d['period']}:[{f}]+[{b}]")
    return f'分析最近{n}期大乐透数据，预测下一期：\n' + '\n'.join(reversed(lines[-n:])) + '\n\n输出JSON。'

def get_prediction(history, n_history=30):
    result = call_ai(SYSTEM_PROMPT, build_prompt(history, n_history), max_tokens=600, temperature=0)
    if 'error' in result:
        return {'success': False, 'error': result['error']}
    return {'success': True, 'data': result}

def self_learn(prediction, actual, kind='dlt'):
    """反馈学习：分析预测偏差并记录到学习日志"""
    pred_f = set(prediction.get('prediction', {}).get('front', []))
    pred_b = set(prediction.get('prediction', {}).get('back', []))
    actual_f = set(actual['front'])
    actual_b = set(actual['back'])
    fh = len(pred_f & actual_f)
    bh = len(pred_b & actual_b)
    
    log_path = f'D:/AI/lottery-app/data/{kind}_learning_log.json'
    try:
        with open(log_path, 'r', encoding='utf-8') as f:
            log = json.load(f)
    except:
        log = {'corrections': [], 'summary': {'total': 0, 'front_hits_sum': 0, 'back_hits_sum': 0}}
    
    log['summary']['total'] += 1
    log['summary']['front_hits_sum'] += fh
    log['summary']['back_hits_sum'] += bh
    
    if fh == 0 and bh == 0:
        log['corrections'].append({
            'timestamp': datetime.now().isoformat(),
            'period': actual.get('period'),
            'prediction': prediction,
            'actual': {'front': actual['front'], 'back': actual['back']},
            'front_hits': fh, 'back_hits': bh
        })
        # Keep last 20 corrections
        log['corrections'] = log['corrections'][-20:]
    
    with open(log_path, 'w', encoding='utf-8') as f:
        json.dump(log, f, ensure_ascii=False, indent=2)
    
    avg_f = log['summary']['front_hits_sum'] / log['summary']['total']
    avg_b = log['summary']['back_hits_sum'] / log['summary']['total']
    return {'front_hits': fh, 'back_hits': bh, 'avg_front': avg_f, 'avg_back': avg_b}

if __name__ == '__main__':
    # Quick test
    with open(r'D:\AI\lottery-app\data\dlt_history_full.json', 'r', encoding='utf-8') as f:
        dlt = json.load(f)
    
    print('Testing AI prediction...')
    result = get_prediction(dlt, 30)
    if result['success']:
        d = result['data']
        print(f'Prediction: {d["prediction"]["front"]}+{d["prediction"]["back"]}')
        print(f'Reason: {d["prediction"]["reason"]}')
        print(f'Reverse: {d["reverse"]["front"]}+{d["reverse"]["back"]}')
        print(f'Reason: {d["reverse"]["reason"]}')
    else:
        print(f'Error: {result["error"]}')