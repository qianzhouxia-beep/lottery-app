"""
Patch the frontend index.html to:
1. Add combo selector HTML after predictContent div
2. Replace doPredict() with AI-based implementation
3. Add renderPredCardAI() function
4. Fix copyNumbers/saveFav for AI format
"""
import re

content = open('D:/AI/lottery-app/web/index.html', 'rb').read()
print('File size:', len(content))

# ============================================================
# 1. After <div id="predictContent"> add AI combo selector
# ============================================================
OLD_SKELETON_AFTER_CONTENT = (
    b'<div id="predictContent">\r\n'
    b'      <div class="skeleton" style="padding:16px;margin-bottom:12px;">\r\n'
    b'        <div class="skeleton-text narrow" style="margin-bottom:12px;height:12px;"></div>\r\n'
    b'        <div style="display:flex;justify-content:center;gap:6px;margin:12px 0;">\r\n'
    b'          <div class="skeleton-ball"></div><div class="skeleton-ball"></div>\r\n'
    b'          <div class="skeleton-ball"></div><div class="skeleton-ball"></div>\r\n'
    b'          <div class="skeleton-ball"></div>\r\n'
    b'        </div>\r\n'
    b'      </div>'
)

NEW_SKELETON_AFTER_CONTENT = (
    b'<div id="predictContent">\r\n'
    b'      <div class="glass-card" style="padding:12px 16px;margin-bottom:12px;">\r\n'
    b'        <div style="display:flex;align-items:center;justify-content:space-between;flex-wrap:wrap;gap:8px;">\r\n'
    b'          <div style="display:flex;align-items:center;gap:8px;">\r\n'
    b'            <span style="font-size:12px;color:var(--text-secondary);">AI</span>\r\n'
    b'            <select id="fcSelect" onchange="doPredict()" style="background:var(--bg-secondary);border:1px solid var(--border);border-radius:6px;padding:4px 8px;color:var(--text-primary);font-size:13px;">\r\n'
    b'              <option value="5">5+2 (&#x00A52;&#x5143;)</option>\r\n'
    b'              <option value="6" selected>6+2 (&#x00A56;&#x5143;)</option>\r\n'
    b'              <option value="7">7+2 (&#x00A521;&#x5143;)</option>\r\n'
    b'              <option value="8">8+2 (&#x00A528;&#x5143;)</option>\r\n'
    b'            </select>\r\n'
    b'            <span style="font-size:11px;color:var(--text-muted);" id="comboCost">6&#x6D3E;&#x00A512;&#x5143;</span>\r\n'
    b'          </div>\r\n'
    b'          <div style="font-size:11px;color:var(--text-muted);" id="aiModelTag">Hermes AI</div>\r\n'
    b'        </div>\r\n'
    b'      </div>\r\n'
    b'      <div class="skeleton" style="padding:16px;margin-bottom:12px;">\r\n'
    b'        <div class="skeleton-text narrow" style="margin-bottom:12px;height:12px;"></div>\r\n'
    b'        <div style="display:flex;justify-content:center;gap:6px;margin:12px 0;">\r\n'
    b'          <div class="skeleton-ball"></div><div class="skeleton-ball"></div>\r\n'
    b'          <div class="skeleton-ball"></div><div class="skeleton-ball"></div>\r\n'
    b'          <div class="skeleton-ball"></div>\r\n'
    b'        </div>\r\n'
    b'      </div>'
)

if OLD_SKELETON_AFTER_CONTENT in content:
    content = content.replace(OLD_SKELETON_AFTER_CONTENT, NEW_SKELETON_AFTER_CONTENT, 1)
    print('Patched: combo selector added after predictContent')
else:
    print('WARNING: predictContent skeleton pattern not found!')

# ============================================================
# 2. Replace doPredict() function - find it first
# ============================================================
# The skeleton inside doPredict
OLD_DOPREDICT_SKELETON = (
    b"  const content = document.getElementById('predictContent');\r\n"
    b"  content.innerHTML = `\r\n"
    b"    <div class=\"skeleton\" style=\"padding:16px;margin-bottom:12px;\">\r\n"
    b"      <div class=\"skeleton-text narrow\" style=\"margin-bottom:12px;height:12px;\"></div>\r\n"
    b"      <div style=\"display:flex;justify-content:center;gap:6px;margin:12px 0;\">\r\n"
    b"        <div class=\"skeleton-ball\"></div><div class=\"skeleton-ball\"></div>\r\n"
    b"        <div class=\"skeleton-ball\"></div><div class=\"skeleton-ball\"></div>\r\n"
    b"        <div class=\"skeleton-ball\"></div>\r\n"
    b"      </div>\r\n"
    b"    </div>`;"
)

NEW_DOPREDICT_BODY = (
    b"  const content = document.getElementById('predictContent');\r\n"
    b"  const fc = parseInt(document.getElementById('fcSelect').value) || 5;\r\n"
    b"  const bc = 2;\r\n"
    b"  // Update cost display\r\n"
    b"  const comboCosts = {5: ['1','2'], 6: ['6','12'], 7: ['21','42'], 8: ['56','112']};\r\n"
    b"  const costs = comboCosts[fc] || ['1','2'];\r\n"
    b"  document.getElementById('comboCost').textContent = fc + '+' + bc + ' \\u3010' + costs[0] + '\\u6D3E \\u00A5' + costs[1] + '\\u5143\\u3011';\r\n"
    b"  document.getElementById('aiModelTag').textContent = 'Hermes AI (DeepSeek)';\r\n"
    b"  // Show skeleton\r\n"
    b"  const skel = content.querySelector('.skeleton') || document.createElement('div');\r\n"
    b"  if (!skel.classList.contains('skeleton')) {\r\n"
    b"    skel.className = 'skeleton';\r\n"
    b"    skel.style.cssText = 'padding:16px;margin-bottom:12px;';\r\n"
    b"    skel.innerHTML = '<div class=\"skeleton-text narrow\" style=\"margin-bottom:12px;height:12px;\"></div><div style=\"display:flex;justify-content:center;gap:6px;margin:12px 0;\"><div class=\"skeleton-ball\"></div><div class=\"skeleton-ball\"></div><div class=\"skeleton-ball\"></div><div class=\"skeleton-ball\"></div><div class=\"skeleton-ball\"></div></div>';\r\n"
    b"    content.appendChild(skel);\r\n"
    b"  }\r\n"
    b"  // Call AI predict endpoint\r\n"
    b"  const data = await api('predict_ai?kind=' + currentKind + '&fc=' + fc + '&bc=' + bc);\r\n"
    b"  if (data.error) {\r\n"
    b"    content.innerHTML = `\r\n"
    b"      <div class=\"glass-card\" style=\"text-align:center;padding:30px;\">\r\n"
    b"        <div style=\"color:var(--error);font-size:14px;margin-bottom:8px;\">\\u52A0\\u8F7D\\u5931\\u8D25</div>\r\n"
    b"        <div style=\"font-size:12px;color:var(--text-muted);\">\\u8BF7\\u68C0\\u67E5\\u670D\\u52A1\\u5668</div>\r\n"
    b"      </div>`;\r\n"
    b"    return;\r\n"
    b"  }\r\n"
    b"  document.getElementById('predictPeriod').textContent = '\\u7B2C ' + data.for_period + ' \\u671F';\r\n"
    b"  document.getElementById('predictTime').textContent = data.generated_at || '';\r\n"
    b"  renderPredCardAI(data, content, fc, bc);\r\n"
    b"  loadReviewHistory();\r\n"
    b"}"
)

if OLD_DOPREDICT_SKELETON in content:
    content = content.replace(OLD_DOPREDICT_SKELETON, NEW_DOPREDICT_BODY, 1)
    print('Patched: doPredict() skeleton replaced with AI version')
else:
    print('WARNING: doPredict skeleton pattern not found at expected position')

# ============================================================
# 3. Add renderPredCardAI() function after renderPredCard()
# ============================================================
RENDERPREDCARD_END_MARKER = (
    b"      </div>\r\n"
    b"    </div>`;\r\n"
    b"}\r\n"
)

RENDERPREDCARD_AI_FUNC = (
    b"      </div>\r\n"
    b"    </div>`;\r\n"
    b"}\r\n"
    b"\r\n"
    b"/* ============================================================\r\n"
    b"   Render: AI Prediction Card (Hermes v4)\r\n"
    b"   ============================================================ */\r\n"
    b"async function renderPredCardAI(data, content, fc, bc) {\r\n"
    b"  // Remove skeleton\r\n"
    b"  const skel = content.querySelector('.skeleton');\r\n"
    b"  if (skel) skel.remove();\r\n"
    b"  const pred = data.prediction;\r\n"
    b"  const rev = data.reverse;\r\n"
    b"  const analysis = data.analysis;\r\n"
    b"  const combo = data.combo;\r\n"
    b"  const ranked = data.ranked_front || [];\r\n"
    b"  const ranked_b = data.ranked_back || [];\r\n"
    b"\r\n"
    b"  // Build hot/cold HTML\r\n"
    b"  const hotF = (analysis.hot_front || []).slice(0,6).map(n => `<span class=\"tag front\">${n}</span>`).join('');\r\n"
    b"  const coldF = (analysis.cold_front || []).slice(0,6).map(n => `<span class=\"tag\" style=\"background:rgba(100,100,100,0.3);color:var(--text-secondary);\">${n}</span>`).join('');\r\n"
    b"  const hotB = (analysis.hot_back || []).slice(0,4).map(n => `<span class=\"tag back\">${n}</span>`).join('');\r\n"
    b"  const coldB = (analysis.cold_back || []).slice(0,4).map(n => `<span class=\"tag\" style=\"background:rgba(100,100,100,0.3);color:var(--text-secondary);\">${n}</span>`).join('');\r\n"
    b"\r\n"
    b"  // Trend tag\r\n"
    b"  const trendTag = analysis.trend ? `<span style=\"font-size:11px;color:var(--primary);background:rgba(192,193,255,0.1);padding:2px 8px;border-radius:10px;\">\\u2714 ${analysis.trend}</span>` : '';\r\n"
    b"\r\n"
    b"  // Sum range badge\r\n"
    b"  const sumRange = analysis.sum_range ? `<span style=\"font-size:11px;padding:2px 8px;background:rgba(255,179,173,0.1);color:#ffb3ad;border-radius:10px;\">\\u548C\\u503C ${analysis.sum_range}</span>` : '';\r\n"
    b"\r\n"
    b"  // Top 10 ranked front list (confidence bars)\r\n"
    b"  const rankedHTML = ranked.slice(0, 10).map(n => {\r\n"
    b"    const pct = Math.round((n.confidence || 0.5) * 100);\r\n"
    b"    const cls = pct >= 75 ? 'high' : pct >= 60 ? 'medium' : 'low';\r\n"
    b"    return `<div style=\"display:flex;align-items:center;gap:8px;padding:3px 0;\">\r\n"
    b"      <span style=\"width:18px;text-align:right;font-size:12px;font-family:var(--font-mono);\">${n.num}</span>\r\n"
    b"      <div style=\"flex:1;height:4px;background:rgba(255,255,255,0.1);border-radius:2px;\">\r\n"
    b"        <div style=\"width:${pct}%;height:100%;border-radius:2px;\" class=\"conf-${cls}\"></div>\r\n"
    b"      </div>\r\n"
    b"      <span style=\"font-size:10px;color:var(--text-muted);width:28px;text-align:right;\">${pct}%</span>\r\n"
    b"    </div>`;\r\n"
    b"  }).join('');\r\n"
    b"\r\n"
    b"  // Normal prediction card\r\n"
    b"  const normalBalls = (pred.front||[]).map(n => `<div class=\"ball front size-md\">${n}</div>`).join('');\r\n"
    b"  const normalBackBalls = (pred.back||[]).map(n => `<div class=\"ball back size-md\">${n}</div>`).join('');\r\n"
    b"  const normalHTML = `\r\n"
    b"    <div class=\"pred-card normal\">\r\n"
    b"      <div class=\"pred-card-header\">\r\n"
    b"        <div class=\"pred-card-title\"><div class=\"dot\"></div>\\u6B63\\u9009 (\\u71B1\\u53F7\\u7B56\\u7565)</div>\r\n"
    b"        <span class=\"pred-card-label\">\\u7B5B\\u4FE1\\u5EA6 82%</span>\r\n"
    b"      </div>\r\n"
    b"      <div class=\"confidence-bar\"><div class=\"confidence-fill high\" style=\"width:82%\"></div></div>\r\n"
    b"      <div class=\"balls-row\" style=\"margin:14px 0;\">\r\n"
    b"        ${normalBalls}\r\n"
    b"        <div class=\"ball sep\" style=\"width:16px;\">+</div>\r\n"
    b"        ${normalBackBalls}\r\n"
    b"      </div>\r\n"
    b"      <div class=\"pred-meta\" style=\"flex-wrap:wrap;gap:4px;\">\r\n"
    b"        ${trendTag} ${sumRange}\r\n"
    b"      </div>\r\n"
    b"      <div style=\"font-size:11px;color:var(--text-secondary);margin:8px 0;padding:8px;background:rgba(192,193,255,0.05);border-radius:8px;\">\r\n"
    b"        <span style=\"color:var(--primary);font-weight:600;\">\\u5206\\u6790:</span> ${pred.reason || '\\u71B1\\u53F7\\u5EF6\\u7EED\\uFF0C\\u51B7\\u53F7\\u56DE\\u8865'}</div>\r\n"
    b"      <div class=\"btn-row\">\r\n"
    b"        <button class=\"btn-secondary\" style=\"flex:1;\" onclick=\"copyAIPred('normal')\">\r\n"
    b"          <span class=\"material-symbols-outlined\" style=\"font-size:15px;\">content_copy</span> \\u590D\\u5236\r\n"
    b"        </button>\r\n"
    b"        <button class=\"btn-secondary\" style=\"flex:1;\" onclick=\"saveFavAI('normal', data)\">\r\n"
    b"          <span class=\"material-symbols-outlined\" style=\"font-size:15px;\">favorite</span> \\u6536\\u85CF\r\n"
    b"        </button>\r\n"
    b"      </div>\r\n"
    b"    </div>`;\r\n"
    b"\r\n"
    b"  // Reverse prediction card\r\n"
    b"  const revBalls = (rev.front||[]).map(n => `<div class=\"ball\" style=\"background:rgba(100,100,100,0.3);color:var(--text-secondary);font-size:18px;width:36px;height:36px;border-radius:50%;display:flex;align-items:center;justify-content:center;\">${n}</div>`).join('');\r\n"
    b"  const revBackBalls = (rev.back||[]).map(n => `<div class=\"ball back size-md\">${n}</div>`).join('');\r\n"
    b"  const reverseHTML = `\r\n"
    b"    <div class=\"pred-card reverse\">\r\n"
    b"      <div class=\"pred-card-header\">\r\n"
    b"        <div class=\"pred-card-title\"><div class=\"dot\" style=\"background:var(--warning)\"></div>\\u53CD\\u9009 (\\u51B7\\u53F7\\u7B56\\u7565)</div>\r\n"
    b"        <span class=\"pred-card-label\">\\u7B5B\\u4FE1\\u5EA6 61%</span>\r\n"
    b"      </div>\r\n"
    b"      <div class=\"confidence-bar\"><div class=\"confidence-fill medium\" style=\"width:61%\"></div></div>\r\n"
    b"      <div class=\"balls-row\" style=\"margin:14px 0;\">\r\n"
    b"        ${revBalls}\r\n"
    b"        <div class=\"ball sep\" style=\"width:16px;\">+</div>\r\n"
    b"        ${revBackBalls}\r\n"
    b"      </div>\r\n"
    b"      <div style=\"font-size:11px;color:var(--text-secondary);margin:8px 0;padding:8px;background:rgba(255,179,173,0.05);border-radius:8px;\">\r\n"
    b"        <span style=\"color:#ffb3ad;font-weight:600;\">\\u5206\\u6790:</span> ${rev.reason || '\\u51B7\\u53F7\\u53CD\\u5E38\\uFF0C\\u907F\\u5F00\\u70ED\\u53F7'}</div>\r\n"
    b"      <div class=\"btn-row\">\r\n"
    b"        <button class=\"btn-secondary\" style=\"flex:1;\" onclick=\"copyAIPred('reverse')\">\r\n"
    b"          <span class=\"material-symbols-outlined\" style=\"font-size:15px;\">content_copy</span> \\u590D\\u5236\r\n"
    b"        </button>\r\n"
    b"        <button class=\"btn-secondary\" style=\"flex:1;\" onclick=\"saveFavAI('reverse', data)\">\r\n"
    b"          <span class=\"material-symbols-outlined\" style=\"font-size:15px;\">favorite</span> \\u6536\\u85CF\r\n"
    b"        </button>\r\n"
    b"      </div>\r\n"
    b"    </div>`;\r\n"
    b"\r\n"
    b"  // Hot/cold analysis card\r\n"
    b"  const analysisHTML = `\r\n"
    b"    <div class=\"glass-card\" style=\"margin-bottom:12px;\">\r\n"
    b"      <div style=\"font-size:12px;font-weight:600;margin-bottom:10px;color:var(--text-secondary);\">\\u2705 \\u70ED\\u51B7\\u5206\\u6790</div>\r\n"
    b"      <div style=\"margin-bottom:8px;\">\r\n"
    b"        <div style=\"font-size:11px;color:var(--primary);margin-bottom:4px;\">\\u524D\\u533A \\u70ED\\u53F7: ${hotF}</div>\r\n"
    b"        <div style=\"font-size:11px;color:var(--text-muted);\">\\u524D\\u533A \\u51B7\\u53F7: ${coldF}</div>\r\n"
    b"      </div>\r\n"
    b"      <div style=\"margin-bottom:8px;\">\r\n"
    b"        <div style=\"font-size:11px;color:#ffb3ad;margin-bottom:4px;\">\\u540E\\u533A \\u70ED\\u53F7: ${hotB}</div>\r\n"
    b"        <div style=\"font-size:11px;color:var(--text-muted);\">\\u540E\\u533A \\u51B7\\u53F7: ${coldB}</div>\r\n"
    b"      </div>\r\n"
    b"      <div style=\"margin-bottom:8px;\">\r\n"
    b"        <div style=\"font-size:11px;color:var(--text-secondary);margin-bottom:4px;\">\\u524D\\u533A\\u4F53\\u8BCA\\u503C (Top 10)</div>\r\n"
    b"        ${rankedHTML}\r\n"
    b"      </div>\r\n"
    b"      ${combo && combo.count > 1 ? `<div style=\"margin-top:10px;padding:10px;background:rgba(192,193,255,0.08);border-radius:8px;\">\r\n"
    b"        <div style=\"font-size:11px;color:var(--primary);margin-bottom:4px;\">\\u590D\\u5F0F\\u6295\\u6CE8 (${combo.type})</div>\r\n"
    b"        <div style=\"font-size:11px;color:var(--text-secondary);\">\\u5171 <strong style=\"color:var(--text-primary)\">${combo.count}</strong> \\u6CE8\\uFF0C\\u9884\\u8BA1 <strong style=\"color:var(--warning)\">${combo.cost}\\u5143</strong></div>\r\n"
    b"        <div style=\"font-size:10px;color:var(--text-muted);margin-top:4px;\">\\u524D\\u533A\\u5019\\u9009: [${(combo.front_pool||[]).join(', ')}]</div>\r\n"
    b"        <div style=\"font-size:10px;color:var(--text-muted);\">\\u540E\\u533A\\u5019\\u9009: [${(combo.back_pool||[]).join(', ')}]</div>\r\n"
    b"      </div>` : ''}\r\n"
    b"    </div>`;\r\n"
    b"\r\n"
    b"  content.innerHTML = normalHTML + reverseHTML + analysisHTML;\r\n"
    b"}"
)

if RENDERPREDCARD_END_MARKER in content:
    content = content.replace(RENDERPREDCARD_END_MARKER, RENDERPREDCARD_AI_FUNC, 1)
    print('Patched: renderPredCardAI() added after renderPredCard()')
else:
    print('WARNING: renderPredCard end marker not found!')

# ============================================================
# 4. Add copyAIPred and saveFavAI functions after saveFav()
# ============================================================
SAVEFAV_END = (
    b"    showToast('\\u6536\\u85CF\\u5931\\u8D25');\r\n"
    b"  }\r\n"
    b"}\r\n"
)

AIPRED_FUNCS = (
    b"    showToast('\\u6536\\u85CF\\u5931\\u8D25');\r\n"
    b"  }\r\n"
    b"}\r\n"
    b"\r\n"
    b"/* ============================================================\r\n"
    b"   AI Copy & Save (for Hermes AI predictions)\r\n"
    b"   ============================================================ */\r\n"
    b"let lastAIData = null;\r\n"
    b"\r\n"
    b"async function copyAIPred(type) {\r\n"
    b"  if (!lastAIData) {\r\n"
    b"    showToast('\\u6CA1\\u6709\\u53EF\\u590D\\u5236\\u7684\\u9884\\u6D4B\\u6570\\u636E');\r\n"
    b"    return;\r\n"
    b"  }\r\n"
    b"  const src = type === 'normal' ? lastAIData.prediction : lastAIData.reverse;\r\n"
    b"  const front = (src.front || []).join(' ');\r\n"
    b"  const back = (src.back || []).join(' ');\r\n"
    b"  const text = '\\u524D\\u533A: ' + front + '  \\u540E\\u533A: ' + back;\r\n"
    b"  try {\r\n"
    b"    await navigator.clipboard.writeText(text);\r\n"
    b"    showToast('\\u5DF2\\u590D\\u5236\\u5230\\u526A\\u8D34\\u677F');\r\n"
    b"  } catch(e) { showToast('\\u590D\\u5236\\u5931\\u8D25'); }\r\n"
    b"}\r\n"
    b"\r\n"
    b"async function saveFavAI(type, data) {\r\n"
    b"  lastAIData = data;\r\n"
    b"  const src = type === 'normal' ? data.prediction : data.reverse;\r\n"
    b"  try {\r\n"
    b"    const favs = JSON.parse(localStorage.getItem('lottery_favs') || '[]');\r\n"
    b"    favs.unshift({\r\n"
    b"      kind: currentKind, type: 'AI-' + type,\r\n"
    b"      front: (src.front || []).join(','),\r\n"
    b"      back: (src.back || []).join(','),\r\n"
    b"      period: data.for_period,\r\n"
    b"      model: 'Hermes AI',\r\n"
    b"      time: new Date().toISOString()\r\n"
    b"    });\r\n"
    b"    localStorage.setItem('lottery_favs', JSON.stringify(favs.slice(0, 50)));\r\n"
    b"    showToast('\\u5DF2\\u6536\\u85CF');\r\n"
    b"  } catch(e) { showToast('\\u6536\\u85CF\\u5931\\u8D25'); }\r\n"
    b"}\r\n"
)

if SAVEFAV_END in content:
    content = content.replace(SAVEFAV_END, AIPRED_FUNCS, 1)
    print('Patched: copyAIPred and saveFavAI added after saveFav()')
else:
    print('WARNING: saveFav end not found!')

# ============================================================
# 5. Fix copyNumbers and saveFav to use predict_ai endpoint
# ============================================================
OLD_COPYNUMBERS_API = b"const preds = await api('predict');"
NEW_COPYNUMBERS_API = b"const preds = await api('predict_ai?kind=' + currentKind + '&fc=5&bc=2');"

if OLD_COPYNUMBERS_API in content:
    content = content.replace(OLD_COPYNUMBERS_API, NEW_COPYNUMBERS_API, 1)
    print('Patched: copyNumbers fixed for AI endpoint')
else:
    print('WARNING: copyNumbers API call not found')

OLD_SAVEFAV_API = b"const preds = await api('predict');"
NEW_SAVEFAV_API = b"const preds = await api('predict_ai?kind=' + currentKind + '&fc=5&bc=2');"

if OLD_SAVEFAV_API in content:
    content = content.replace(OLD_SAVEFAV_API, NEW_SAVEFAV_API, 1)
    print('Patched: saveFav fixed for AI endpoint')
else:
    print('WARNING: saveFav API call not found')

# Fix the data access in copyNumbers/saveFav (they use preds.find)
OLD_PREDS_FIND = b"const pred = (preds.predictions || []).find(p => p.type === type);"
NEW_PREDS_FIND = (
    b"const pred = type === 'normal' ? preds.prediction : preds.reverse;"
    b"if (!pred) return;"
)

if OLD_PREDS_FIND in content:
    content = content.replace(OLD_PREDS_FIND, NEW_PREDS_FIND, 2)  # 2 occurrences
    print('Patched: preds.find replaced with direct property access')
else:
    print('WARNING: preds.find pattern not found')

# Write output
with open('D:/AI/lottery-app/web/index.html', 'wb') as f:
    f.write(content)
print('Done! New size:', len(content))
