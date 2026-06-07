import json, re

def _strip_suffixes(name):
    suffixes = ("-agent", "-cli", "-tui", "-sdk", "-ai", "-hub", "-studio")
    candidates = []
    for suffix in suffixes:
        if name.endswith(suffix):
            candidates.append(name[:-len(suffix)])
    return candidates

def _extract_repo_path(gh_url):
    if not gh_url:
        return ''
    m = re.search(r'github\.com/([^/]+/[^/]+)', gh_url, re.IGNORECASE)
    return m.group(1).lower().rstrip('/') if m else ''

with open('cache/github_stars.json') as f:
    stars_cache = json.load(f)

print("=== Testing actual app.py fallback chain ===\n")

test_names = ['agno', 'aider', 'cline', 'opencode', 'firecrawl']
for name in test_names:
    try:
        with open(f'agents/{name}.json') as f:
            agent = json.load(f)
    except:
        continue

    gh = agent.get('github_repo', '')
    repo_path_stars = _extract_repo_path(gh)
    star_val = None

    print(f'--- {name} ---')
    print(f'  gh={gh}')
    print(f'  repo_path_stars={repo_path_stars}')

    if repo_path_stars:
        # Step 1: exact match
        if repo_path_stars in stars_cache:
            sv = stars_cache[repo_path_stars].get('stars', -1)
            print(f'  Step1(exact): {repo_path_stars} IN cache, stars={sv}')
            if sv > 0:
                star_val = sv
                print(f'  -> star_val={star_val} (MATCHED)')
        else:
            print(f'  Step1(exact): {repo_path_stars} NOT in cache')

        # Step 2: repo_name with suffix stripping
        if star_val is None:
            repo_name = repo_path_stars.split('/')[-1] if '/' in repo_path_stars else ''
            print(f'  Step2(repo_name): repo_name={repo_name}')
            for key_candidate in [repo_name] + _strip_suffixes(repo_name):
                if key_candidate in stars_cache:
                    sv = stars_cache[key_candidate].get('stars', -1)
                    print(f'    trying key={key_candidate}, stars={sv}')
                    if sv > 0:
                        star_val = sv
                        print(f'    -> MATCHED! star_val={star_val}')
                        break
                else:
                    print(f'    key={key_candidate} NOT in cache')

        # Step 3: partial match
        if star_val is None:
            repo_name = repo_path_stars.split('/')[-1] if '/' in repo_path_stars else ''
            print(f'  Step3(partial): searching for "{repo_name}" in any key')
            match = next((v for k, v in stars_cache.items() if repo_name in k and v.get('stars', -1) > 0), None)
            if match:
                star_val = match.get('stars', -1)
                print(f'  -> MATCHED! star_val={star_val}')
            else:
                print(f'  -> no partial match found')

    print(f'  FINAL star_val={star_val}\n')

print(f"\nCache has {len(stars_cache)} entries")
print(f"Cache keys (first 10): {list(stars_cache.keys())[:10]}")