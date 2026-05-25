#!/usr/bin/env python3
"""Analyze cached GitHub stars."""
import json

d = json.load(open('cache/github_stars.json'))
print('Agents cached:', len(d))
valid = [(k, v['stars']) for k, v in d.items() if v.get('stars', -1) >= 0]
print('With valid stars:', len(valid))
valid.sort(key=lambda x: -x[1])
print('Top 10 by stars:')
for k, s in valid[:10]:
    print(f'  {s:>10,} {k}')