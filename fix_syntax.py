#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Fix template literal syntax error in index.html"""

import re

with open('web/index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# The broken pattern - find and replace the entire showReviewManual function
old_pattern = r'''function showReviewManual\(type\) \{
  const resultArea = document\.getElementById\('reviewResultArea'\);
  const src = type === 'normal' \? lastAIData\.prediction : lastAIData\.reverse;
  const pf = \(src\.front \|\| \[\]\), pb = \(src\.back \|\| \[\]\);
  resultArea\.innerHTML = `[\s\S]*?`;
\}'''

new_func = '''function showReviewManual(type) {
  const resultArea = document.getElementById('reviewResultArea');
  const src = type === 'normal' ? lastAIData.prediction : lastAIData.reverse;
  const pf = (src.front || []), pb = (src.back || []);
  const frontVal = pf.join(' ');
  const backVal = pb.join(' ');
  resultArea.innerHTML = '<div style="margin-top:12px;padding:12px;background:var(--surface-container-low);border-radius:10px;">'
    + '<div style="font-size:11px;color:var(--text-muted);margin-bottom:8px;">输入开奖号码 (空格分隔)</div>'
    + '<div style="margin-bottom:8px;"><input id="manualFrontInput" type="text" placeholder="前区, 例: 4 11 12 13 25" value="' + frontVal + '" style="width:100%;padding:8px 10px;background:var(--surface-container);border:1px solid var(--border-subtle);border-radius:8px;color:var(--text-primary);font-family:var(--font-mono);font-size:13px;box-sizing:border-box;outline:none;"></div>'
    + '<div style="margin-bottom:10px;"><input id="manualBackInput" type="text" placeholder="后区, 例: 4 8" value="' + backVal + '" style="width:100%;padding:8px 10px;background:var(--surface-container);border:1px solid var(--border-subtle);border-radius:8px;color:var(--text-primary);font-family:var(--font-mono);font-size:13px;box-sizing:border-box;outline:none;"></div>'
    + '<button onclick="submitManualReview(\\'' + type + '\\')" class="btn-primary" style="width:100%;justify-content:center;">'
    + '<span class="material-symbols-outlined" style="font-size:16px;">check_circle</span> 确认复盘'
    + '</button></div>';
}'''

# Find the function
match = re.search(old_pattern, content)
if match:
    print(f"Found function at position {match.start()}-{match.end()}")
    content = content[:match.start()] + new_func + content[match.end():]
    with open('web/index.html', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Fixed!")
else:
    print("Pattern not found, trying line-by-line approach...")
    lines = content.split('\n')
    for i, line in enumerate(lines):
        if 'function showReviewManual' in line:
            print(f"Found at line {i+1}")
            # Find the closing brace
            brace_count = 0
            start_i = i
            for j in range(i, min(i+20, len(lines))):
                brace_count += lines[j].count('{')
                brace_count -= lines[j].count('}')
                if brace_count == 0 and j > i:
                    print(f"Function ends at line {j+1}")
                    # Replace lines i to j
                    new_lines = lines[:i] + new_func.split('\n') + lines[j+1:]
                    with open('web/index.html', 'w', encoding='utf-8') as f:
                        f.write('\n'.join(new_lines))
                    print("Fixed with line approach!")
                    break
            break
