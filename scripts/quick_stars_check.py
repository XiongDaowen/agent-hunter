#!/usr/bin/env python3
"""Quick GitHub stars fetch - try to populate cache with minimal rate limit impact."""
import json, time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

AGENTS_DIR = Path('/home/xiowen/agent-hunter/agents')
CACHE_FILE = Path('/home/xiowen/agent-hunter/cache/github_stars.json')

def get_stars(repo_url):
    if 'github.com/' not in repo_url:
        return -1
    parts = repo_url.rstrip('/').split('github.com/')
    if len(parts) < 2:
        return -1
    path = parts[1].strip('/').rstrip('.git')
    if '/' not in path:
        return -1
    api_url = f"https://api.github.com/repos/{path}"
    try:
        req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urlopen(req, timeout=8) as resp:
            return json.loads(resp.read()).get('stargazers_count', -1)
    except HTTPError as e:
        if e.code == 403:
            return -2
        return -1
    except:
        return -1

# Load existing cache - support BOTH "t" and "fetched_at" keys
cache = json.load(open(CACHE_FILE)) if CACHE_FILE.exists() else {}
now = time.time()

# Fix cache entries that have "t" instead of "fetched_at"
for agent_id, entry in list(cache.items()):
    if 't' in entry and 'fetched_at' not in entry:
        entry['fetched_at'] = entry['t']
        entry['t'] = entry.get('t')
    if 'fetched_at' in entry:
        entry['age_hours'] = (now - entry['fetched_at']) / 3600

# Get agents with repos
agents_with_repos = []
for f in sorted(AGENTS_DIR.glob('*.json')):
    a = json.load(open(f))
    gh_repo = a.get('github_repo', '')
    if gh_repo:
        agents_with_repos.append((a.get('name', f.stem), gh_repo, f.stem))

print(f"Agents with GitHub repos: {len(agents_with_repos)}")
print(f"Existing cache entries: {len(cache)}")

# Count fresh entries (age < 24h)
fresh = sum(1 for e in cache.values() if e.get('age_hours', 999) < 24)
print(f"Fresh cache entries (<24h): {fresh}")

# Try to fetch ONE agent as a test
if agents_with_repos:
    name, repo, agent_id = agents_with_repos[0]
    stars = get_stars(repo)
    print(f"\nTest fetch for {name}: {stars}")
    if stars >= 0:
        print("GitHub API is accessible - can proceed with fetch")
    elif stars == -2:
        print("Rate limited already")
    else:
        print("Fetch failed - network issue")