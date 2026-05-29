import json, os, glob
from datetime import datetime

agents_dir = '/home/xiowen/agent-hunter/agents'
json_files = glob.glob(f'{agents_dir}/*.json')
print(f'Total JSON files: {len(json_files)}')

categories = {}
recent_week = 0
recent_month = 0
total_size = 0

for f in json_files:
    try:
        with open(f) as fp:
            data = json.load(fp)
        cat = data.get('category', 'Unknown')
        categories[cat] = categories.get(cat, 0) + 1
        mtime = os.path.getmtime(f)
        now = datetime.now().timestamp()
        if now - mtime < 86400:
            recent_week += 1
        if now - mtime < 2592000:
            recent_month += 1
        total_size += os.path.getsize(f)
    except:
        pass

print(f'Categories: {json.dumps(categories, indent=2)}')
print(f'Updated in last week: {recent_week}')
print(f'Updated in last month: {recent_month}')
print(f'Total size: {total_size/1024:.1f} KB')