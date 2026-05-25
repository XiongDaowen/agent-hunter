#!/usr/bin/env python3
"""测试 DuckDuckGo 搜索"""
import requests

url = "https://html.duckduckgo.com/html/"
data = {"q": "AI coding assistant CLI tool 2025"}
headers = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Content-Type": "application/x-www-form-urlencoded",
}

try:
    resp = requests.post(url, data=data, headers=headers, timeout=15)
    print(f'Status: {resp.status_code}')
    print(f'Content length: {len(resp.text)}')
    print(f'Has result: {"result__a" in resp.text}')
    # 打印前500字符
    print(resp.text[:500])
except Exception as e:
    print(f'Error: {e}')