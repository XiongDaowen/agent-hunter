#!/usr/bin/env python3
"""Check GitHub stars data completeness."""
import json
from pathlib import Path

agents_dir = Path('agents')
missing_stars = []
has_stars = []
zero_stars = []

for f in sorted(agents_dir.glob('*.json')):
    d = json.load(open(f))
    name = d.get('name', f.stem)
    gh_repo = d.get('github_repo', '')
    stars = d.get('github_stars')
    
    if not gh_repo:
        continue
    
    if stars is None:
        missing_stars.append((name, gh_repo))
    elif stars == 0:
        zero_stars.append((name, gh_repo))
    else:
        has_stars.append((name, stars, gh_repo))

print(f"Total agents with GitHub repo: {len(missing_stars)+len(zero_stars)+len(has_stars)}")
print(f"Has stars data: {len(has_stars)}")
print(f"Missing stars data: {len(missing_stars)}")
print(f"Zero stars: {len(zero_stars)}")

print("\n=== Missing stars ===")
for name, repo in missing_stars[:10]:
    print(f"  {name}: {repo}")

print("\n=== Zero stars (check if real) ===")
for name, repo in zero_stars[:5]:
    print(f"  {name}: {repo}")

# Top 10 by stars
has_stars.sort(key=lambda x: -x[1])
print("\n=== Top 10 by stars ===")
for name, stars, repo in has_stars[:10]:
    print(f"  {name}: {stars:,} ⭐")