content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
# Check if the functions are defined in JS
idx_onclick = content.find(b'onclick="copyAIPred')
idx_js_def = content.find(b'async function copyAIPred')
print('onclick at:', idx_onclick)
print('JS definition at:', idx_js_def)
if idx_onclick >= 0:
    print('onclick context:', repr(content[idx_onclick-30:idx_onclick+40]))
if idx_js_def >= 0:
    print('JS def context:', repr(content[idx_js_def:idx_js_def+200]))
