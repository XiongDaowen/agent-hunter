#!/usr/bin/env python3
"""Quick test of the search fallback logic"""
import sys
sys.path.insert(0, '.')
from hunter import _search_hn_algolia, _search_360
import json

print("=== Testing HN Algolia ===")
results = _search_hn_algolia("AI coding agent terminal 2025", limit=3)
print(f"HN returned {len(results)} results")
for r in results:
    print(f"  - {r['title'][:60]}")

print()
print("=== Testing 360 Search ===")
results = _search_360("AI编程助手 IDE 编辑器 推荐 2025", limit=3)
print(f"360 returned {len(results)} results")
for r in results:
    print(f"  - {r['title'][:60]}")

print()
print("=== All OK ===")
