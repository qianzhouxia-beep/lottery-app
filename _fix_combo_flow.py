import re, os, sys

# Force UTF-8 output
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

h = os.path.join('D:\\AI\\lottery-app', 'web', 'index.html')
with open(h, 'r', encoding='utf-8') as f:
    c = f.read()

# Find doPredict function
idx = c.find('async function doPredict')
end = c.find('\nasync function', idx + 5)
if end < 0:
    end = c.find('\nfunction', idx + 5)
if end < 0:
    end = len(c)

body = c[idx:end]
lines = body.split('\n')

print('doPredict function (%d lines):' % len(lines))
for i, line in enumerate(lines[:40], start=1):
    print('%3d: %s' % (i, line[:200]))
