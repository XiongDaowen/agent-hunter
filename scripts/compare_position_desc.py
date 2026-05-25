#!/usr/bin/env python3
import json
from pathlib import Path

agents = []
for f in Path('agents').glob('*.json'):
    with open(f) as fp:
        agents.append(json.load(fp))

# Compare position vs description for each agent
print("Agents where position ≈ description (likely redundant):")
print("=" * 80)
for a in sorted(agents, key=lambda x: x['name']):
    pos = a.get('position', '')
    desc = a.get('description', '')
    if pos and desc:
        # Simple similarity check
        import difflib
        ratio = difflib.SequenceMatcher(None, pos, desc).ratio()
        if ratio > 0.5:
            print(f"\n[{a['name']}]")
            print(f"  POSITION: {pos[:80]}")
            print(f"  DESC:     {desc[:80]}")
            print(f"  Similarity: {ratio:.2f}")

print("\n\nAgents where position ≠ description (distinct content):")
print("=" * 80)
for a in sorted(agents, key=lambda x: x['name']):
    pos = a.get('position', '')
    desc = a.get('description', '')
    if pos and desc:
        import difflib
        ratio = difflib.SequenceMatcher(None, pos, desc).ratio()
        if ratio <= 0.5:
            print(f"\n[{a['name']}]")
            print(f"  POSITION: {pos[:80]}")
            print(f"  DESC:     {desc[:80]}")