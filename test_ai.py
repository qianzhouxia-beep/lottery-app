import urllib.request, json, urllib.parse

url = 'http://localhost:5123/api/predict_ai?' + urllib.parse.urlencode({'kind': 'dlt', 'fc': 5, 'bc': 2})
req = urllib.request.Request(url)
with urllib.request.urlopen(req, timeout=30) as resp:
    data = json.loads(resp.read())

print('=== PREDICTION ===')
p = data['prediction']
print(f'Front: {p["front"]}')
print(f'Back: {p["back"]}')
print(f'Reason: {p["reason"]}')
print()
print('=== REVERSE ===')
r = data['reverse']
print(f'Front: {r["front"]}')
print(f'Back: {r["back"]}')
print(f'Reason: {r["reason"]}')
print()
print('=== COMBO ===')
print(json.dumps(data.get('combo', {}), indent=2, ensure_ascii=False))
print()
print('=== HOT FRONT ===')
print(data['analysis']['hot_front'])
print('=== COLD FRONT ===')
print(data['analysis']['cold_front'])
print('=== RANKED FRONT (top 10) ===')
for n in data['ranked_front'][:10]:
    print(f"  {n['num']:>2}: {n['confidence']:.2f}")
