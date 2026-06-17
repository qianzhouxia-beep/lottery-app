#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Lottery API Server - Raw Socket Implementation
Fixes ERR_INVALID_HTTP_RESPONSE on Windows by using raw sockets.
"""
import sys, os, json, math, random, time, socket, urllib.parse, requests
from datetime import datetime, timedelta
from pathlib import Path
from itertools import combinations

# ===== Self-Learning Engine =====
from hermes_learner import SelfLearningEngine, load_history

# Global learners (lazy initialized)
_DLT_LEARNER = None
_SSQ_LEARNER = None

def get_learner(kind='dlt'):
    global _DLT_LEARNER, _SSQ_LEARNER
    if kind == 'dlt':
        if _DLT_LEARNER is None:
            _DLT_LEARNER = SelfLearningEngine('dlt')
        return _DLT_LEARNER
    else:
        if _SSQ_LEARNER is None:
            _SSQ_LEARNER = SelfLearningEngine('ssq')
        return _SSQ_LEARNER

# ============================================================
# Config
# ============================================================
BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
DATA_DIR.mkdir(exist_ok=True)

# ============================================================
# Data Loading
# ============================================================

def load_dlt():
    # Prefer full history if available
    full = DATA_DIR / 'dlt_history_full.json'
    if full.exists():
        with open(full, 'r', encoding='utf-8') as f:
            return json.load(f)
    path = DATA_DIR / 'dlt_history.json'
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def load_ssq():
    # Prefer full history if available
    full = DATA_DIR / 'ssq_history_full.json'
    if full.exists():
        with open(full, 'r', encoding='utf-8') as f:
            return json.load(f)
    path = DATA_DIR / 'ssq_history.json'
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

# ============================================================
# Analysis Engine
# ============================================================

def zone_stats(nums, zones):
    return [sum(1 for n in nums if z[0] <= n <= z[1]) for z in zones]

def hot_cold(data, key='front', n=15):
    freq = {}
    for d in data:
        for num in d[key]:
            freq[num] = freq.get(num, 0) + 1
    total = len(data)
    return {num: count / total for num, count in freq.items()}

def avg_diff(data, key='front'):
    diffs = []
    for i in range(1, min(len(data), 20)):
        prev = data[i-1][key]
        curr = data[i][key]
        diffs.append(abs(sum(curr) - sum(prev)))
    return sum(diffs) / len(diffs) if diffs else 0

# ============================================================
# Prediction Engine (Hermes v4)
# ============================================================

def predict_dlt_v4(history, n=2, ai_front_scores=None, ai_back_scores=None):
    if len(history) < 10:
        return None
    
    recent = history[-10:]
    last = history[-1]
    
    front_zones = [(1,7),(8,14),(15,21),(22,28),(29,35)]
    back_zones = [(1,4),(5,8),(9,12)]
    
    last_front = last['front']
    last_back = last['back']
    last_fz = zone_stats(last_front, front_zones)
    
    hf = hot_cold(history[-15:], 'front')
    hb = hot_cold(history[-15:], 'back')
    
    prev = history[-2]['front'] if len(history) >= 2 else []
    reprob = {num: 1.0 if num in prev else 0.0 for num in range(1, 36)}
    
    avg_diff_val = avg_diff(history[-10:], 'front')
    
    sums = [d.get('sum', sum(d.get('front', []))) for d in history[-10:]]
    sum_trend = sums[-1] - sums[-2] if len(sums) >= 2 else 0
    
    candidates = {}
    for num in range(1, 36):
        score = 0.0
        for i, (z1, z2) in enumerate(front_zones):
            if z1 <= num <= z2:
                score += 0.3 if last_fz[i] > 0 else -0.1
                break
        freq = hf.get(num, 0)
        score += freq * 2.0
        score += reprob.get(num, 0) * 0.5
        mid_sum = 88
        last_sum = last.get('sum', sum(last.get('front', [])))
        if last_sum > 110:
            score += 0.3 if 60 <= num <= 90 else 0.0
        elif last_sum < 70:
            score += 0.3 if num >= 25 else 0.0
        # AI-boosted confidence: add AI's ranking score (0-0.45) to bias the engine
        if ai_front_scores and num in ai_front_scores:
            score += ai_front_scores[num] * 0.4
        candidates[num] = score
    
    sorted_nums = sorted(candidates.items(), key=lambda x: -x[1])
    
    results = []
    for strategy in ['normal', 'reverse']:
        if strategy == 'normal':
            chosen = sorted_nums[:5]
        else:
            reverse_sorted = sorted(candidates.items(), key=lambda x: x[1])[:10]
            chosen = random.sample(reverse_sorted, min(5, len(reverse_sorted)))
        
        front = sorted([n for n, s in chosen])
        
        hb_sorted = sorted(hb.items(), key=lambda x: -x[1])
        if strategy == 'normal':
            back = [n for n, s in hb_sorted[:2]]
        else:
            hb_reverse = sorted(hb.items(), key=lambda x: x[1])
            back = [n for n, s in hb_reverse[:2]]
        back.sort()
        
        results.append({
            'type': 'normal' if strategy == 'normal' else 'reverse',
            'front': front,
            'back': back,
            'sum': sum(front),
        })
    
    return results

def predict_ssq_v4(history, n=2, ai_front_scores=None, ai_back_scores=None):
    if len(history) < 10:
        return None
    
    hf = hot_cold(history[-15:], 'front')
    hb = hot_cold(history[-15:], 'back')
    
    last = history[-1]
    prev = history[-2]['front'] if len(history) >= 2 else []
    
    candidates = {}
    for num in range(1, 34):
        score = hf.get(num, 0) * 3.0
        if num in prev:
            score += 0.5
        # AI-boosted confidence
        if ai_front_scores and num in ai_front_scores:
            score += ai_front_scores[num] * 0.4
        candidates[num] = score
    
    sorted_nums = sorted(candidates.items(), key=lambda x: -x[1])
    
    results = []
    for strategy in ['normal', 'reverse']:
        if strategy == 'normal':
            chosen = sorted_nums[:6]
        else:
            reverse_sorted = sorted(candidates.items(), key=lambda x: x[1])[:12]
            chosen = random.sample(reverse_sorted, min(6, len(reverse_sorted)))
        
        front = sorted([n for n, s in chosen])
        
        hb_sorted = sorted(hb.items(), key=lambda x: -x[1])
        back = [n for n, s in hb_sorted[:1]]
        
        results.append({
            'type': 'normal' if strategy == 'normal' else 'reverse',
            'front': front,
            'back': back,
            'sum': sum(front),
        })
    
    return results

# ============================================================
# API Handlers
# ============================================================

def api_get_latest(kind='dlt'):
    data = load_dlt() if kind == 'dlt' else load_ssq()
    if not data:
        return {'error': 'No data'}
    latest = data[-1]
    return {
        'period': latest['period'],
        'front': latest['front'],
        'back': latest['back'],
        'sum': latest.get('sum', sum(latest['front'])),
        'count': len(data),
        'fetched_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

def api_get_history(kind='dlt', limit=30):
    data = load_dlt() if kind == 'dlt' else load_ssq()
    return data[-limit:]

def api_get_trend(kind='dlt'):
    data = load_dlt() if kind == 'dlt' else load_ssq()
    if len(data) < 5:
        return {'error': 'Not enough data'}
    
    recent = data[-10:]
    last = recent[-1]
    
    hf = hot_cold(data, 'front', 15)
    hb = hot_cold(data, 'back', 15)
    
    if kind == 'dlt':
        zones = [(1,7,'S'),(8,14,'M1'),(15,21,'M2'),(22,28,'M3'),(29,35,'L')]
    else:
        zones = [(1,6,'Z1'),(7,12,'Z2'),(13,19,'Z3'),(20,25,'Z4'),(26,33,'L')]
    
    zone_dist = zone_stats(last['front'], [z[:2] for z in zones])
    zone_labels = [z[2] for z in zones]
    
    return {
        'period': last['period'],
        'last_draw': {'front': last['front'], 'back': last['back']},
        'sum': last.get('sum', sum(last['front'])),
        'zone_dist': dict(zip(zone_labels, zone_dist)),
        'hot_front': sorted(hf.items(), key=lambda x: -x[1])[:10],
        'hot_back': sorted(hb.items(), key=lambda x: -x[1])[:6],
        'data_range': f"{data[0]['period']} - {data[-1]['period']}",
    }

# ============================================================
# AI Prediction (DeepSeek)
# ============================================================

from ai_client import call_deepseek, AI_SYSTEM_PROMPT, AI_CONFIG

def expand_combo(front_pool, back_pool, front_count, back_count):
    if front_count < 5: front_count = 5
    if front_count > len(front_pool): front_count = len(front_pool)
    if back_count < 2: back_count = 2
    if back_count > len(back_pool): back_count = len(back_pool)
    top_f = front_pool[:front_count]
    top_b = back_pool[:back_count]
    combos = []
    for fi in combinations(range(front_count), 5):
        for bi in combinations(range(back_count), 2):
            combos.append({
                'front': sorted([top_f[i] for i in fi]),
                'back': sorted([top_b[i] for i in bi])
            })
    return {
        'combos': combos,
        'count': len(combos),
        'cost': len(combos) * 2,
        'front_pool': top_f,
        'back_pool': top_b,
        'type': "{}"+str(front_count)+"+"+str(back_count)
    }

def expand_combo(front_pool, back_pool, front_count, back_count):
    if front_count < 5: front_count = 5
    if front_count > len(front_pool): front_count = len(front_pool)
    if back_count < 2: back_count = 2
    if back_count > len(back_pool): back_count = len(back_pool)
    top_f = front_pool[:front_count]
    top_b = back_pool[:back_count]
    combos = []
    for fi in combinations(range(front_count), 5):
        for bi in combinations(range(back_count), 2):
            combos.append({
                'front': sorted([top_f[i] for i in fi]),
                'back': sorted([top_b[i] for i in bi])
            })
    return {
        'combos': combos,
        'count': len(combos),
        'cost': len(combos) * 2,
        'front_pool': top_f,
        'back_pool': top_b,
        'type': f'{front_count}+{back_count}'
    }

def api_predict_ai(kind='dlt', front_pool_size=None, back_pool_size=None, front_user=None, back_user=None):
    """AI预测：AI当军师提供排名，Hermes统计引擎生成具体号码"""
    data = load_dlt() if kind == 'dlt' else load_ssq()
    if len(data) < 10:
        return {'error': 'Not enough history'}
    
    # Step 1: Call DeepSeek AI to get rankings and analysis
    lines = []
    for d in data[-30:]:
        f = ','.join(str(x) for x in d['front'])
        b = ','.join(str(x) for x in d['back'])
        lines.append(f"{d['period']}:[{f}]+[{b}]")
    data_str = '\n'.join(reversed(lines))
    user_prompt = f'分析最近30期{"大乐透" if kind=="dlt" else "双色球"}数据，预测下一期：\n{data_str}\n\n输出JSON。'
    
    raw = None
    ai_available = True
    for attempt in range(3):
        try:
            raw = call_deepseek(AI_SYSTEM_PROMPT, user_prompt)
            break
        except Exception as e:
            if attempt == 2:
                ai_available = False
                break
            time.sleep(2)
    
    result = {}
    if raw and ai_available:
        try:
            result = json.loads(raw) if isinstance(raw, str) else raw
        except:
            ai_available = False
    
    next_period = str(int(data[-1]['period']) + 1)
    
    # Fallback: if AI is unavailable, use empty scores (Hermes v4 runs pure stats)
    if not ai_available:
        ai_analysis = {'summary': 'AI服务暂时不可用，使用Hermes v4纯统计引擎'}
        ai_front_scores = {}
        ai_back_scores = {}
        ranked_front_display = []
        ranked_back_display = []
    else:
        ranked_f = result.get('ranked_front', [])
        ranked_b = result.get('ranked_back', [])
        ai_analysis = result.get('analysis', {})
        
        # Step 2: Build AI confidence scores for Hermes v4 engine
        # AI gives us ranked_front like [{"num":7,"confidence":0.9},...] → convert to score dict
        ai_front_scores = {}
        for i, item in enumerate(ranked_f):
            num = item.get('num')
            conf = item.get('confidence', 0.5)
            # Score: top rank gets highest bonus (0.5 at #1 down to 0 at #12)
            ai_front_scores[num] = conf * 0.5  # 0-0.45 range
        ai_back_scores = {}
        for i, item in enumerate(ranked_b):
            num = item.get('num')
            conf = item.get('confidence', 0.5)
            ai_back_scores[num] = conf * 0.5
        
        # Build ranked lists for UI (from AI rankings)
        # Ensure all 35/33 front and 12 back numbers appear with AI confidence
        all_front = list(range(1, 36)) if kind == 'dlt' else list(range(1, 34))
        all_back = list(range(1, 13))
        
        # Fill missing numbers with low confidence
        for n in all_front:
            if n not in ai_front_scores:
                ai_front_scores[n] = 0.0
        for n in all_back:
            if n not in ai_back_scores:
                ai_back_scores[n] = 0.0
        
        ranked_front_display = [
            {'num': n, 'confidence': round(ai_front_scores[n], 2)}
            for n in sorted(all_front, key=lambda x: -ai_front_scores[x])
        ]
        ranked_back_display = [
            {'num': n, 'confidence': round(ai_back_scores[n], 2)}
            for n in sorted(all_back, key=lambda x: -ai_back_scores[x])
        ]
    
    # Step 3: Use Hermes v4 engine (with or without AI-boosted weights)
    engine_func = predict_dlt_v4 if kind == 'dlt' else predict_ssq_v4
    preds = engine_func(data, 2, ai_front_scores=ai_front_scores, ai_back_scores=ai_back_scores)
    
    main = preds[0]  # Primary prediction
    reverse_picks = preds[1] if len(preds) > 1 else None
    
    # Step 4: Generate ranked display for AI-unavailable case (stats-based)
    if not ai_available:
        # Build simple frequency-based ranking
        freq_front = {}
        freq_back = {}
        for d in data[-30:]:
            for n in d['front']:
                freq_front[n] = freq_front.get(n, 0) + 1
            for n in d['back']:
                freq_back[n] = freq_back.get(n, 0) + 1
        max_f = max(freq_front.values()) if freq_front else 1
        max_b = max(freq_back.values()) if freq_back else 1
        ranked_front_display = [
            {'num': n, 'confidence': round(freq_front.get(n, 0) / max_f, 2)}
            for n in sorted(freq_front.keys(), key=lambda x: -freq_front[x])
        ]
        ranked_back_display = [
            {'num': n, 'confidence': round(freq_back.get(n, 0) / max_b, 2)}
            for n in sorted(freq_back.keys(), key=lambda x: -freq_back[x])
        ]
    
    # Step 5: Determine front/back number pools for combo expansion
    # When user provides their own pool, use its actual size regardless of front_pool_size param
    if front_user or back_user:
        fc = len(front_user) if front_user else (front_pool_size if front_pool_size else 5)
        bc = len(back_user) if back_user else (back_pool_size if back_pool_size else 2)
    else:
        fc = front_pool_size if front_pool_size else 5
        bc = back_pool_size if back_pool_size else 2

    if fc > 5 or bc > 2:
        # User's own numbers or AI's top numbers as pool
        if front_user:
            front_nums = sorted(list(front_user))
        else:
            front_nums = [x['num'] for x in ranked_front_display[:max(fc, 8)]]
        if back_user:
            back_nums = sorted(list(back_user))
        else:
            back_nums = [x['num'] for x in ranked_back_display[:max(bc, 4)]]
        
        # If still not enough, fill from Hermes engine numbers
        if len(front_nums) < fc:
            extras = [n for n in main['front'] if n not in front_nums]
            for n in ranked_front_display:
                if n['num'] not in front_nums and len(extras) < fc - len(front_nums):
                    extras.append(n['num'])
            front_nums.extend(extras[:fc - len(front_nums)])
        if len(back_nums) < bc:
            extras = [n for n in main['back'] if n not in back_nums]
            for n in ranked_back_display:
                if n['num'] not in back_nums and len(extras) < bc - len(back_nums):
                    extras.append(n['num'])
            back_nums.extend(extras[:bc - len(back_nums)])
        
        combo = expand_combo(front_nums[:fc], back_nums[:bc], fc, bc)
    else:
        combo = None
    
    # Step 6: Build reverse prediction (completely different from main)
    if reverse_picks:
        rev_front = reverse_picks['front']
        rev_back = reverse_picks['back']
    else:
        # Fall back: pick from lowest-confidence numbers that aren't in main
        top_conf_nums = set(main['front'] + main['back'])
        low_front = [x['num'] for x in ranked_front_display if x['num'] not in top_conf_nums][-5:]
        low_back = [x['num'] for x in ranked_back_display if x['num'] not in top_conf_nums][-2:]
        rev_front, rev_back = low_front, low_back
    
    return {
        'for_period': next_period,
        'model': 'Hermes AI (DeepSeek)' if ai_available else 'Hermes v4 (pure stats)',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'analysis': ai_analysis,
        'ranked_front': ranked_front_display,
        'ranked_back': ranked_back_display,
        'user_front': front_user,
        'user_back': back_user,
        'prediction': {
            'front': main['front'],
            'back': main['back'],
            'reason': 'AI排名 + Hermes统计引擎生成'
        },
        'reverse': {
            'front': rev_front,
            'back': rev_back,
            'reason': '低频冷号反选，与正选完全不同'
        },
        'combo': combo,
    }

def api_predict(kind='dlt'):
    data = load_dlt() if kind == 'dlt' else load_ssq()
    if len(data) < 10:
        return {'error': 'Not enough history'}
    
    preds = predict_dlt_v4(data, 2) if kind == 'dlt' else predict_ssq_v4(data, 2)
    next_period = str(int(data[-1]['period']) + 1)
    
    return {
        'for_period': next_period,
        'predictions': preds,
        'model': 'Hermes v4',
        'generated_at': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
    }

def api_review(kind='dlt', period=None):
    data = load_dlt() if kind == 'dlt' else load_ssq()
    
    if period:
        target = next((d for d in data if d['period'] == period), None)
        if not target:
            return {'error': f'Period {period} not found'}
        idx = data.index(target)
        prev = data[idx-1] if idx > 0 else None
    else:
        if len(data) < 2:
            return {'error': 'Not enough data'}
        idx = len(data) - 2
        target = data[idx]
        prev = data[idx-1] if idx > 0 else None
    
    return {
        'period': target['period'],
        'actual': {'front': target['front'], 'back': target['back']},
        'prev': {'front': prev['front'], 'back': prev['back']} if prev else None,
        'data_count': len(data),
    }

# ============================================================
# HTTP Server (Raw Socket - avoids http.server protocol bugs)
# ============================================================

def make_response(status_code, content_type, body_bytes):
    """Build a proper HTTP/1.1 response."""
    status_text = {200: 'OK', 404: 'Not Found', 400: 'Bad Request', 405: 'Method Not Allowed'}.get(status_code, 'Unknown')
    header = (
        f"HTTP/1.1 {status_code} {status_text}\r\n"
        f"Content-Type: {content_type}\r\n"
        f"Access-Control-Allow-Origin: *\r\n"
        f"Content-Length: {len(body_bytes)}\r\n"
        f"Connection: close\r\n"
        f"\r\n"
    )
    return header.encode('ascii') + body_bytes


def handle_request(raw_request):
    """Parse and route HTTP request."""
    try:
        # Split headers from body
        if b'\r\n\r\n' not in raw_request:
            return make_response(400, 'text/plain', b'Bad Request')
        
        header_part = raw_request.split(b'\r\n\r\n', 1)[0]
        lines = header_part.decode('ascii', errors='replace').split('\r\n')
        if not lines:
            return make_response(400, 'text/plain', b'Bad Request')
        
        request_line = lines[0].strip()
        parts = request_line.split(' ', 2)
        if len(parts) < 3:
            return make_response(400, 'text/plain', b'Bad Request')
        
        method, url_path, _version = parts
        
        # Parse query string
        if '?' in url_path:
            path, qs_str = url_path.split('?', 1)
        else:
            path, qs_str = url_path, ''
        qs = urllib.parse.parse_qs(qs_str)
        
        path = path.rstrip('/')
        kind = qs.get('kind', ['dlt'])[0]
        
        # CORS preflight
        if method == 'OPTIONS':
            body = b''
            resp = (
                "HTTP/1.1 200 OK\r\n"
                "Access-Control-Allow-Origin: *\r\n"
                "Access-Control-Allow-Methods: GET, POST, OPTIONS\r\n"
                "Access-Control-Allow-Headers: Content-Type\r\n"
                "Content-Length: 0\r\n"
                "Connection: close\r\n"
                "\r\n"
            ).encode('ascii')
            return resp
        
        # Parse POST body (if any)
        body_bytes = b''
        if b'\r\n\r\n' in raw_request:
            body_bytes = raw_request.split(b'\r\n\r\n', 1)[1]
        
        if method not in ('GET', 'POST'):
            return make_response(405, 'text/plain', b'Method Not Allowed')
        
        # ===== Self-Learning Routes =====
        if path == '/api/predict_selflearn':
            learner = get_learner(kind)
            # Use hybrid strategy by default with full AI
            result = learner.predict(
                load_history(kind),
                strategy='hybrid',
                call_ai_func=lambda s, u: call_deepseek(s, u)
            )
            # Add reverse reason to AI predictions
            if 'reverse' in result and isinstance(result['reverse'], dict) and 'reason' not in result['reverse']:
                result['reverse']['reason'] = '基于历史教训的冷号反选'
            # Attach learning status
            result['learning'] = {
                'current_strategy': learner.meta.get_status()['current_strategy'],
                'weights': learner.stats.params,
            }
            if learner.lessons and learner.lessons.lessons['lessons']:
                latest_lesson = learner.lessons.lessons['lessons'][-1]
                result['learning']['latest_lesson'] = latest_lesson
            data = result
        
        elif path == '/api/self_learn':
            if method != 'POST':
                return make_response(405, 'text/plain', b'Use POST for self_learn')
            try:
                payload = json.loads(body_bytes.decode('utf-8'))
            except:
                data = {'error': 'Invalid JSON body'}
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                return make_response(400, 'application/json; charset=utf-8', body)
            
            period = payload.get('period', '')
            front = payload.get('front', [])
            back = payload.get('back', [])
            strategy = payload.get('strategy', 'hybrid')
            
            if not front or not back:
                data = {'error': 'Missing front/back actual numbers'}
                body = json.dumps(data, ensure_ascii=False).encode('utf-8')
                return make_response(400, 'application/json; charset=utf-8', body)
            
            learner = get_learner(kind)
            
            # 找到对应期数的预测记录
            prediction_record = None
            for r in reversed(learner.records['records']):
                if r.get('period') == period or (not period and r.get('period') == str(int(learner.records['records'][-1].get('period', 0)))):
                    prediction_record = {
                        'prediction': r.get('prediction', {}),
                        'reverse': r.get('reverse', {}),
                        'strategy': r.get('strategy', strategy),
                    }
                    break
            
            if not prediction_record and learner.records['records']:
                # 使用最新的预测记录
                latest = learner.records['records'][-1]
                prediction_record = {
                    'prediction': latest.get('prediction', {}),
                    'reverse': latest.get('reverse', {}),
                    'strategy': latest.get('strategy', strategy),
                }
            
            if not prediction_record:
                data = {'error': '找不到匹配的预测记录，请先生成一次预测', 'note': '可以用空记录继续学习'}
                prediction_record = {
                    'prediction': {'front': [], 'back': []},
                    'reverse': {'front': [], 'back': []},
                    'strategy': strategy,
                }
            
            actual = {'period': period, 'front': front, 'back': back}
            
            # 执行学习
            import io as _io
            old_stdout = sys.stdout
            sys.stdout = _io.StringIO()
            try:
                learn_result = learner.self_learn(prediction_record, actual, verbose=True)
            except Exception as e:
                learn_result = {'error': str(e)}
            learn_log = sys.stdout.getvalue()
            sys.stdout = old_stdout
            
            data = {
                'success': True,
                'period': period,
                'front_hits': learn_result.get('front_hits', 0),
                'back_hits': learn_result.get('back_hits', 0),
                'weights_optimized': learn_result.get('weights_optimized', False),
                'strategy_switched': learn_result.get('strategy_switched', False),
                'new_weights': learner.stats.params,
                'learning_log': learn_log,
                'performance': learner.lessons.get_performance_summary(),
            }
        
        elif path == '/api/learning_status':
            learner = get_learner(kind)
            data = learner.get_learning_status()
        
        elif path == '/api/refresh_weights':
            """手动触发权重优化（即使没有新一期开奖，也可手动调参）"""
            learner = get_learner(kind)
            hist = load_history(kind)
            if len(hist) >= 35:
                learner.stats.optimize_weights(hist, window=30, verbose=False)
                data = {
                    'success': True,
                    'new_weights': learner.stats.params,
                    'note': '基于全部历史数据重新优化权重',
                }
            else:
                data = {'error': f'数据不足(仅{len(hist)}期)，需要至少35期'}
        
        else:
            # Route requests
            if path == '/api/latest':
                data = api_get_latest(kind)
            elif path == '/api/history':
                limit = int(qs.get('limit', [30])[0])
                data = api_get_history(kind, limit)
            elif path == '/api/trend':
                data = api_get_trend(kind)
            elif path == '/api/predict':
                data = api_predict(kind)
            elif path == '/api/predict_ai':
                fc = int(qs.get('fc', [5])[0])  # front pool count
                bc = int(qs.get('bc', [2])[0])  # back pool count
                # User-selected numbers (comma-separated)
                front_str = qs.get('front', [None])[0]
                back_str = qs.get('back', [None])[0]
                front_user = [int(x) for x in front_str.split(',')] if front_str else None
                back_user = [int(x) for x in back_str.split(',')] if back_str else None
                data = api_predict_ai(kind, fc, bc, front_user, back_user)
            elif path == '/api/review':
                period = qs.get('period', [None])[0]
                data = api_review(kind, period)
            elif path in ('/api/dlt', '/api/ssq'):
                data = api_get_latest(kind)
            elif path == '/api/status':
                dlt_data = load_dlt()
                ssq_data = load_ssq()
                data = {
                    'dlt_count': len(dlt_data),
                    'ssq_count': len(ssq_data),
                    'dlt_latest': dlt_data[-1]['period'] if dlt_data else None,
                    'ssq_latest': ssq_data[-1]['period'] if ssq_data else None,
                    'server_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                }
            elif path == '/api/config':
                from ai_client import AI_CONFIG, reload_config
                data = {
                    'model': AI_CONFIG.get('model', ''),
                    'base_url': AI_CONFIG.get('base_url', ''),
                    'api_key_preview': AI_CONFIG.get('api_key', '')[:8] + '...' if AI_CONFIG.get('api_key') else '',
                }
            elif path == '' or path == '/':
                try:
                    html_file = BASE_DIR / 'web' / 'index.html'
                    body = open(html_file, 'rb').read()
                except Exception:
                    body = b'<html><body><h1>Frontend not found</h1></body></html>'
                return make_response(200, 'text/html; charset=utf-8', body)
            else:
                body = json.dumps({'error': 'Not found'}).encode('utf-8')
                return make_response(404, 'application/json; charset=utf-8', body)
            body = json.dumps(data, ensure_ascii=False).encode('utf-8')
            return make_response(200, 'application/json; charset=utf-8', body)
        
        body = json.dumps(data, ensure_ascii=False).encode('utf-8')
        return make_response(200, 'application/json; charset=utf-8', body)
        
    except Exception as e:
        err_body = json.dumps({'error': str(e)}).encode('utf-8')
        return make_response(500, 'application/json; charset=utf-8', err_body)


def run_server(host='0.0.0.0', port=None):
    """Run HTTP server using raw sockets.
    Port priority: $WEB_PORT > $ZEABUR_PORT > $PORT > default 5123
    """
    if port is None:
        _raw = os.environ.get('WEB_PORT') or os.environ.get('ZEABUR_PORT') or os.environ.get('PORT') or ''
        # Strip possible shell literal like ${WEB_PORT}
        _raw = _raw.strip().lstrip('$').strip('{}').strip()
        port = int(_raw) if _raw.isdigit() else 5123
    # Pre-load HTML
    try:
        open(BASE_DIR / 'web' / 'index.html', 'rb').read()
    except Exception:
        pass
    
    # ===== 启动自动学习守护 =====
    try:
        from auto_learner import AutoLearnerManager
        _auto_learner = AutoLearnerManager()
        _auto_learner.start_all()
    except Exception as e:
        print(f'[警告] 自动学习守护启动失败: {e}')
    
    srv = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    srv.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    srv.bind((host, port))
    srv.listen(5)
    
    print(f'[OK] Lottery API Server running at http://localhost:{port}')
    print(f'   Latest:   http://localhost:{port}/api/latest?kind=dlt')
    print(f'   Trend:    http://localhost:{port}/api/trend?kind=dlt')
    print(f'   Predict:  http://localhost:{port}/api/predict?kind=dlt')
    print(f'   AI:       http://localhost:{port}/api/predict_ai?kind=dlt')
    print(f'   Status:   http://localhost:{port}/api/status')
    print(f'   \n=== Self-Learning (NEW!) ===')
    print(f'   SelfLearn Predict: http://localhost:{port}/api/predict_selflearn?kind=dlt')
    print(f'   SelfLearn (POST):  http://localhost:{port}/api/self_learn?kind=dlt')
    print(f'   Learning Status:   http://localhost:{port}/api/learning_status?kind=dlt')
    print(f'   Refresh Weights:   http://localhost:{port}/api/refresh_weights?kind=dlt')
    
    try:
        while True:
            conn, addr = srv.accept()
            conn.settimeout(10)
            try:
                raw = b''
                while True:
                    chunk = conn.recv(4096)
                    if not chunk:
                        break
                    raw += chunk
                    if b'\r\n\r\n' in raw:
                        break
                if raw:
                    response = handle_request(raw)
                    conn.sendall(response)
            except socket.timeout:
                pass
            except Exception:
                pass
            finally:
                try:
                    conn.close()
                except Exception:
                    pass
    except KeyboardInterrupt:
        pass
    finally:
        srv.close()


# ============================================================
# Entry Point
# ============================================================

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == 'update':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
        from data_fetcher import update_dlt, update_ssq
        print(f'[{datetime.now().strftime("%H:%M:%S")}] Updating data...')
        try:
            update_dlt()
        except Exception as e:
            print(f'[DLT ERROR] {e}')
        time.sleep(1)
        try:
            update_ssq()
        except Exception as e:
            print(f'[SSQ ERROR] {e}')
    else:
        run_server()
