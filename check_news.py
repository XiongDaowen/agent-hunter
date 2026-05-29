import json
with open('/home/xiowen/agent-hunter/cache/news.json') as f:
    d = json.load(f)
total = 0
empty_desc = []
for topic, info in d['topics'].items():
    total += info['count']
    for item in info['items']:
        if not item.get('description', '').strip():
            empty_desc.append((topic, item['title'][:60]))
print(f'Total items: {total}, reported: {d["total"]}')
print(f'Empty descriptions: {len(empty_desc)}')
for t, title in empty_desc:
    print(f'  [{t}] {title}')