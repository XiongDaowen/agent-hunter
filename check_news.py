import json

with open('cache/news.json') as f:
    news = json.load(f)

print(f"News updated: {news.get('updated')}")
print(f"Total topics: {len(news.get('topics', {}))}")
for topic_name, topic_data in news.get('topics', {}).items():
    items = topic_data.get('items', [])
    first = items[0] if items else {}
    print(f"  {topic_name}: {topic_data.get('count')} items, latest: {first.get('time_ago', '?')} - {first.get('title', '')[:40]}")