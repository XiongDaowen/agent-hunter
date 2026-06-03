#!/usr/bin/env python3
"""agent-hunter WebUI — Flask backend, single-page HTML frontend."""

import json
import sys
import re
from pathlib import Path

from flask import Flask, jsonify, render_template, request

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from hunter import load_all_agents, discover, update_all, load_meta
from news import generate_news_data, NEWS_DATA_FILE

app = Flask(__name__)


# ── Release matching ───────────────────────────────────────────────────

def _load_releases():
    rf = BASE_DIR / "data" / "releases.json"
    if not rf.exists():
        return {}
    with open(rf) as f:
        return json.load(f).get("releases", {})


def _load_stars_cache():
    """Load GitHub stars from cache file (once per Flask process)."""
    cache_file = BASE_DIR / "cache" / "github_stars.json"
    if not cache_file.exists():
        return {}
    try:
        with open(cache_file) as f:
            return json.load(f)
    except (json.JSONDecodeError, OSError):
        return {}


def _extract_repo_path(gh_url: str) -> str:
    """Extract 'owner/repo' from GitHub URL, case-insensitive."""
    if not gh_url:
        return ""
    m = re.search(r'github\.com/([^/]+/[^/]+)', gh_url, re.IGNORECASE)
    return m.group(1).lower().rstrip("/") if m else ""


# ── API ────────────────────────────────────────────────────────────────

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/api/agents")
def api_agents():
    agents = load_all_agents()
    meta = load_meta()
    releases = _load_releases()
    stars_cache = _load_stars_cache()

    for a in agents:
        name_key = a.get("name", "").lower().replace(" ", "-")
        if name_key in meta:
            a["last_updated"] = meta[name_key].get("last_updated", "")

        # Inject GitHub stars if available in cache
        # Primary: match by github_repo path (handles name mismatches like pydanticai vs pydantic-ai)
        repo_path_stars = _extract_repo_path(a.get("github_repo", ""))
        star_val = None
        if repo_path_stars:
            if repo_path_stars in stars_cache:
                star_val = stars_cache[repo_path_stars].get("stars", -1)
            else:
                # Fallback: match by repo name only (handles org renames like opencode-ai → anomalyco)
                repo_name = repo_path_stars.split("/")[-1] if "/" in repo_path_stars else ""
                # Also check direct key match (e.g. stars key is "pydantic-ai" vs path "pydantic/pydantic-ai")
                if repo_name in stars_cache:
                    star_val = stars_cache[repo_name].get("stars", -1)
                else:
                    match = next((v for k, v in stars_cache.items() if k.endswith("/" + repo_name)), None)
                    if match:
                        star_val = match.get("stars", -1)
        # Fallback: match by name_key directly
        if star_val is None:
            name_key = a.get("name", "").lower().replace(" ", "-")
            if name_key in stars_cache and stars_cache[name_key].get("stars", -1) > 0:
                star_val = stars_cache[name_key]["stars"]
            else:
                # Try stripping common suffixes (e.g. "Hermes Agent" -> "hermes" matches cache key "hermes")
                for suffix in ("-agent", "-cli", "-tui", "-sdk"):
                    if name_key.endswith(suffix):
                        shorter = name_key[:-len(suffix)]
                        if shorter in stars_cache and stars_cache[shorter].get("stars", -1) > 0:
                            star_val = stars_cache[shorter]["stars"]
                            break
        if star_val is not None and star_val > 0:
            a["_stars"] = star_val

        # Match release data by github_repo (exact path, then repo-name-only fallback)
        repo_path = _extract_repo_path(a.get("github_repo", ""))
        if repo_path:
            if repo_path in releases:
                r = releases[repo_path]
            else:
                # Fallback: match by repo name only (handle org renames like opencode-ai → anomalyco)
                repo_name = repo_path.split("/")[-1] if "/" in repo_path else ""
                match = next((v for k, v in releases.items() if k.endswith("/" + repo_name)), None)
                if match:
                    r = match
                else:
                    r = None
            if r:
                a["_release"] = {
                    "tag": r.get("tag_name", ""),
                    "date": r.get("published_at", "")[:10],
                    "url": r.get("html_url", ""),
                    "changelog": r.get("changelog_zh", "").strip(),
                    "diff": r.get("diff_summary", "").strip().replace("相较上一版本：", ""),
                }

    return jsonify(agents)


@app.route("/api/news")
def api_news():
    if NEWS_DATA_FILE.exists():
        with open(NEWS_DATA_FILE) as f:
            return jsonify(json.load(f))
    return jsonify({"total": 0, "updated": "", "topics": {}})


@app.route("/api/news/refresh", methods=["POST"])
def api_news_refresh():
    try:
        total = generate_news_data()
        return jsonify({"ok": True, "total": total})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/agents/refresh", methods=["POST"])
def api_agents_refresh():
    try:
        agents = load_all_agents()
        update_all(agents, force=False)
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


@app.route("/api/agents/discover", methods=["POST"])
def api_agents_discover():
    try:
        new_agents = discover()
        if new_agents:
            update_all(new_agents, force=True)
        return jsonify({"ok": True, "new_count": len(new_agents)})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)}), 500


if __name__ == "__main__":
    import os
    port = int(os.environ.get("PORT", 8501))
    print(f"🚀 agent-hunter WebUI running at http://localhost:{port}")
    app.run(host="0.0.0.0", port=port, debug=False)
