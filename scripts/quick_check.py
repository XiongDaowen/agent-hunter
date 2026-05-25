#!/usr/bin/env python3
import json
from pathlib import Path
from datetime import datetime, timezone

agents_dir = Path('agents')

# Check 1: website field format
print("=== Website field check ===")
broken_website = []
missing_website = []
for f in agents_dir.glob('*.json'):
    d = json.load(open(f))
    name = d.get('name', f.stem)
    website = d.get('website', '')
    if website == '' or website == None:
        missing_website.append(f'{f.name}: {name}')
    elif not website.startswith('http'):
        broken_website.append(f'{f.name}: website="{website}"')
print(f'Missing website: {len(missing_website)}')
for b in missing_website[:5]:
    print(f'  {b}')
print(f'Broken website (no http): {len(broken_website)}')
for b in broken_website[:5]:
    print(f'  {b}')

# Check 2: last_verified age
print("\n=== Last verified age check ===")
today = datetime.now(timezone.utc).date()
old_verified = []
for f in agents_dir.glob('*.json'):
    d = json.load(open(f))
    lv = d.get('last_verified', '')
    if lv:
        try:
            dt = datetime.fromisoformat(lv.replace('Z','+00:00')).date()
            age = (today - dt).days
            if age > 30:
                old_verified.append((f.name, age, lv))
        except:
            pass
old_verified.sort(key=lambda x: -x[1])
print(f'Agents not verified in >30 days: {len(old_verified)}')
for name, age, lv in old_verified[:10]:
    print(f'  {name}: {age}d old (last: {lv})')