import re, os, sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

h = os.path.join('D:\\AI\\lottery-app', 'web', 'index.html')
with open(h, 'r', encoding='utf-8') as f:
    c = f.read()

# Find switchTab for predict case
idx = c.find("case 'predict'")
snippet = c[idx:idx+500]
print('predict case:')
print(snippet[:400])
print()

# Find initPicker call
init_calls = [(m.start(), c[max(0,m.start()-100):m.start()+200]) for m in re.finditer(r'initPicker\(\)', c)]
print('initPicker() calls:', len(init_calls))
for pos, ctx in init_calls:
    print(f'  pos {pos}: ...{repr(ctx[-80:])}')
