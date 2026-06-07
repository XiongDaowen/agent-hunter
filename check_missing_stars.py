import json

with open('cache/github_stars.json') as f:
    cache = json.load(f)

# Check which of the 10 missing repos exist in cache (even with -1)
missing_repos = ['crawl4ai', 'firecrawl', 'flexpilot', 'flowscript', 'go-tui', 'hai-cli', 'pydantic-ai', 'sourcegraph', 'ya-copilot', 'modelcontextprotocol']

for r in missing_repos:
    if r in cache:
        print(f'{r}: {cache[r]}')
    else:
        # Try partial
        matches = [(k, v) for k, v in cache.items() if r in k]
        if matches:
            print(f'{r}: partial matches: {matches}')
        else:
            print(f'{r}: NOT IN CACHE')