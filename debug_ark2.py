#!/usr/bin/env python3
"""Debug version of _llm_chat with more logging"""
import os
import sys
import json
import requests
import time

cfg_path = os.path.join('/home/xiowen/agent-hunter', 'config.json')
with open(cfg_path) as f:
    cfg = json.load(f)

llm_cfg = cfg.get("llm", {})
base_url = llm_cfg.get("base_url", "")
api_key = llm_cfg.get("api_key", "")
model = llm_cfg.get("model", "MiniMax-M2.7")

print(f"base_url: {base_url}")
print(f"api_key: {api_key[:20]}...")
print(f"model: {model}")

messages = [{"role": "user", "content": "Say 'OK' in one word"}]
temperature = 0.1
max_tokens = 100

# The actual code path from hunter.py
flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "llm_unavailable.flag")
if os.path.exists(flag_file):
    print(f"Flag exists at: {flag_file}")
    os.remove(flag_file)
    print("Flag removed")

base = base_url.rstrip("/")
url = f"{base}/chat/completions"
print(f"URL: {url}")

headers = {
    "Authorization": f"Bearer {api_key}",
    "content-type": "application/json",
}
body = {
    "model": model,
    "max_tokens": max_tokens,
    "temperature": temperature,
    "messages": messages,
}

print("Making request...")
try:
    resp = requests.post(url, headers=headers, json=body, timeout=120)
    print(f"Status: {resp.status_code}")
    
    if resp.status_code == 401:
        print("401 Unauthorized!")
        
    resp.raise_for_status()
    data = resp.json()
    print(f"Response: {json.dumps(data)[:500]}")
    
    choices = data.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        print(f"Content: {content}")
    else:
        print("No choices in response")
        
except Exception as e:
    print(f"Error: {type(e).__name__}: {e}")