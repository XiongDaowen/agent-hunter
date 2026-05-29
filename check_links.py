#!/usr/bin/env python3
import json, os, glob, httpx
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

agents_dir = Path('/home/xiowen/agent-hunter/agents')
json_files = glob.glob(str(agents_dir / '*.json'))

dead = []
live = []
errors = []

def check_url(name, url):
    try:
        r = httpx.get(url, timeout=10, follow_redirects=True)
        if r.status_code >= 400:
            return (name, url, f"HTTP {r.status_code}")
        return (name, url, "OK")
    except httpx.HTTPError as e:
        return (name, url, f"ERR: {type(e).__name__}")

name_to_file = {}
for f in json_files:
    with open(f) as fp:
        data = json.load(fp)
    name = data.get('name', '')
    website = data.get('website', '')
    if name and website:
        name_to_file[name] = (f, website)

print(f"Checking {len(name_to_file)} agents with website fields...")
with ThreadPoolExecutor(max_workers=8) as ex:
    futures = {ex.submit(check_url, name, info[1]): name for name, info in name_to_file.items()}
    for fut in as_completed(futures):
        result = fut.result()
        if result[2] != "OK":
            dead.append(result)
        else:
            live.append(result)

print(f"\nResults: {len(live)} live, {len(dead)} dead ({len(errors)} errors)")
if dead:
    print("\nDead links:")
    for name, url, status in sorted(dead):
        print(f"  [{status}] {name}: {url}")