content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
# Check key new markers
checks = {
    'predict_ai endpoint call': b"api('predict_ai",
    'renderPredCardAI function': b'async function renderPredCardAI',
    'copyAIPred function': b'async function copyAIPred',
    'saveFavAI function': b'async function saveFavAI',
    'lastAIData variable': b'let lastAIData',
    'combo selector': b'fcSelect',
    'no old renderPredCard': b'function renderPredCard(',
    'no old doPredict predict': b"api('predict')",
}
for name, pat in checks.items():
    pos = content.find(pat)
    status = 'OK' if pos >= 0 else 'MISSING'
    print(f'{status}: {name} (pos {pos})')
print()
print('File size:', len(content))
