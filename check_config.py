import json
with open('/home/xiowen/agent-hunter/config.json') as f:
    d = json.load(f)
firecrawl = d.get('search_sources', {}).get('domestic', {}).get('firecrawl', {})
print('firecrawl status:', firecrawl.get('enabled'))
firecrawl_overseas = d.get('search_sources', {}).get('overseas', {}).get('firecrawl', {})
print('firecrawl overseas:', firecrawl_overseas.get('enabled'))
print('360:', d.get('search_sources', {}).get('domestic', {}).get('360_search', {}).get('enabled'))
print('DDG:', d.get('search_sources', {}).get('overseas', {}).get('duckduckgo', {}).get('enabled'))