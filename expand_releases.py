#!/usr/bin/env python3
"""Expand releases.json to cover ALL agent repos with GitHub URLs.
- Adds missing repos from agents/*.json
- Fixes wrong owner/repo pairs (case mismatches, renamed orgs)
- Preserves existing valid entries with tag_name
"""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).parent
if str(BASE).startswith("/tmp"):
    BASE = Path("/home/xiowen/agent-hunter")
AGENTS_DIR = BASE / "agents"
RELEASES_FILE = BASE / "data" / "releases.json"

def extract_repo(gh_url):
    if not gh_url:
        return None, None
    m = re.search(r'github\.com/([^/]+)/([^/]+)', gh_url, re.IGNORECASE)
    if m:
        return m.group(1), m.group(2)
    return None, None

# Collect all agent repos
agent_repos = {}  # key -> {owner, repo, name}
for f in AGENTS_DIR.glob("*.json"):
    try:
        with open(f) as fp:
            agent = json.load(fp)
        gh_url = agent.get("github_repo", "")
        if not gh_url:
            continue
        owner, repo = extract_repo(gh_url)
        if not owner or not repo:
            continue
        key = f"{owner}/{repo}".lower()
        agent_repos[key] = {"owner": owner, "repo": repo, "name": agent.get("name", f.stem)}
    except Exception as e:
        print(f"WARN: {f}: {e}", file=sys.stderr)

# Load existing releases
with open(RELEASES_FILE) as f:
    data = json.load(f)
releases = data.get("releases", {})

# Fix strategy:
# 1. Keep entries with valid tag_name (they worked correctly)
# 2. For empty tag_name entries, check if the key matches agent's actual repo
#    - If key doesn't match any agent github_repo -> mark for removal or update
# 3. Add all missing agent repos

fixed = 0
added = 0
removed_stale = 0

# Entries with empty tag_name that need investigation
stale_keys = [k for k, v in releases.items() if not v.get("tag_name")]
print(f"=== Stale entries (empty tag_name) ===")
for k in stale_keys:
    v = releases[k]
    print(f"  {k}: owner={v.get('owner')}, repo={v.get('repo')}")

# For each existing release entry
new_releases = {}
for key, info in releases.items():
    tag = info.get("tag_name", "")
    owner = info.get("owner", "")
    repo = info.get("repo", "")

    if tag:
        # Valid entry — keep as-is
        new_releases[key] = info
        continue

    # Empty tag_name — check if we can fix the key
    # Try to find matching agent repo
    correct_key = None
    for agent_key, agent_info in agent_repos.items():
        if agent_info["owner"].lower() == owner.lower() and agent_info["repo"].lower() == repo.lower():
            correct_key = agent_key
            break

    if correct_key and correct_key != key:
        # Key is wrong (case/rename issue) — fix it
        info["owner"] = agent_repos[correct_key]["owner"]
        info["repo"] = agent_repos[correct_key]["repo"]
        new_releases[correct_key] = info
        fixed += 1
        print(f"  FIXED key: {key} -> {correct_key}")
    elif correct_key is None:
        # No matching agent — remove stale entry
        print(f"  REMOVED stale: {key} (no matching agent)")
        removed_stale += 1
    else:
        # Key matches but still no tag — keep for retry
        new_releases[key] = info

# Add missing repos
for key, info in agent_repos.items():
    if key not in new_releases:
        new_releases[key] = {
            "owner": info["owner"],
            "repo": info["repo"],
            "tag_name": "",
            "published_at": "",
            "html_url": f"https://github.com/{info['owner']}/{info['repo']}/releases",
            "body": "",
            "changelog_zh": "⏳ 等待首次获取...",
            "diff_summary": "⏳ 等待首次获取"
        }
        added += 1
        print(f"  ADDED: {key} ({info['name']})")

data["releases"] = new_releases
data["last_updated"] = ""

with open(RELEASES_FILE, "w") as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f"\nDone: {fixed} fixed, {added} added, {removed_stale} removed")
print(f"Total releases entries: {len(new_releases)}")
