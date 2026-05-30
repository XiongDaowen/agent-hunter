#!/usr/bin/env python3
"""Fetch GitHub releases for all repos in releases.json."""
import json, sys, time as time_module, re
from pathlib import Path
from datetime import datetime, timezone

import requests

BASE = Path(__file__).parent.parent
RELEASES_FILE = BASE / "data" / "releases.json"
GITHUB_TOKEN = ""

HEADERS = {"Accept": "application/vnd.github+json", "User-Agent": "agent-hunter/1.0"}
if GITHUB_TOKEN:
    HEADERS["Authorization"] = f"Bearer {GITHUB_TOKEN}"


def fetch_release(owner: str, repo: str) -> dict | None:
    url = f"https://api.github.com/repos/{owner}/{repo}/releases/latest"
    try:
        r = requests.get(url, headers=HEADERS, timeout=20)
        if r.status_code == 200:
            return r.json()
        if r.status_code == 404:
            return None
        print(f"   WARN {owner}/{repo}: HTTP {r.status_code}", file=sys.stderr)
    except Exception as e:
        print(f"   WARN {owner}/{repo}: {e}", file=sys.stderr)
    return None


def make_summary(body: str) -> str:
    """Extract non-heading, non-separator lines from release body."""
    lines = []
    for raw in body.split("\n"):
        l = raw.strip()
        # Strip markdown list prefixes
        l = re.sub(r"^[*\-·]\s+", "", l)
        if l and not l.startswith("#") and not l.startswith("---") and len(l) > 10:
            lines.append(f"· {l}")
    return "\n".join(lines[:6])


def main():
    if not RELEASES_FILE.exists():
        print("No releases.json")
        return

    with open(RELEASES_FILE) as f:
        data = json.load(f)

    releases = data.get("releases", {})
    updated = 0

    for key, info in releases.items():
        owner = info.get("owner", "")
        repo = info.get("repo", "")
        if not owner or not repo:
            continue

        print(f"Checking {owner}/{repo}...")
        release = fetch_release(owner, repo)
        if not release:
            print(f"  (no release found)")
            continue

        tag = release.get("tag_name", "")
        published = release.get("published_at", "")
        body = release.get("body", "")
        html_url = release.get("html_url", "")

        if tag and tag != info.get("tag_name", ""):
            print(f"  NEW TAG: {tag}")
            updated += 1
            # Store the previous tag so we can track version history
            info["previous_tag"] = info.get("tag_name", "")
            info["diff_summary"] = f"相较上一版本：{make_summary(body)[:80]}"

        info["tag_name"] = tag
        info["published_at"] = published
        info["html_url"] = html_url
        info["body"] = body
        info["changelog_zh"] = make_summary(body)

        time_module.sleep(0.6)

    if updated > 0:
        data["last_updated"] = datetime.now(timezone.utc).isoformat()
        with open(RELEASES_FILE, "w") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    print(f"Done. {updated} updated.")


if __name__ == "__main__":
    main()