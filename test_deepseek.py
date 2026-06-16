import requests, json

key = 'sk-9W3zD7CJURFJDy6rNks6ngG7Y2Llxftor63RtZfBQj48Y4Hq'
url = 'https://api-tokenmaster.com/v1/chat/completions'

system_prompt = '你是一个彩票数据分析助手。分析数据后，以JSON格式输出：{"hot_front":[...],"hot_back":[...],"zone_forecast":{"S":...,"M":...,"L":...}}，不要输出其他内容。'

recent = '[3,11,19,26,33], [1,9,15,26,31], [9,11,14,20,25], [8,18,27,32,33], [7,12,22,25,30]'

user_prompt = f'前区数据：{recent}\n分析以上数据，输出JSON格式的分析结果。'

resp = requests.post(url,
    headers={'Authorization': f'Bearer {key}', 'Content-Type': 'application/json'},
    json={
        'model': 'deepseek-chat',
        'messages': [
            {'role': 'system', 'content': system_prompt},
            {'role': 'user', 'content': user_prompt}
        ],
        'max_tokens': 400,
        'temperature': 0.3
    },
    timeout=30)

print(f'Status: {resp.status_code}')
result = resp.json()
print(result['choices'][0]['message']['content'])
print(f'\nModel used: {result["model"]}')
print(f'Tokens used: {result["usage"]["total_tokens"]}')