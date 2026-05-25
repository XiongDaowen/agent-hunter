#!/usr/bin/env python3
import json

d = json.load(open('data/releases.json'))
releases = d.get('releases', {})
print(f"Type of releases: {type(releases)}")
if isinstance(releases, dict):
    print(f"Agents with releases: {len(releases)}")
    for agent_id, rels in list(releases.items())[:5]:
        print(f"  {agent_id}: {len(rels)} releases")
        for r in rels[:2]:
            print(f"    - {r.get('version', r.get('tag', '?'))} ({r.get('date', '?')}) - {str(r.get('name', ''))[:50]}")
print(f"Last updated: {d.get('last_updated', 'unknown')}")