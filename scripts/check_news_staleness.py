#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone, timedelta

cache_dir = Path('cache')
news_file = cache_dir / 'news.json'
d = json.load(open(news_file))
print('News total:', d.get('total', 0), 'updated:', d.get('updated', 'unknown'))

now = datetime.now(timezone.utc)
updated_str = d.get('updated', '')
try:
    updated_dt = datetime.fromisoformat(updated_str.replace('Z', '+00:00')).replace(tzinfo=timezone.utc)
    age_hours = (now - updated_dt).total_seconds() / 3600
    print('Age hours:', round(age_hours, 1), '-', 'STALE >24h' if age_hours > 24 else 'fresh')
except Exception as e:
    print('Parse error:', e)

# Count stale items
cutoff = now - timedelta(days=60)
stale_count = 0
for topic_name, topic in d.get('topics', {}).items():
    for item in topic.get('items', []):
        date_h = item.get('date_human', '')
        if date_h:
            try:
                item_dt = datetime.fromisoformat(date_h.replace('Z', '+00:00'))
                if item_dt.tzinfo is None:
                    item_dt = item_dt.replace(tzinfo=timezone.utc)
                if item_dt < cutoff:
                    stale_count += 1
            except:
                pass
print('Stale (>60d) news items:', stale_count)