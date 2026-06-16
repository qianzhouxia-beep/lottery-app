"""
抓取大乐透和双色球历史数据 (2023-2025)
正确解析 500.com 的 period 格式：23010 -> 2023年第10期
"""
import requests, json, time, io, sys
from bs4 import BeautifulSoup

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
}

def normalize_period(raw):
    """'23010' -> '23010' (保持原样，用于排序)"""
    return raw.strip()

def fetch_dlt():
    url = 'https://datachart.500.com/dlt/history/newinc/history.php?start=23001&end=26064'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.encoding = 'gb2312'
    soup = BeautifulSoup(resp.text, 'html.parser')
    rows = soup.select('tr')[1:]

    data = []
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        if len(cols) < 8:
            continue
        period_raw = cols[0].strip()
        if not re.match(r'^\d{5}$', period_raw):
            continue
        try:
            front = [int(cols[i]) for i in range(1, 6)]
            back = [int(cols[i]) for i in range(6, 8)]
            data.append({'period': period_raw, 'front': front, 'back': back})
        except:
            pass

    # Sort by period ascending
    data.sort(key=lambda x: x['period'])
    print(f'DLT: {len(data)} records, {data[0]["period"]} -> {data[-1]["period"]}')
    return data

def fetch_ssq():
    url = 'https://datachart.500.com/ssq/history/newinc/history.php?start=23001&end=26065'
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.encoding = 'gb2312'
    soup = BeautifulSoup(resp.text, 'html.parser')
    rows = soup.select('tr')[1:]

    data = []
    for row in rows:
        cols = [td.get_text(strip=True) for td in row.find_all('td')]
        if len(cols) < 8:
            continue
        period_raw = cols[0].strip()
        if not re.match(r'^\d{5}$', period_raw):
            continue
        try:
            front = [int(cols[i]) for i in range(1, 6)]
            back = [int(cols[6])]  # SSQ has 1 back number
            data.append({'period': period_raw, 'front': front, 'back': back})
        except:
            pass

    data.sort(key=lambda x: x['period'])
    print(f'SSQ: {len(data)} records, {data[0]["period"]} -> {data[-1]["period"]}')
    return data

if __name__ == '__main__':
    import re
    print('Fetching DLT (2023-2025)...')
    dlt = fetch_dlt()
    time.sleep(1)
    print('Fetching SSQ (2023-2025)...')
    ssq = fetch_ssq()

    with open(r'D:\AI\lottery-app\data\dlt_history_full.json', 'w', encoding='utf-8') as f:
        json.dump(dlt, f, ensure_ascii=False, indent=2)

    with open(r'D:\AI\lottery-app\data\ssq_history_full.json', 'w', encoding='utf-8') as f:
        json.dump(ssq, f, ensure_ascii=False, indent=2)

    print(f'\nDone! DLT={len(dlt)} SSQ={len(ssq)}')
    print(f'DLT range: {dlt[0]["period"]} -> {dlt[-1]["period"]}')
    print(f'SSQ range: {ssq[0]["period"]} -> {ssq[-1]["period"]}')