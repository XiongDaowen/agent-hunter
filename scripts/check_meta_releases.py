#!/usr/bin/env python3
"""Quick check of meta.json and releases.json."""
import json
from pathlib import Path

# meta.json
meta = Path('cache/meta.json')
if meta.exists():
    d = json.load(open(meta))
    print("=== cache/meta.json ===")
    print("Keys:", list(d.keys())[:10])
    print("Sample (first 2):", dict(list(d.items())[:2]))
else:
    print("No cache/meta.json")

# releases.json
rel = Path('data/releases.json')
if rel.exists():
    d = json.load(open(rel))
    print("\n=== data/releases.json ===")
    print("Keys:", list(d.keys())[:10])
    releases = d.get('releases', d.get('items', []))
    if isinstance(releases, list):
        print("Count:", len(releases))
        if releases:
            print("Sample:", json.dumps(releases[0], indent=2)[:300])
    else:
        print("Not a list:", type(releases))
else:
    print("No data/releases.json")