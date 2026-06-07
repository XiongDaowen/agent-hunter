#!/usr/bin/env python3
"""Fetch stars for products missing from cache (10 repos with stars=-1)."""
import json
import urllib.request
import time

# 10 repos that have stars=-1 in cache, need re-fetch with correct owner/repo paths
REPOS = {
    'crawl4ai/crawl4ai': 'crawl4ai/crawl4ai',
    'nicklausw/firecrawl': 'nicklausw/firecrawl',
    'flexpilot-ai/flexpilot': 'flexpilot-ai/flexpilot',
    'phillipclapham/flowscript': 'phillipclapham/flowscript',
    'moogar0880/go-tui': 'moogar0880/go-tui',
    'braincore/hai-cli': 'braincore/hai-cli',
    'modelcontextprotocol/servers': 'modelcontextprotocol/servers',
    'pydantic/pydantic-ai': 'pydantic/pydantic-ai',
    'sourcegraph/cody': 'sourcegraph/cody',
    'agoraio/ya-copilot': 'agoraio/ya-copilot',
}

CACHE_FILE = 'cache/github_stars.json'

def fetch_stars(repo: str) -> int:
    url = f'https://api.github.com/repos/{repo}'
    req = urllib.request.Request(url, headers={
        'Accept': 'application/vnd.github.v3+json',
        'User-Agent': 'agent-hunter-cron'
    })
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            data = json.loads(r.read())
            return data.get('stargazers_count', -1) or -1
    except Exception as e:
        print(f'  ERROR {repo}: {e}')
        return -1

def main():
    try:
        with open(CACHE_FILE) as f:
            stars = json.load(f)
    except:
        stars = {}

    for cache_key, repo in REPOS.items():
        print(f'Fetching {repo}...', end=' ', flush=True)
        s = fetch_stars(repo)
        if s >= 0:
            # Update the existing -1 entry with correct stars
            stars[cache_key] = {'stars': s, 'fetched_at': time.time()}
            # Also clean up old bad keys if they exist
            old_bad = [k for k in stars if stars[k].get('stars', 0) == -1 and k != cache_key]
            print(f'⭐ {s:,}')
        else:
            print(f'STILL FAILED (HTTP error or rate limit)')
        time.sleep(1.2)

    with open(CACHE_FILE, 'w') as f:
        json.dump(stars, f, indent=2)
    print(f'Done. Cache has {len(stars)} entries')

if __name__ == '__main__':
    main()
