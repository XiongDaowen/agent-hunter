#!/usr/bin/env python3
"""Fetch GitHub stars for all agents with repos. Uses public API (60 req/hr)."""
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

CACHE = Path('cache/github_stars.json')
AGENTS = Path('agents')

def gh_stars(repo_url):
    if not repo_url or 'github.com/' not in repo_url:
        return -1
    parts = repo_url.rstrip('/').split('github.com/')
    if len(parts) < 2:
        return -1
    path = parts[1].strip('/').rstrip('.git')
    if '/' not in path:
        return -1
    try:
        req = Request(f"https://api.github.com/repos/{path}",
                     headers={'User-Agent': 'Mozilla/5.0'})
        with urlopen(req, timeout=10) as r:
            return json.loads(r.read()).get('stargazers_count', -1)
    except HTTPError as e:
        return -2 if e.code == 403 else -1
    except:
        return -1

# Load cache (1hr TTL)
cache = json.load(open(CACHE)) if CACHE.exists() else {}

results = {}
rate_limited = False

for f in sorted(AGENTS.glob('*.json')):
    a = json.load(open(f))
    repo = a.get('github_repo', '')
    if not repo:
        continue
    agent_id = f.stem
    name = a.get('name', agent_id)
    
    if agent_id in cache and cache[agent_id].get('stars', -1) >= 0:
        age_h = (time.time() - cache[agent_id].get('t', 0)) / 3600
        if age_h < 1:
            results[agent_id] = (name, cache[agent_id]['stars'], 'cached')
            continue
    
    if rate_limited:
        results[agent_id] = (name, -1, 'rate_limited')
        continue
    
    stars = gh_stars(repo)
    if stars == -2:
        print(f"[LIMIT] {name} - rate limited, stopping")
        rate_limited = True
        results[agent_id] = (name, -1, 'limit')
        continue
    
    results[agent_id] = (name, stars, 'fetched')
    cache[agent_id] = {'stars': stars, 't': time.time()}
    print(f"[OK] {name}: {stars:,}" if stars >= 0 else f"[ERR] {name}: {stars}")
    time.sleep(2)

# Save
with open(CACHE, 'w') as f:
    json.dump(cache, f)
print(f"\nSaved {CACHE}")
valid = sum(1 for v in results.values() if v[1] >= 0)
print(f"Valid stars: {valid}/{len(results)}")