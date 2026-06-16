content = open('D:/AI/lottery-app/web/index.html', 'rb').read()

# Find the orphaned old doPredict code
old_doPredict_start = content.find(b'  const data = await api(\'predict\');\r\n\r\n  if (data.error)')
old_doPredict_end = content.find(b'\r\nfunction renderPredCard(pred, type)', old_doPredict_start)

if old_doPredict_start >= 0 and old_doPredict_end >= 0:
    orphaned = content[old_doPredict_start:old_doPredict_end]
    print('Found orphaned old doPredict code (%d bytes):' % len(orphaned))
    print(repr(orphaned[:200]))
    content = content[:old_doPredict_start] + content[old_doPredict_end:]
    print('Removed orphaned code')
    with open('D:/AI/lottery-app/web/index.html', 'wb') as f:
        f.write(content)
    print('Written. New size:', len(content))
else:
    print('Pattern not found')
    # Try to find what is there
    idx = content.find(b"const data = await api('predict')")
    if idx >= 0:
        print('Found at pos %d: %r' % (idx, content[idx:idx+200]))
    idx2 = content.find(b'function renderPredCard(pred, type)')
    if idx2 >= 0:
        print('renderPredCard at pos %d: %r' % (idx2, content[idx2:idx2+50]))
