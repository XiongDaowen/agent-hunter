#!/usr/bin/env python3
"""Quick data quality check on agent descriptions."""
import json
from pathlib import Path

suspect = []
for f in sorted(Path('agents').glob('*.json')):
    d = json.load(open(f))
    desc = d.get('description', '')
    name = d.get('name', f.stem)
    # Flag very short descriptions
    if len(desc) < 40:
        suspect.append((f.stem, len(desc), desc))

print(f"Short desc agents (<40 chars): {len(suspect)}")
for name, l, d in suspect:
    print(f"  {name} (len={l}): {d[:80]}")

# Also check for duplicate descriptions (copy-paste indicator)
from collections import Counter
all_descs = []
for f in sorted(Path('agents').glob('*.json')):
    d = json.load(open(f))
    all_descs.append(d.get('description', ''))

dupes = Counter(all_descs)
print(f"\nDuplicate descriptions: {sum(1 for c in dupes.values() if c > 1)}")
for desc, count in dupes.items():
    if count > 1:
        print(f"  [{count}x] {desc[:60]}")