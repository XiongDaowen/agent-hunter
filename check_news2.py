import json

with open('cache/news.json') as f:
    news = json.load(f)

# Check if topics have duplicate content
for topic_name, topic_data in news.get('topics', {}).items():
    print(f"=== {topic_name} ===")
    for item in topic_data.get('items', [])[:3]:
        print(f"  [{item.get('time_ago')}] {item.get('title', '')[:70]}")
        print(f"    source={item.get('source')}, url={item.get('url', '')[:60]}")
    print()