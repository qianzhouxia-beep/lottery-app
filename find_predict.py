import re

content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
print('Size:', len(content))

# Find predict-related functions
for pat in [b'predict', b'fetchDlt', b'fetchSsq', b'getDlt', b'getSsq']:
    for m in re.finditer(re.escape(pat), content):
        start = max(0, m.start()-40)
        end = min(len(content), m.end()+80)
        snippet = content[start:end]
        print('Found %s at pos %d: %r' % (pat, m.start(), snippet))
        print('---')
