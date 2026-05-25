#!/usr/bin/env python3
import json, os, glob

agents = sorted(glob.glob('agents/*.json'))
missing_website = missing_github = missing_docs = missing_tags = 0
missing_pricing = 0

for f in agents:
    name = os.path.basename(f)
    try:
        with open(f) as fp:
            d = json.load(fp)
            if not d.get('website'): missing_website += 1
            if not d.get('github_repo'): missing_github += 1
            if not d.get('docs_url'): missing_docs += 1
            if not d.get('tags'): missing_tags += 1
            if not d.get('pricing'): missing_pricing += 1
    except Exception as e:
        print(f"Error reading {name}: {e}")

print(f"Total agents: {len(agents)}")
print(f"Missing website: {missing_website}")
print(f"Missing github_repo: {missing_github}")
print(f"Missing docs_url: {missing_docs}")
print(f"Missing tags: {missing_tags}")
print(f"Missing pricing: {missing_pricing}")

# Show which ones have missing fields
print("\n--- Agents missing website ---")
for f in agents:
    try:
        with open(f) as fp:
            d = json.load(fp)
            if not d.get('website'):
                print(f"  {d.get('name', '?')} ({os.path.basename(f)})")
    except: pass

print("\n--- Agents missing github_repo ---")
for f in agents:
    try:
        with open(f) as fp:
            d = json.load(fp)
            if not d.get('github_repo'):
                print(f"  {d.get('name', '?')} ({os.path.basename(f)})")
    except: pass