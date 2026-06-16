content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
# Add lastAIData = null before copyAIPred if not present
if b'let lastAIData' not in content:
    marker = b'async function copyAIPred'
    replacement = b'let lastAIData = null;\r\n\r\nasync function copyAIPred'
    if marker in content:
        content = content.replace(marker, replacement, 1)
        print('Added lastAIData = null')
    else:
        print('ERROR: copyAIPred not found')
else:
    print('lastAIData already exists')

with open('D:/AI/lottery-app/web/index.html', 'wb') as f:
    f.write(content)
print('Done. Size:', len(content))
