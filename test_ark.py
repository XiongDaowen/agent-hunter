#!/usr/bin/env python3
import requests

# Test Ark
ark_key = "ark-dd5ccd59-ec1f-461a-bf1c-8c55098cedbe-4da6a"
ark_url = "https://ark.cn-beijing.volces.com/api/coding/v3"

headers = {
    'Authorization': f'Bearer {ark_key}',
    'Content-Type': 'application/json'
}
data = {
    'model': 'ark-code-latest',
    'messages': [{'role': 'user', 'content': 'Hi'}],
    'max_tokens': 10
}

try:
    r = requests.post(f'{ark_url}/chat/completions', headers=headers, json=data, timeout=30)
    print(f'Ark Status: {r.status_code}')
    print(r.text[:500])
except Exception as e:
    print(f'Ark Error: {e}')