import json
from pathlib import Path

agents_dir = Path('agents')
poor_desc = []
poor_features = []
poor_strengths = []

for f in agents_dir.glob('*.json'):
    with open(f) as fp:
        a = json.load(fp)
    name = a.get('name', f.name)
    desc = a.get('description', '')
    features = a.get('Features', []) or a.get('features', [])
    strengths = a.get('strengths', [])

    if len(desc) < 50:
        poor_desc.append((name, desc[:80] if desc else '(empty)'))
    if not features or len(features) < 2:
        poor_features.append((name, len(features) if features else 0))
    if not strengths or len(strengths) < 2:
        poor_strengths.append((name, len(strengths) if strengths else 0))

print(f'=== Products with <50 char descriptions ({len(poor_desc)}) ===')
for n, d in poor_desc:
    print(f'  {n}: {d}')

print(f'\n=== Products with <2 features ({len(poor_features)}) ===')
for n, c in poor_features:
    print(f'  {n}: {c} features')

print(f'\n=== Products with <2 strengths ({len(poor_strengths)}) ===')
for n, c in poor_strengths:
    print(f'  {n}: {c} strengths')