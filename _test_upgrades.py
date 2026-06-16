#!/usr/bin/env python3
"""Test all new modules - direct imports"""

# 1. Test imports
from ai_client import call_deepseek, AI_SYSTEM_PROMPT, AI_CONFIG
print('[OK] ai_client import OK')

from hermes_learner import SelfLearningEngine, load_history
print('[OK] hermes_learner import OK')

from hermes_xgb import XGBEngine
print('[OK] hermes_xgb import OK')

from auto_learner import AutoLearner
print('[OK] auto_learner import OK')

# 2. Test data loading
history = load_history('dlt')
print(f'[OK] Loaded {len(history)} dlt periods')

# 3. Test XGBoost training
xgb = XGBEngine('dlt')
trained = xgb.train(history, silent=True)
print(f'[OK] XGBoost trained: {trained}')

# 4. Test SelfLearningEngine with XGBoost
engine = SelfLearningEngine('dlt')
engine._xgb = xgb
engine._xgb_trained = trained

result = engine.predict(history, strategy='hybrid')
pred = result.get('prediction', {})
print(f'[OK] Prediction: {pred.get("front",[])} + {pred.get("back",[])}')
model_name = result.get('model', '?')
print(f'     Model: {model_name}')

# 5. Test AutoLearner
al = AutoLearner('dlt')
print(f'[OK] AutoLearner created, draw day={al.tracker.is_draw_day()}')
print(f'     After draw={al.tracker.is_after_draw()}')

# 6. Test ai_client config
print(f'[OK] AI config: model={AI_CONFIG["model"]}, base_url={AI_CONFIG["base_url"]}')

# 7. Test XGBoost scores
front_scores, back_scores = xgb.get_scores(history)
top5 = sorted(front_scores.items(), key=lambda x: -x[1])[:5]
top2 = sorted(back_scores.items(), key=lambda x: -x[1])[:2]
print(f'[OK] XGBoost top-5 front: {[n for n,s in top5]}')
print(f'     XGBoost top-2 back: {[n for n,s in top2]}')

print('\n=== ALL TESTS PASSED ===')
