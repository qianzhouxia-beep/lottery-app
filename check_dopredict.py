content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
idx = content.find(b'async function doPredict')
print(repr(content[idx:idx+500]))
