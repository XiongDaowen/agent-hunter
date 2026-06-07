import json, urllib.request

url = 'http://localhost:8501/api/agents'
with urllib.request.urlopen(url) as resp:
    agents = json.load(resp)

print(f'Total agents: {len(agents)}')
stars_ok = [a for a in agents if a.get('_stars', 0) > 0]
stars_null = [a for a in agents if a.get('_stars') is None and a.get('github_repo')]
stars_missing = [a for a in agents if not a.get('github_repo')]
print(f'Have stars > 0: {len(stars_ok)}')
print(f'GitHub but stars=null: {len(stars_null)}')
print(f'No GitHub repo: {len(stars_missing)}')
print()
print('Sample WITH stars:')
for a in stars_ok[:8]:
    print(f'  {a["name"]}: stars={a.get("_stars")}, gh={a.get("github_repo","none")[:50]}')
print()
print('Sample GitHub but NO stars:')
for a in stars_null[:8]:
    print(f'  {a["name"]}: gh={a.get("github_repo","?")[:60]}')