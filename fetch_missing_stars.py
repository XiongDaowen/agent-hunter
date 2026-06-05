#!/usr/bin/env python3
"""Fetch GitHub stars for the 8 missing products."""
import json
import urllib.request
import time

MISSING_REPOS = {
    'vercel-ai-sdk': 'vercel/ai',
    'tabby': 'TabbyML/tabby',
    'vectimus': 'vectimus/vectimus',
    'ya-copilot': 'AgoraIO/ya-copilot',
    'zed-ai': 'zed-industries/zed',
    'swe-agent': 'princeton-nlp/swe-agent',
    'twinny': 'rjmacarthy/twinny',
    'toad': 'batrachianai/toad',
}

CACHE_FILE = 'cache/github_stars.json'

def fetch_stars(repo: str) -> int:
    """Fetch star count from GitHub API."""
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
    # Load existing cache
    cache_file = CACHE_FILE
    try:
        with open(cache_file) as f:
            stars = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        stars = {}

    print(f'Loaded {len(stars)} existing entries')
    print(f'Fetching stars for {len(MISSING_REPOS)} missing repos...')

    for pid, repo in MISSING_REPOS.items():
        print(f'  Fetching {repo}...', end=' ', flush=True)
        s = fetch_stars(repo)
        if s >= 0:
            stars[repo] = {'stars': s, 'fetched_at': time.time()}
            stars[pid] = {'stars': s, 'fetched_at': time.time()}
            print(f'⭐ {s:,}')
        else:
            print(f'FAILED (stars={s})')
        time.sleep(1.2)  # Rate limit protection

    # Save
    with open(cache_file, 'w') as f:
        json.dump(stars, f, indent=2)

    print(f'\nDone. Cache now has {len(stars)} entries')
    
    # Verify
    for pid in MISSING_REPOS:
        found = pid in stars or any(pid.replace('-','').replace('_','') in k.replace('-','').replace('_','') for k in stars)
        print(f'  {pid}: {"✅ FOUND" if found else "❌ STILL MISSING"}')

if __name__ == '__main__':
    main()
