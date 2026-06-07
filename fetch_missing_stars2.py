#!/usr/bin/env python3
"""Fetch stars for products missing from cache."""
import json
import urllib.request
import time

REPOS = {
    'crawl4ai': 'crawl4ai/crawl4ai',
    'hermes-agent': 'NousResearch/hermes-agent',
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

    for pid, repo in REPOS.items():
        print(f'Fetching {repo}...', end=' ', flush=True)
        s = fetch_stars(repo)
        if s >= 0:
            stars[repo] = {'stars': s, 'fetched_at': time.time()}
            stars[pid] = {'stars': s, 'fetched_at': time.time()}
            print(f'⭐ {s:,}')
        else:
            print(f'FAILED')
        time.sleep(1.2)

    with open(CACHE_FILE, 'w') as f:
        json.dump(stars, f, indent=2)
    print(f'Done. Cache has {len(stars)} entries')

if __name__ == '__main__':
    main()