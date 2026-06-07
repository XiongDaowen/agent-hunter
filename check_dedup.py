import json

with open('cache/news.json') as f:
    news = json.load(f)

all_urls_by_topic = {}
for topic, data in news['topics'].items():
    urls = set()
    for item in data.get('items', []):
        urls.add(item.get('url', ''))
    all_urls_by_topic[topic] = urls

from collections import Counter
all_urls = []
for topic, urls in all_urls_by_topic.items():
    all_urls.extend(urls)
url_counts = Counter(all_urls)

duplicates = {url: count for url, count in url_counts.items() if count > 1}
print(f"Total unique URLs: {len(set(all_urls))}")
print(f"URLs appearing in 2+ topics: {len(duplicates)}")
if duplicates:
    for url, count in list(duplicates.items())[:5]:
        owners = [t for t, urls in all_urls_by_topic.items() if url in urls]
        print(f"  [{count}x] {url[:70]}")
        print(f"    Topics: {owners}")

other_urls = all_urls_by_topic.get('Other', set())
# All URLs from other topics
non_other = set()
for t, urls in all_urls_by_topic.items():
    if t != 'Other':
        non_other |= urls
other_unique = other_urls - non_other
other_overlap = other_urls & non_other
print(f"\n'Other' topic: {len(other_urls)} URLs total")
print(f"'Other' unique (not in other topics): {len(other_unique)}")
print(f"'Other' overlapping: {len(other_overlap)}")