#!/usr/bin/env python3
"""测试搜狗搜索结果解析"""
import requests
import re
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
    # 尝试解析搜索结果 - 搜狗结果通常是 <h3 class="vrwrap"><a href="...">标题</a></h3>
    # 或者 <h3 class="pt"><a href="...">标题</a></h3>
    results = []
    
    # 方法1: vrwrap 样式
    pattern1 = r'<h3 class="vrwrap"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    # 方法2: pt 样式
    pattern2 = r'<h3 class="pt"[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    # 方法3: 通用 h3
    pattern3 = r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
    
    for p in [pattern1, pattern2, pattern3]:
        matches = re.findall(p, resp.text, re.S)
        if matches:
            print(f"Pattern {p[:30]}... found {len(matches)} matches")
            for m in matches[:3]:
                href, title = m
                # 清理 HTML 标签
                title = re.sub(r'<[^>]+>', '', title)
                print(f"  - {title[:60]} -> {href[:50]}")
                results.append({'title': title[:120], 'url': href})
            if results:
                break
    
    print(f"\nTotal results found: {len(results)}")
except Exception as e:
    print(f'Error: {e}')