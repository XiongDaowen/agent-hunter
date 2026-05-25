import os, json
agents_dir = 'agents'
missing_website = []
missing_github = []
short_desc = []

for f in os.listdir(agents_dir):
    if not f.endswith('.json'): continue
    with open(os.path.join(agents_dir, f)) as fp:
        a = json.load(fp)
    name = a.get('name', f)
    if not a.get('website') or a.get('website') == 'N/A' or a.get('website') == '':
        missing_website.append(name)
    if not a.get('github_repo'):
        missing_github.append(name)
    desc = a.get('description', '')
    if len(desc) < 30:
        short_desc.append(f'{name}: {desc[:50]}')

print(f'Missing website: {len(missing_website)}')
for n in missing_website: print(f'  {n}')
print(f'Missing github_repo: {len(missing_github)}')
for n in missing_github: print(f'  {n}')
print(f'Short description (<30): {len(short_desc)}')
for d in short_desc: print(f'  {d}')