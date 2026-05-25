import json, os
agents_dir = '/home/xiowen/agent-hunter/agents'
files = [f for f in os.listdir(agents_dir) if f.endswith('.json')]
data = []
for f in files:
    with open(os.path.join(agents_dir, f)) as fp:
        data.append(json.load(fp))
print(f'Total agents: {len(data)}')
missing_desc = [a['name'] for a in data if not a.get('description') or a['description'] == '']
missing_website = [a['name'] for a in data if not a.get('website') or a['website'] == '']
missing_github = [a['name'] for a in data if not a.get('github_repo') or a['github_repo'] == '']
print(f'Missing description: {len(missing_desc)}')
print(f'Missing website: {len(missing_website)}')
print(f'Missing github_repo: {len(missing_github)}')
print('Missing desc:', missing_desc)
print('Missing website:', missing_website)
print('Missing github:', missing_github[:10])