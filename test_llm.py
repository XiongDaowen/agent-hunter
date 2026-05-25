import requests
import json

cfg = {
    "base_url": "https://ark.cn-beijing.volces.com/api/coding/v3",
    "api_key": "ark-dd5ccd59-ec1f-461a-bf1c-8c55098cedbe-4da6a",
    "model": "ark-code-latest"
}

url = f"{cfg['base_url']}/chat/completions"
headers = {
    "Authorization": f"Bearer {cfg['api_key']}",
    "content-type": "application/json"
}
body = {
    "model": cfg["model"],
    "max_tokens": 100,
    "messages": [{"role": "user", "content": "say hello in 3 words"}]
}

resp = requests.post(url, headers=headers, json=body, timeout=30)
print("Status:", resp.status_code)
print("Response:", resp.text[:500])