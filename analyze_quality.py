#!/usr/bin/env python3
import json
import glob
import os

agents_dir = "agents"
issues = []

for f in sorted(glob.glob(os.path.join(agents_dir, "*.json"))):
    with open(f) as fp:
        d = json.load(fp)
    name = d.get('id', 'unknown')
    
    # Check github_repo
    github = d.get('github_repo', '')
    if not github:
        issues.append((name, 'missing github_repo'))
    elif github in ('null', 'None'):
        issues.append((name, f'bad github_repo: {github}'))
    
    # Check docs_url
    docs = d.get('docs_url', '')
    if not docs or docs in ('null', 'None'):
        issues.append((name, f'bad docs_url: {docs}'))
    
    # Check features array
    features = d.get('features', [])
    if not features or len(features) < 2:
        issues.append((name, f'few features: {len(features)}'))
    
    # Check strengths array  
    strengths = d.get('strengths', [])
    if not strengths or len(strengths) < 1:
        issues.append((name, f'few strengths: {len(strengths)}'))

if issues:
    print("=== Data Quality Issues ===")
    for name, issue in issues:
        print(f"{name}: {issue}")
else:
    print("No significant data issues found")

print(f"\nTotal agents: {len(glob.glob(os.path.join(agents_dir, '*.json')))}")