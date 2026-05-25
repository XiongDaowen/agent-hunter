#!/usr/bin/env python3
import os
import requests
import json

# Test Ark LLM directly
ark_key = "ark-dd5ccd59-ec1f-461a-bf1c-8c55098cedbe-4da6a"
ark_url = "https://ark.cn-beijing.volces.com/api/coding/v3"
model = "ark-code-latest"

url = f"{ark_url}/chat/completions"
headers = {
    "Authorization": f"Bearer {ark_key}",
    "content-type": "application/json",
}
body = {
    "model": model,
    "max_tokens": 100,
    "temperature": 0.1,
    "messages": [{"role": "user", "content": "Say 'OK' in one word"}],
}

print(f"URL: {url}")
print(f"Headers: {headers}")
print(f"Body: {body}")
print()

try:
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    print(f"Status: {resp.status_code}")
    print(f"Response: {resp.text[:1000]}")
except Exception as e:
    print(f"Error: {e}")