import re

with open('hermes_learner.py', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "STRATEGIES = ['pure_stats', 'hybrid']",
    "STRATEGIES = ['pure_stats', 'hybrid', 'xgb', 'hybrid_xgb']"
)

with open('hermes_learner.py', 'w', encoding='utf-8') as f:
    f.write(content)

print('OK')
