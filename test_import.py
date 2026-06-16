import sys
sys.path.insert(0, r'D:\AI\lottery-app')
try:
    import api_server
    print('api_server imports OK')
except Exception as e:
    print(f'Error: {e}')