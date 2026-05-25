#!/usr/bin/env python3
"""Quick data quality check for agent-hunter iteration."""
import json
from pathlib import Path
from datetime import datetime, timezone

cache_dir = Path('cache')
news_file = cache_dir / 'news.json'
if news_file.exists():
    d = json.load(open(news_file))
    print(f"News cache: {d.get('total', 0)} items, updated {d.get('updated', 'unknown')}")
    now = datetime.now(timezone.utc)
    updated_str = d.get('updated', '')
    if updated_str:
        try:
            updated_dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00'))
            age_hours = (now - updated_dt.replace(tzinfo=timezone.utc)).total_seconds() / 3600
            print(f"  Age: {age_hours:.1f} hours")
            if age_hours > 24:
                print(f"  ⚠️ STALE - older than 24h!")
            else:
                print(f"  ✅ Fresh")
        except Exception as e:
            print(f"  Parse error: {e}")

    # Count items by time bucket
    items = []
    for topic_name, topic in d.get('topics', {}).items():
        for item in topic.get('items', []):
            item['_topic'] = topic_name
            items.append(item)
    print(f"  Total news items across {len(d.get('topics', {}))} topics")

    # Check for very old items
    from dateutil import parser as dateutil_parser
    from datetime import timedelta
    cutoff = now - timedelta(days=60)
    old_items = []
    for item in items:
        time_str = item.get('time_ago', '')
        # time_ago format: "55d ago", "3h ago", "2 weeks ago"
        # Parse from time_ago or from date_human
        date_h = item.get('date_human', '')
        if date_h:
            try:
                item_dt = dateutil_parser.parse(date_h)
                if item_dt.tzinfo is None:
                    item_dt = item_dt.replace(tzinfo=timezone.utc)
                if item_dt < cutoff:
                    old_items.append((item['title'][:50], item['_topic'], item_dt.strftime('%Y-%m-%d')))
            except:
                pass
    if old_items:
        print(f"\n⚠️ Items older than 60 days: {len(old_items)}")
        for title, topic, date in old_items[:5]:
            print(f"  [{topic}] {title} ({date})")
    else:
        print("\n✅ No items older than 60 days")

agents_dir = Path('agents')
# Check missing website
missing_w = [(f.name, json.load(open(f)).get('name','?')) for f in agents_dir.glob('*.json') if not json.load(open(f)).get('website','')]
print(f"\nAgents with missing website: {len(missing_w)}")
for fn, name in missing_w[:3]:
    print(f"  {fn}: {name}")