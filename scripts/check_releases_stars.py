#!/usr/bin/env python3
"""Check releases.json and GitHub stars data."""
import json
from pathlib import Path

# releases.json
d = json.load(open('data/releases.json'))
releases = d.get('releases', [])
print(f"Total releases: {len(releases)}")
print(f"Last updated: {d.get('last_updated', 'unknown')}")

# Group by agent
from collections import defaultdict
by_agent = defaultdict(list)
for r in releases:
    by_agent[r.get('agent_id', r.get('agent', '?'))].append(r)
print(f"Agents with releases: {len(by_agent)}")

# Show sample
for agent_id, rels in sorted(by_agent.items())[:5]:
    print(f"\n  {agent_id}: {len(rels)} releases")
    for r in rels[:2]:
        print(f"    - {r.get('version', r.get('tag', '?'))} ({r.get('date', r.get('published_at', '?'))}) - {r.get('name', r.get('title', ''))[:50]}")

# GitHub stars: check if hunter.py or another file fetches it
print("\n=== GitHub stars check ===")
agent_with_repo = 0
agent_with_stars = 0
for f in sorted(Path('agents').glob('*.json')):
    a = json.load(open(f))
    if a.get('github_repo'):
        agent_with_repo += 1
        if a.get('github_stars') not in (None, '', 0):
            agent_with_stars += 1
print(f"Agents with GitHub repo: {agent_with_repo}")
print(f"Agents with stars data: {agent_with_stars}")