import json

with open('cache/news.json') as f:
    news = json.load(f)

# Check 'Other' topic content
print("=== Other topic (first 5 items) ===")
for item in news['topics']['Other']['items'][:5]:
    print(f"[{item.get('time_ago')}] {item.get('source')} - {item.get('title', '')[:80]}")
    print(f"  url: {item.get('url', '')[:80]}")
    print(f"  desc: {item.get('description', '')[:100]}")
    print()

# Check OpenCode topic
print("=== OpenCode topic (first 3 items) ===")
for item in news['topics']['OpenCode']['items'][:3]:
    print(f"[{item.get('time_ago')}] {item.get('source')} - {item.get('title', '')[:80]}")
    print(f"  url: {item.get('url', '')[:80]}")

print()
# Check unique URLs across topics
all_urls = set()
for topic, data in news['topics'].items():
    for item in data.get('items', []):
        all_urls.add(item.get('url', ''))
print(f"Total unique URLs: {len(all_urls)}")