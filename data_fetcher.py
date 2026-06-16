#!/usr/bin/env python3
"""
500.com 大乐透 + 双色球 数据抓取器
"""
import urllib.request
import re
import json
import os
import time
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, 'data')
os.makedirs(DATA_DIR, exist_ok=True)

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,*/*',
    'Accept-Language': 'zh-CN,zh;q=0.9',
}

# ============================================================
# 大乐透
# ============================================================

def fetch_dlt_page():
    url = 'https://datachart.500.com/dlt/zoushi/jbzs_foreback.shtml'
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=20)
    raw = resp.read()
    return raw.decode('gb2312', errors='replace')

def parse_dlt_text(text):
    """解析大乐透页面"""
    results = []
    trs = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.DOTALL)
    
    for tr in trs:
        period_match = re.search(r'<td[^>]*align=["\']center["\'][^>]*>\s*(\d{5})\s*</td>', tr)
        if not period_match:
            continue
        period = period_match.group(1)
        if not period.startswith('26'):
            continue
        
        tds = re.findall(r'<td\b([^>]*)>(.*?)</td>', tr, re.DOTALL)
        
        reds = []
        backs = []
        for attrs, content in tds:
            m = re.search(r'(\d+)', content)
            if not m:
                continue
            num = int(m.group(1))
            
            if 'chartBall01' in attrs:
                if 1 <= num <= 35:
                    reds.append(num)
            elif 'chartBall02' in attrs:
                if 1 <= num <= 12:
                    backs.append(num)
        
        if len(reds) == 5 and len(backs) == 2:
            results.append({
                'period': period,
                'front': sorted(reds),
                'back': sorted(backs),
                'sum': sum(reds),
            })
    
    results.sort(key=lambda x: x['period'])
    return results

def load_dlt():
    path = os.path.join(DATA_DIR, 'dlt_history.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_dlt(data):
    path = os.path.join(DATA_DIR, 'dlt_history.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_dlt():
    """增量更新大乐透数据"""
    local = load_dlt()
    local_periods = {d['period'] for d in local}
    
    text = fetch_dlt_page()
    online = parse_dlt_text(text)
    
    new = [d for d in online if d['period'] not in local_periods]
    
    if new:
        all_data = local + new
        all_data.sort(key=lambda x: x['period'])
        save_dlt(all_data)
        print(f'[DLT] +{len(new)}期: {[d["period"] for d in new]}')
    else:
        print(f'[DLT] 无新数据 (最新: {local[-1]["period"] if local else "N/A"})')
    
    return new

# ============================================================
# 双色球
# ============================================================

def fetch_ssq_page():
    url = 'https://datachart.500.com/ssq/zoushi/jbzs_redblue.shtml'
    req = urllib.request.Request(url, headers=HEADERS)
    resp = urllib.request.urlopen(req, timeout=20)
    raw = resp.read()
    return raw.decode('gb2312', errors='replace')

def parse_ssq_text(text):
    """解析双色球页面"""
    results = []
    trs = re.findall(r'<tr[^>]*>(.*?)</tr>', text, re.DOTALL)
    
    for tr in trs:
        period_match = re.search(r'<td[^>]*align=["\']center["\'][^>]*>\s*(\d{5})\s*</td>', tr)
        if not period_match:
            continue
        period = period_match.group(1)
        
        tds = re.findall(r'<td\b([^>]*)>(.*?)</td>', tr, re.DOTALL)
        
        reds = []
        backs = []
        for attrs, content in tds:
            m = re.search(r'(\d+)', content)
            if not m:
                continue
            num = int(m.group(1))
            
            if 'chartBall01' in attrs:
                if 1 <= num <= 33:
                    reds.append(num)
            elif 'chartBall02' in attrs:
                if 1 <= num <= 16:
                    backs.append(num)
        
        # 双色球: 6个红球 + 1个蓝球
        if len(reds) >= 6 and len(backs) >= 1:
            reds = sorted(set(reds))[:6]
            backs = sorted(set(backs))[:1]
            results.append({
                'period': period,
                'front': reds,
                'back': backs,
                'sum': sum(reds),
            })
    
    results.sort(key=lambda x: x['period'])
    return results

def load_ssq():
    path = os.path.join(DATA_DIR, 'ssq_history.json')
    if os.path.exists(path):
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_ssq(data):
    path = os.path.join(DATA_DIR, 'ssq_history.json')
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def update_ssq():
    """增量更新双色球数据"""
    local = load_ssq()
    local_periods = {d['period'] for d in local}
    
    text = fetch_ssq_page()
    online = parse_ssq_text(text)
    
    new = [d for d in online if d['period'] not in local_periods]
    
    if new:
        all_data = local + new
        all_data.sort(key=lambda x: x['period'])
        save_ssq(all_data)
        print(f'[SSQ] +{len(new)}期: {[d["period"] for d in new[:5]]}')
    else:
        print(f'[SSQ] 无新数据 (最新: {local[-1]["period"] if local else "N/A"})')
    
    return new

# ============================================================
# 手动数据修正
# ============================================================

def add_manual(period, front, back, kind='dlt'):
    """手动添加开奖数据"""
    if kind == 'dlt':
        data = load_dlt()
        entry = {'period': period, 'front': front, 'back': back, 'sum': sum(front)}
        idx = next((i for i, d in enumerate(data) if d['period'] == period), None)
        if idx is not None:
            data[idx] = entry
        else:
            data.append(entry)
        data.sort(key=lambda x: x['period'])
        save_dlt(data)
        print(f'[DLT] {"更新" if idx is not None else "新增"} {period}: {front} + {back}')
    else:
        data = load_ssq()
        entry = {'period': period, 'front': front, 'back': back, 'sum': sum(front)}
        idx = next((i for i, d in enumerate(data) if d['period'] == period), None)
        if idx is not None:
            data[idx] = entry
        else:
            data.append(entry)
        data.sort(key=lambda x: x['period'])
        save_ssq(data)
        print(f'[SSQ] {"更新" if idx is not None else "新增"} {period}: {front} + {back}')

# ============================================================
# 测试
# ============================================================

if __name__ == '__main__':
    print(f'[{datetime.now().strftime("%H:%M:%S")}] 更新数据...')
    
    try:
        update_dlt()
    except Exception as e:
        print(f'[DLT ERROR] {e}')
    
    time.sleep(1)
    
    try:
        update_ssq()
    except Exception as e:
        print(f'[SSQ ERROR] {e}')
    
    # 显示当前数据状态
    dlt = load_dlt()
    ssq = load_ssq()
    print(f'\n当前: DLT {len(dlt)}期, SSQ {len(ssq)}期')
