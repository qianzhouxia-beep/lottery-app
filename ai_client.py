#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Client - 共享 AI 客户端模块
=================================
从 api_server.py 提取，消除循环导入

用法：
  from ai_client import call_deepseek, AI_CONFIG, AI_SYSTEM_PROMPT
"""
import json, requests, sys, io
from pathlib import Path

# Windows UTF-8
# sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

BASE_DIR = Path(__file__).parent
DATA_DIR = BASE_DIR / 'data'
CONFIG_PATH = BASE_DIR / 'config.json'

# 从 config.json 加载配置
with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
    _CONFIG = json.load(f)

API_KEY = _CONFIG.get('api_key', '')
BASE_URL = _CONFIG.get('base_url', 'https://api-tokenmaster.com/v1')
MODEL = _CONFIG.get('model', 'deepseek-chat')

AI_CONFIG = {
    'api_key': API_KEY,
    'base_url': BASE_URL,
    'model': MODEL,
}


def reload_config():
    """
    重新从 config.json 加载配置（热更新，无需重启进程）
    更新后新请求立即使用新配置
    """
    global _CONFIG, API_KEY, BASE_URL, MODEL, AI_CONFIG
    try:
        with open(CONFIG_PATH, 'r', encoding='utf-8') as f:
            _CONFIG = json.load(f)
        API_KEY = _CONFIG.get('api_key', '')
        BASE_URL = _CONFIG.get('base_url', 'https://api.deepseek.com/v1')
        MODEL = _CONFIG.get('model', 'deepseek-chat')
        AI_CONFIG = {
            'api_key': API_KEY,
            'base_url': BASE_URL,
            'model': MODEL,
        }
        return {'success': True, 'api_key': API_KEY[:8] + '...', 'base_url': BASE_URL, 'model': MODEL}
    except Exception as e:
        return {'success': False, 'error': str(e)}

SYSTEM_PROMPT = '''你是一个专业的大乐透彩票预测专家。

输出严格JSON格式（不带任何其他文字）：
{
  "analysis": {
    "hot_front": [按热度排序的前区号码(最多10个)],
    "cold_front": [冷门号码(最多5个)],
    "hot_back": [后区热号(最多5个)],
    "cold_back": [后区冷号(最多3个)],
    "zone_distribution": {"S":1-12区数量,"M1":13-23区数量,"M2":24-29区数量,"M3":30-35区数量},
    "sum_range": "low/mid/high",
    "trend": "近期趋势描述（15字以内）"
  },
  "ranked_front": [{"num":号码,"confidence":置信度(0-1)}, ...],  // 按置信度降序排列的前区12个候选
  "ranked_back": [{"num":号码,"confidence":置信度(0-1)}, ...],    // 按置信度降序排列的后区6个候选
  "prediction": {
    "front": [5个正选前区号],
    "back": [2个正选后区号],
    "reason": "预测逻辑（20字以内）"
  },
  "reverse": {
    "front": [5个反选前区号（必须与正选完全不同）],
    "back": [2个反选后区号（必须与正选完全不同）],
    "reason": "反选逻辑（20字以内）"
  }
}'''

# 这个变量名兼容 api_server.py 中的引用
AI_SYSTEM_PROMPT = SYSTEM_PROMPT

def call_deepseek(system, user, max_tokens=800, temperature=0.0):
    """
    调用 DeepSeek API（通过 TokenMaster 代理）
    返回解析后的 JSON 或原始字符串
    """
    url = f"{BASE_URL}/chat/completions"
    headers = {
        'Authorization': f"Bearer {API_KEY}",
        'Content-Type': 'application/json',
    }
    payload = {
        'model': MODEL,
        'messages': [
            {'role': 'system', 'content': system},
            {'role': 'user', 'content': user},
        ],
        'max_tokens': max_tokens,
        'temperature': temperature,
        # 确保输出纯 JSON
        'response_format': {'type': 'json_object'},
    }
    
    try:
        resp = requests.post(url, headers=headers, json=payload, timeout=30)
        if resp.status_code != 200:
            return json.dumps({
                'error': f'API HTTP {resp.status_code}',
                'detail': resp.text[:200],
            })
        
        data = resp.json()
        content = data['choices'][0]['message']['content']
        return content
    except Exception as e:
        return json.dumps({'error': f'API call failed: {str(e)}'})


def update_config(new_api_key=None, new_base_url=None, new_model=None):
    """
    在线更新配置
    """
    global API_KEY, BASE_URL, MODEL
    
    config = dict(_CONFIG)
    if new_api_key:
        config['api_key'] = new_api_key
        API_KEY = new_api_key
        AI_CONFIG['api_key'] = new_api_key
    if new_base_url:
        config['base_url'] = new_base_url
        BASE_URL = new_base_url
        AI_CONFIG['base_url'] = new_base_url
    if new_model:
        config['model'] = new_model
        MODEL = new_model
        AI_CONFIG['model'] = new_model
    
    with open(CONFIG_PATH, 'w', encoding='utf-8') as f:
        json.dump(config, f, ensure_ascii=False, indent=4)
    
    return config


def test_connection():
    """测试 API 连接是否正常"""
    try:
        start = __import__('time').time()
        result = call_deepseek('Say "ok" in JSON: {"status":"ok"}', 'test', max_tokens=10)
        elapsed = __import__('time').time() - start
        return {'success': True, 'latency': round(elapsed, 2), 'response': result[:100]}
    except Exception as e:
        return {'success': False, 'error': str(e)}
