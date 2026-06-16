import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

h = os.path.join('D:\\AI\\lottery-app', 'web', 'index.html')
with open(h, 'r', encoding='utf-8') as f:
    c = f.read()

# Find initPicker
idx = c.find('function initPicker')
end = c.find('\nasync function', idx + 5)
if end < 0:
    end = c.find('\nfunction', idx + 5)
if end < 0:
    end = len(c)
body = c[idx:end]
lines = body.split('\n')
print('initPicker (first 20 lines):')
for i, l in enumerate(lines[:20], 1):
    print('%3d: %s' % (i, l[:200]))
print()

# Find switchTab for predict tab
idx2 = c.find("case 'predict'")
end2 = c.find('\n  }', idx2 + 5)
body2 = c[idx2:end2]
lines2 = body2.split('\n')
print("switchTab predict case:")
for i, l in enumerate(lines2[:20], 1):
    print('%3d: %s' % (i, l[:200]))
