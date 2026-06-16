content = open('D:/AI/lottery-app/web/index.html', 'rb').read()

# Find the Render: Trend marker
trend_marker = b'/* ============================================================\r\n   Render: Trend\r\n   ============================================================ */'
pos = content.find(trend_marker)
print('Render: Trend at:', pos)

if pos < 0:
    print('ERROR: Render: Trend not found')
else:
    ai_block = (
        b'/* ============================================================\r\n'
        b'   AI Copy & Save (for Hermes AI predictions)\r\n'
        b'   ============================================================ */\r\n'
        b'let lastAIData = null;\r\n'
        b'\r\n'
        b'async function copyAIPred(type) {\r\n'
        b"  if (!lastAIData) {\r\n"
        b"    showToast('\\u6CA1\\u6709\\u53EF\\u590D\\u5236\\u7684\\u9884\\u6D4B\\u6570\\u636E');\r\n"
        b'    return;\r\n'
        b'  }\r\n'
        b"  const src = type === 'normal' ? lastAIData.prediction : lastAIData.reverse;\r\n"
        b"  const front = (src.front || []).join(' ');\r\n"
        b"  const back = (src.back || []).join(' ');\r\n"
        b"  const text = '\\u524D\\u533A: ' + front + '  \\u540E\\u533A: ' + back;\r\n"
        b'  try {\r\n'
        b"    await navigator.clipboard.writeText(text);\r\n"
        b"    showToast('\\u5DF2\\u590D\\u5236\\u5230\\u526A\\u8D34\\u677F');\r\n"
        b'  } catch(e) { showToast(\'\\u590D\\u5236\\u5931\\u8D25\'); }\r\n'
        b'}\r\n'
        b'\r\n'
        b'async function saveFavAI(type, data) {\r\n'
        b'  lastAIData = data;\r\n'
        b"  const src = type === 'normal' ? data.prediction : data.reverse;\r\n"
        b'  try {\r\n'
        b"    const favs = JSON.parse(localStorage.getItem('lottery_favs') || '[]');\r\n"
        b"    favs.unshift({\r\n"
        b'      kind: currentKind,\r\n'
        b"      type: 'AI-' + type,\r\n"
        b"      front: (src.front || []).join(','),\r\n"
        b"      back: (src.back || []).join(','),\r\n"
        b'      period: data.for_period,\r\n'
        b"      model: 'Hermes AI',\r\n"
        b"      time: new Date().toISOString()\r\n"
        b'    });\r\n'
        b"    localStorage.setItem('lottery_favs', JSON.stringify(favs.slice(0, 50)));\r\n"
        b"    showToast('\\u5DF2\\u6536\\u85CF');\r\n"
        b'  } catch(e) { showToast(\'\\u6536\\u85CF\\u5931\\u8D25\'); }\r\n'
        b'}\r\n'
        b'\r\n'
    )
    
    content = content[:pos] + ai_block + content[pos:]
    print('Inserted AI functions before Render: Trend')
    with open('D:/AI/lottery-app/web/index.html', 'wb') as f:
        f.write(content)
    print('Written. New size:', len(content))
