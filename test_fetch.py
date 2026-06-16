import requests, sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
from bs4 import BeautifulSoup

url = 'https://datachart.500.com/dlt/history/newinc/history.php?start=23001&end=23010'
resp = requests.get(url, headers={'User-Agent':'Mozilla/5.0'}, timeout=10)
resp.encoding = 'gb2312'
soup = BeautifulSoup(resp.text, 'html.parser')
rows = soup.select('tr')[:8]
for row in rows:
    cols = [td.get_text(strip=True) for td in row.find_all('td')]
    print(repr(cols))