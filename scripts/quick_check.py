#!/usr/bin/env python3
import json
from pathlib import Path

agents = []
for f in Path('agents').glob('*.json'):
    with open(f) as fp:
        agents.append(json.load(fp))

print(f"Total agents: {len(agents)}")

# Check position field
pos_count = sum(1 for a in agents if a.get('position'))
pos_examples = [(a['name'], a.get('position','')) for a in agents if a.get('position')][:10]
print(f"Agents with position: {pos_count}/78")
print("Examples:")
for n, p in pos_examples:
    print(f"  {n}: '{p}'")

# Check news data
news_file = Path('cache/news.json')
if news_file.exists():
    with open(news_file) as f:
        nd = json.load(f)
    print(f"\nNews update: {nd.get('updated', '?')}")
    print(f"Total news items: {nd.get('total', 0)}")
    topics = nd.get('topics', {})
    print("Topics:")
    for t, d in topics.items():
        print(f"  {t}: {d.get('count', 0)} items")
else:
    print("\nNo news.json found")

# Check meta.json freshness
import os
meta_stat = os.stat('cache/meta.json')
from datetime import datetime
mtime = datetime.fromtimestamp(meta_stat.st_mtime)
print(f"\nmeta.json last modified: {mtime}")