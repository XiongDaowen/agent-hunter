import json, os, glob
from datetime import datetime

files = glob.glob('/home/xiowen/agent-hunter/agents/*.json')
stats = {'total': len(files), 'categories': {}, 'updates': {}}
for f in files:
    try:
        with open(f) as fp:
            d = json.load(fp)
            cat = d.get('category', 'Unknown')
            stats['categories'][cat] = stats['categories'].get(cat, 0) + 1
            mtime = os.path.getmtime(f)
            days_ago = (datetime.now() - datetime.fromtimestamp(mtime)).days
            if days_ago <= 7:
                bucket = '0-7d'
            elif days_ago <= 30:
                bucket = '8-30d'
            else:
                bucket = '30d+'
            stats['updates'][bucket] = stats['updates'].get(bucket, 0) + 1
    except Exception as e:
        pass

print(json.dumps(stats, indent=2))