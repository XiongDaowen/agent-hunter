#!/usr/bin/env python3
"""测试搜狗搜索"""
import requests
from urllib.parse import quote

url = 'https://www.sogou.com/web?query=' + quote('AI编程助手 推荐')
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.sogou.com/',
}

try:
    resp = requests.get(url, headers=headers, timeout=15)
    print(f'Status: {resp.status_code}')
    print(f'Content length: {len(resp.text)}')
    print(f'Has results: {"result" in resp.text.lower()}')
    # 打印前1000字符
    print(resp.text[:1000])
except Exception as e:
    print(f'Error: {e}')