#!/usr/bin/env python3
"""测试 360 搜索是否正常工作"""
import requests
from urllib.parse import quote

url = 'https://www.so.com/s?q=' + quote('AI编程助手 推荐')
headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Referer': 'https://www.360.cn/',
}

try:
    resp = requests.get(url, headers=headers, timeout=15)
    print(f'Status: {resp.status_code}')
    print(f'Content length: {len(resp.text)}')
    print(f'Has <h3>: {"<h3" in resp.text}')
    # 检查是否有搜索结果
    if '没有找到' in resp.text:
        print('WARNING: 没有找到搜索结果')
    if '反爬' in resp.text or '验证' in resp.text:
        print('WARNING: 可能被反爬')
    print('---First 1000 chars---')
    print(resp.text[:1000])
except Exception as e:
    print(f'Error: {e}')