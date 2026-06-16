#!/usr/bin/env python3
"""Patch api_server.py - replace AI_CONFIG/AI_SYSTEM_PROMPT/call_deepseek with import from ai_client"""
import re

with open('api_server.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Find AI_CONFIG = { ... call_deepseek function end
idx1 = content.find('\nAI_CONFIG = {')
if idx1 == -1:
    idx1 = content.find('AI_CONFIG = {')
    
# Find end of call_deepseek function (next def after it)
idx2 = content.find('\ndef expand_combo(', idx1)
if idx2 == -1:
    # fallback: find next function
    idx2 = content.find('\ndef ', idx1 + 1)
    # skip past call_deepseek, look for expand_combo
    idx3 = content.find('\ndef ', idx2 + 1)
    idx2 = idx3 if idx3 > idx2 else idx2

# Include the trailing blank lines
old = content[idx1:idx2]

new_text = """
from ai_client import call_deepseek, AI_SYSTEM_PROMPT, AI_CONFIG

def expand_combo(front_pool, back_pool, front_count, back_count):
    if front_count < 5: front_count = 5
    if front_count > len(front_pool): front_count = len(front_pool)
    if back_count < 2: back_count = 2
    if back_count > len(back_pool): back_count = len(back_pool)
    top_f = front_pool[:front_count]
    top_b = back_pool[:back_count]
    combos = []
    for fi in combinations(range(front_count), 5):
        for bi in combinations(range(back_count), 2):
            combos.append({
                'front': sorted([top_f[i] for i in fi]),
                'back': sorted([top_b[i] for i in bi])
            })
    return {
        'combos': combos,
        'count': len(combos),
        'cost': len(combos) * 2,
        'front_pool': top_f,
        'back_pool': top_b,
        'type': "{}"+str(front_count)+"+"+str(back_count)
    }
""".lstrip('\n')

content = content[:idx1] + '\n' + new_text + content[idx2:]

with open('api_server.py', 'w', encoding='utf-8') as f:
    f.write(content)

print(f'Patch applied: replaced {len(old)} bytes with import block')
