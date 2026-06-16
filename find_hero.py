content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
# Find predictContent
idx = content.find(b'id="predictContent"')
print('predictContent at:', idx)
print(repr(content[idx:idx+100]))
