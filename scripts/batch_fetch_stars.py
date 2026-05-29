#!/usr/bin/env python3
"""
Batch fetch GitHub stars in small batches to avoid rate limits.
Run from project root: python3 scripts/batch_fetch_stars.py
"""
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

AGENTS_DIR = Path('agents')
CACHE_FILE = Path('cache/github_stars.json')

BATCH_SIZE = 20  # Fetch 20 at a time, then stop (leaves buffer for other cron jobs)
DELAY = 2  # seconds between requests

def get_gh_stars(repo_url: str) -> int:
    if not repo_url or not isinstance(repo_url, str):
        return -1
    if 'github.com/' not in repo_url:
        return -1
    parts = repo_url.rstrip('/').split('github.com/')
    if len(parts) < 2:
        return -1
    path = parts[1].rstrip('/').strip('/').rstrip('.git')
    if not path or '/' not in path:
        return -1
    api_url = f"https://api.github.com/repos/{path}"
    try:
        req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urlopen(req, timeout=10) as resp:
            return json.loads(resp.read()).get('stargazers_count', -1)
    except HTTPError as e:
        if e.code == 403:
            return -2
        return -1
    except:
        return -1

# Load and normalize existing cache
cache = {}
if CACHE_FILE.exists():
    raw = json.load(open(CACHE_FILE))
    for agent_id, entry in raw.items():
        # Normalize: ensure fetched_at exists (handle old "t" key)
        if 'fetched_at' not in entry and 't' in entry:
            entry['fetched_at'] = entry['t']
        cache[agent_id] = entry

now = time.time()
agents_with_repos = []
for f in sorted(AGENTS_DIR.glob('*.json')):
    a = json.load(open(f))
    gh_repo = a.get('github_repo', '')
    if gh_repo:
        agents_with_repos.append((a.get('name', f.stem), gh_repo, f.stem))

print(f"Agents with GitHub repos: {len(agents_with_repos)}")
print(f"Existing cache entries: {len(cache)}")

# Count fresh entries
fresh = sum(1 for e in cache.values() if e.get('stars', -1) >= 0 and (now - e.get('fetched_at', 0)) / 3600 < 24)
print(f"Fresh cache entries (<24h): {fresh}")

# Find agents that need fetching (not in cache or stale)
to_fetch = []
for name, repo_url, agent_id in agents_with_repos:
    if agent_id in cache:
        entry = cache[agent_id]
        stars = entry.get('stars', -1)
        fetched_at = entry.get('fetched_at', 0)
        age_hours = (now - fetched_at) / 3600 if fetched_at else 999
        if age_hours < 24 and stars >= 0:
            continue  # Fresh enough, skip
    to_fetch.append((name, repo_url, agent_id))

print(f"Agents needing fetch: {len(to_fetch)}")

# Fetch a small batch
if not to_fetch:
    print("Cache is complete and fresh. Nothing to do.")
else:
    batch = to_fetch[:BATCH_SIZE]
    print(f"Fetching batch of {len(batch)}...")
    fetched_count = 0
    rate_limited = False
    
    for name, repo_url, agent_id in batch:
        if rate_limited:
            break
        stars = get_gh_stars(repo_url)
        if stars == -2:
            print(f"  [RATE LIMIT] Stopped at {name}")
            rate_limited = True
            break
        cache[agent_id] = {'stars': stars, 'fetched_at': now}
        if stars >= 0:
            print(f"  [OK] {name}: {stars:,}")
        else:
            print(f"  [ERR] {name}")
        fetched_count += 1
        if fetched_count < len(batch):  # Don't sleep after last one
            time.sleep(DELAY)
    
    # Save updated cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    print(f"\nSaved {len(cache)} entries to cache")
    print(f"Fetched {fetched_count} new entries this run")
    if rate_limited:
        print("Rate limited - will retry next cron run")