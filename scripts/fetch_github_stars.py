#!/usr/bin/env python3
"""
Fetch GitHub stars for all agents and cache to cache/github_stars.json.
Uses GitHub API with basic rate limiting (60 req/hr unauth).
"""
import json
import time
from pathlib import Path
from urllib.request import urlopen, Request
from urllib.error import HTTPError

CACHE_FILE = Path('cache/github_stars.json')
AGENTS_DIR = Path('agents')

def get_gh_stars(repo_url: str) -> int:
    """Extract repo path from URL and fetch star count."""
    if not repo_url or not isinstance(repo_url, str):
        return -1
    # Extract "owner/repo" from various GitHub URL formats
    if 'github.com/' not in repo_url:
        return -1
    
    parts = repo_url.rstrip('/').split('github.com/')
    if len(parts) < 2:
        return -1
    path = parts[1].rstrip('/')
    # Remove .git suffix
    if path.endswith('.git'):
        path = path[:-4]
    # Remove leading/trailing slashes
    path = path.strip('/')
    if not path or '/' not in path:
        return -1
    
    api_url = f"https://api.github.com/repos/{path}"
    
    try:
        req = Request(api_url, headers={'User-Agent': 'Mozilla/5.0', 'Accept': 'application/json'})
        with urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read())
            return data.get('stargazers_count', -1)
    except HTTPError as e:
        if e.code == 403:
            return -2  # Rate limited
        return -1
    except Exception as e:
        return -1

def load_existing_cache() -> dict:
    if CACHE_FILE.exists():
        return json.load(open(CACHE_FILE))
    return {}

def main():
    cache = load_existing_cache()
    
    agents_with_repos = []
    for f in sorted(AGENTS_DIR.glob('*.json')):
        a = json.load(open(f))
        gh_repo = a.get('github_repo', '')
        if gh_repo:
            agents_with_repos.append((a.get('name', f.stem), gh_repo, f.stem))
    
    print(f"Agents with GitHub repos: {len(agents_with_repos)}")
    
    results = {}
    fetched = 0
    cached = 0
    rate_limited = False
    
    for name, repo_url, agent_id in agents_with_repos:
        # Check cache (1 hour TTL)
        if agent_id in cache:
            entry = cache[agent_id]
            cached_stars = entry.get('stars', -1)
            cached_time = entry.get('fetched_at', 0)
            age_hours = (time.time() - cached_time) / 3600 if cached_time else 999
            if age_hours < 1 and cached_stars >= 0:
                results[agent_id] = cached_stars
                cached += 1
                print(f"  [CACHED] {name}: {cached_stars:,}")
                continue
        
        if rate_limited:
            results[agent_id] = -1
            continue
        
        stars = get_gh_stars(repo_url)
        
        if stars == -2:
            print(f"  [RATE LIMIT] Stopping at {name}")
            rate_limited = True
            results[agent_id] = -1
            continue
        
        results[agent_id] = stars
        cache[agent_id] = {'stars': stars, 'fetched_at': time.time()}
        fetched += 1
        print(f"  [FETCHED] {name}: {stars:,}" if stars >= 0 else f"  [ERROR] {name}: {stars}")
        
        # Rate limit: 60/hr unauth, be conservative
        time.sleep(2)
    
    # Save cache
    CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(CACHE_FILE, 'w') as f:
        json.dump(cache, f, indent=2)
    
    print(f"\nSummary: {fetched} fetched, {cached} cached, {len(results)} total")
    print(f"Cache saved to {CACHE_FILE}")
    
    # Count valid results
    valid = sum(1 for v in results.values() if v >= 0)
    print(f"Agents with valid stars: {valid}/{len(results)}")

if __name__ == '__main__':
    main()