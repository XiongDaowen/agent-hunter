#!/home/xiowen/.hermes/hermes-agent/venv/bin/python3
"""
每日资讯模块 — 整合 HN Algolia + Dev.to 搜索，生成卡片式 HTML 报告。
从 agent-daily-report.py 移植并优化。
"""

import json
import re
import sys
from datetime import datetime
from pathlib import Path
from urllib.parse import quote

import requests

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
NEWS_REPORT_FILE = BASE_DIR / "report" / "news.html"

with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)


# ── HN Algolia ──────────────────────────────────────────────────────────

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def fetch_hn(query: str, tags: str = "story", hits_per_page: int = 8) -> list[dict]:
    """Fetch results from HN Algolia API."""
    params = {
        "query": query,
        "tags": tags,
        "hitsPerPage": hits_per_page,
    }
    try:
        r = requests.get(HN_ALGOLIA_URL, params=params, timeout=10)
        if r.status_code != 200:
            return []
        data = r.json()
        results = []
        for hit in data.get("hits", []):
            results.append({
                "title": hit.get("title") or hit.get("story_text", "")[:80],
                "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                "points": hit.get("points", 0),
                "comments": hit.get("num_comments", 0),
                "author": hit.get("author", ""),
                "source": "HN",
                "_meta": f"{hit.get('points', 0)} points | {hit.get('num_comments', 0)} comments | by {hit.get('author', '')}",
            })
        return results
    except Exception as e:
        print(f"   ⚠ HN Algolia failed: {e}", file=sys.stderr)
        return []


# ── Dev.to ─────────────────────────────────────────────────────────────

DEVTO_URL = "https://dev.to/api/articles"


def fetch_devto(query: str, per_page: int = 5) -> list[dict]:
    """Fetch results from Dev.to public API."""
    params = {
        "tag": query.replace(" ", "").lower(),
        "per_page": per_page,
    }
    try:
        r = requests.get(DEVTO_URL, params=params, timeout=10)
        if r.status_code != 200:
            return []
        articles = r.json()
        results = []
        for a in articles:
            results.append({
                "title": a.get("title", ""),
                "url": a.get("url", ""),
                "reactions": a.get("public_reactions_count", 0),
                "comments": a.get("comments_count", 0),
                "read_time": a.get("reading_time_minutes", 0),
                "author": a.get("user", {}).get("username", ""),
                "source": "Dev.to",
                "_meta": f"{a.get('public_reactions_count', 0)} ❤️ | {a.get('comments_count', 0)} 💬 | {a.get('reading_time_minutes', 0)} min read | by @{a.get('user', {}).get('username', '')}",
            })
        return results
    except Exception as e:
        print(f"   ⚠ Dev.to API failed: {e}", file=sys.stderr)
        return []


# ── Combined search ────────────────────────────────────────────────────

def combined_search(query: str, hn_limit: int = 6, devto_limit: int = 4) -> list[dict]:
    """Search both HN and Dev.to, merge results."""
    hn_results = fetch_hn(query, hits_per_page=hn_limit)
    devto_results = fetch_devto(query, per_page=devto_limit)
    # Dev.to first (often higher-quality articles), then HN
    combined = devto_results + hn_results
    return combined


# ── HTML 报告生成 ──────────────────────────────────────────────────────

TOPICS = {
    "OpenClaw": ("OpenClaw AI agent", "🔶", "OpenClaw 相关资讯"),
    "Hermes": ("Hermes Agent AI", "🟣", "Hermes Agent 相关资讯"),
    "OpenCode": ("OpenCode AI coding", "🔵", "OpenCode 相关资讯"),
    "Other": ("AI coding agent LLM", "🟢", "其他 AI Agent 重要资讯"),
}

TOPIC_EMPTY_DEFAULT = """<p style='color:#666;padding:20px;'>暂无相关资讯</p>"""


def format_source_badge(item: dict) -> str:
    """Return source badge HTML."""
    src = item.get("source", "")
    meta = item.get("_meta", "")
    if src == "HN":
        badge = '<span class="source-badge hn">🔗 HN</span>'
        if meta:
            badge += f' <span class="hn-meta">{meta}</span>'
        return badge
    elif src == "Dev.to":
        badge = '<span class="source-badge devto">💻 Dev.to</span>'
        if meta:
            badge += f' <span class="devto-meta">{meta}</span>'
        return badge
    return ""


def render_news_card(item: dict) -> str:
    """Render a single news card HTML."""
    title = item.get("title", "无标题")
    url = item.get("url", "#")
    badge = format_source_badge(item)
    return f"""
    <div class="news-card">
      <div class="news-title"><a href="{url}" target="_blank">{title}</a></div>
      <div class="news-meta">{badge}</div>
    </div>
    """


# ── 全局去重 ──────────────────────────────────────────────────────────

def global_deduplicate(all_results: dict) -> dict:
    """Remove duplicate URLs across all search topics."""
    seen_urls = set()
    deduped = {}
    for topic_name, items in all_results.items():
        deduped_section = []
        for item in items:
            url_val = item.get("url", "")
            if url_val and url_val not in seen_urls:
                seen_urls.add(url_val)
                deduped_section.append(item)
        deduped[topic_name] = deduped_section
    return deduped


# ── 主报告生成 ─────────────────────────────────────────────────────────

def generate_news_report():
    """Search all topics and generate HTML news report."""
    print("🔍 搜索 HN Algolia + Dev.to...")

    all_results = {}
    for topic_name, (query, icon, label) in TOPICS.items():
        print(f"   📡 搜索 [{topic_name}]: {query}")
        results = combined_search(query, hn_limit=6, devto_limit=4)
        all_results[topic_name] = results
        print(f"      → {len(results)} 条结果")

    # Global deduplication across topics
    all_results = global_deduplicate(all_results)

    total = sum(len(v) for v in all_results.values())
    print(f"   ✅ 全局去重后: {total} 条唯一资讯")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Build HTML
    sections_html = ""
    for topic_name, (query, icon, label) in TOPICS.items():
        items = all_results.get(topic_name, [])
        cards_html = "".join(render_news_card(i) for i in items)
        empty_html = TOPIC_EMPTY_DEFAULT if not items else ""
        sections_html += f"""
        <div class="topic-section">
          <h2 class="topic-title">{icon} {label}</h2>
          <div class="news-grid">{cards_html}{empty_html}</div>
        </div>
        """

    html = f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta property="og:title" content="AI Agent 每日资讯 - {date_str}">
<meta name="twitter:title" content="AI Agent 每日资讯 - {date_str}">
<title>AI Agent 每日资讯 - {date_str}</title>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d2e;
    --border: #2a2f45;
    --text: #e2e4f0;
    --text-secondary: #8b8fa8;
    --accent: #6c8cff;
    --hn-color: #ff6600;
    --devto-color: #3b49df;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif; background: var(--bg); color: var(--text); line-height: 1.6; }}
  .container {{ max-width: 1200px; margin: 0 auto; padding: 24px; }}

  .header {{ text-align: center; padding: 48px 24px 32px; border-bottom: 1px solid var(--border); margin-bottom: 32px; }}
  .header h1 {{ font-size: 2.2rem; font-weight: 700; background: linear-gradient(135deg, var(--accent), #a78bfa); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 8px; }}
  .header p {{ color: var(--text-secondary); font-size: 1rem; }}
  .header .meta {{ margin-top: 12px; font-size: 0.85rem; color: var(--text-secondary); }}

  .topic-section {{ margin-bottom: 48px; }}
  .topic-title {{ font-size: 1.3rem; font-weight: 600; margin: 0 0 16px; padding-bottom: 8px; border-bottom: 2px solid var(--border); color: var(--accent); }}

  .news-grid {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 12px; }}
  .news-card {{ background: var(--card); border: 1px solid var(--border); border-radius: 10px; padding: 16px; transition: all 0.15s; }}
  .news-card:hover {{ border-color: var(--accent); transform: translateY(-2px); }}
  .news-title {{ font-size: 0.95rem; font-weight: 500; margin-bottom: 8px; line-height: 1.5; }}
  .news-title a {{ color: var(--text); text-decoration: none; }}
  .news-title a:hover {{ color: var(--accent); }}
  .news-meta {{ font-size: 0.75rem; color: var(--text-secondary); }}

  .source-badge {{ display: inline-block; font-size: 0.7rem; font-weight: 600; padding: 2px 8px; border-radius: 6px; margin-right: 6px; }}
  .source-badge.hn {{ background: rgba(255,102,0,0.15); color: var(--hn-color); }}
  .source-badge.devto {{ background: rgba(59,73,223,0.15); color: var(--devto-color); }}
  .hn-meta, .devto-meta {{ font-size: 0.72rem; color: var(--text-secondary); }}

  .footer {{ text-align: center; padding: 32px; color: var(--text-secondary); font-size: 0.82rem; border-top: 1px solid var(--border); margin-top: 40px; }}
</style>
</head>
<body>
<div class="container">
  <div class="header">
    <h1>🤖 AI Agent 每日资讯</h1>
    <p>HN Algolia + Dev.to 聚合 · AI Agent 相关最新动态</p>
    <div class="meta">📅 {date_str} | 🔍 {total} 条资讯 | 数据来源: HN Algolia & Dev.to</div>
  </div>
  {sections_html}
</div>
<div class="footer">
  <p>由 agent-hunter 自动生成 | 数据来源: HN Algolia & Dev.to | 报告更新时间: {now}</p>
  <p>项目地址: <a href="https://github.com/xiowen/agent-hunter" style="color:var(--accent)">github.com/xiowen/agent-hunter</a></p>
</div>
</body>
</html>"""

    NEWS_REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_REPORT_FILE, "w") as f:
        f.write(html)

    print(f"✅ 资讯报告已生成: {NEWS_REPORT_FILE} ({total} 条)")
    return total


if __name__ == "__main__":
    generate_news_report()
