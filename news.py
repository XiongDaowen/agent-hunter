#!/usr/bin/env python3
"""
每日资讯模块 — 整合 HN Algolia + Dev.to 搜索，生成卡片式 HTML 报告。
从 agent-daily-report.py 移植并优化。
"""

import json
import re
import sys
import html
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote
import time as time_module
import time as _time

import requests

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"
NEWS_REPORT_FILE = BASE_DIR / "report" / "news.html"

with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)


# ── Time helper ──────────────────────────────────────────────────────────

def relative_time(dt_str: str) -> str:
    """Convert ISO datetime string to human-friendly 'Nd Nh ago' format."""
    try:
        dt = datetime.fromisoformat(dt_str.replace("Z", "+00:00"))
    except Exception:
        return dt_str
    now = datetime.now(timezone.utc)
    diff = now - dt
    total_seconds = int(diff.total_seconds())
    if total_seconds < 0:
        return "just now"
    days = total_seconds // 86400
    hours = (total_seconds % 86400) // 3600
    minutes = (total_seconds % 3600) // 60
    if days > 0:
        return f"{days}d ago"
    if hours > 0:
        return f"{hours}h ago"
    if minutes > 0:
        return f"{minutes}m ago"
    return "just now"


# ── HN Algolia ──────────────────────────────────────────────────────────

HN_ALGOLIA_URL = "https://hn.algolia.com/api/v1/search"


def fetch_hn(query: str, tags: str = "story", hits_per_page: int = 8, max_retries: int = 2) -> list[dict]:
    """Fetch results from HN Algolia API with retry logic."""
    params = {
        "query": query,
        "tags": tags,
        "hitsPerPage": hits_per_page,
    }
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(HN_ALGOLIA_URL, params=params, timeout=15)
            if r.status_code != 200:
                if attempt < max_retries:
                    import time
                    time.sleep(2 * (attempt + 1))
                    continue
                return []
            data = r.json()
            results = []
            for hit in data.get("hits", []):
                created_at = hit.get("created_at", "")
                time_ago = relative_time(created_at) if created_at else ""
                story_text = hit.get("story_text") or ""
                # Decode HTML entities in story_text (e.g. &amp;#x2F; → /)
                story_text = html.unescape(story_text)
                # Remove boilerplate
                story_text = re.sub(r"Originally published at.*", "", story_text).strip()
                # Truncate at sentence boundary
                if len(story_text) >= 120:
                    m = re.search(r'[。！？.!?]', story_text[100:])
                    if m:
                        story_text = story_text[:100 + m.start() + 1]
                # Fallback to title if story_text is empty
                description = story_text[:200].strip() if story_text else (hit.get("title") or "")[:200].strip()
                results.append({
                    "title": hit.get("title") or hit.get("story_text", "")[:80],
                    "url": hit.get("url") or f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    "points": hit.get("points", 0),
                    "comments": hit.get("num_comments", 0),
                    "author": hit.get("author", ""),
                    "source": "HN",
                    "description": description,
                    "time_ago": time_ago,
                    "_meta": f"{hit.get('points', 0)} points | {hit.get('num_comments', 0)} comments | by {hit.get('author', '')}",
                })
            return results
        except Exception as e:
            if attempt < max_retries:
                import time
                print(f"   ⚠ HN Algolia attempt {attempt + 1} failed: {e}, retrying...", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
                continue
            print(f"   ⚠ HN Algolia failed after {max_retries + 1} attempts: {e}", file=sys.stderr)
            return []
    return []


# ── Dev.to ─────────────────────────────────────────────────────────────

DEVTO_URL = "https://dev.to/api/articles"


def fetch_devto(query: str, per_page: int = 5, max_retries: int = 2) -> list[dict]:
    """Fetch results from Dev.to public API with retry logic."""
    params = {
        "q": query,
        "per_page": per_page,
    }
    for attempt in range(max_retries + 1):
        try:
            r = requests.get(DEVTO_URL, params=params, timeout=15)
            if r.status_code != 200:
                if attempt < max_retries:
                    import time
                    time.sleep(2 * (attempt + 1))
                    continue
                return []
            articles = r.json()
            results = []
            for a in articles:
                created_at = a.get("published_at", "") or a.get("created_at", "")
                time_ago = relative_time(created_at) if created_at else ""
                raw_desc = a.get("description") or ""
                # Strip HTML tags and decode entities
                import re as re_module
                desc_clean = re_module.sub(r"<[^>]+>", "", raw_desc)
                desc_clean = html.unescape(desc_clean)
                # Remove "Originally published at..." boilerplate
                desc_clean = re_module.sub(r"Originally published at.*", "", desc_clean).strip()
                # Truncate at sentence boundary (look for 。！？.!? or full stop)
                if len(desc_clean) >= 120:
                    m = re_module.search(r'[。！？.!?]', desc_clean[100:])
                    if m:
                        desc_clean = desc_clean[:100 + m.start() + 1]
                # Fallback to title if description ends up empty
                description = desc_clean[:200].strip() if desc_clean.strip() else (a.get("title") or "")[:200]
                results.append({
                    "title": a.get("title", ""),
                    "url": a.get("url", ""),
                    "reactions": a.get("public_reactions_count", 0),
                    "comments": a.get("comments_count", 0),
                    "read_time": a.get("reading_time_minutes", 0),
                    "author": a.get("user", {}).get("username", ""),
                    "source": "Dev.to",
                    "description": description,
                    "time_ago": time_ago,
                    "_meta": f"{a.get('public_reactions_count', 0)} ❤️ | {a.get('comments_count', 0)} 💬 | {a.get('reading_time_minutes', 0)} min read | by @{a.get('user', {}).get('username', '')}",
                })
            return results
        except Exception as e:
            if attempt < max_retries:
                import time
                print(f"   ⚠ Dev.to API attempt {attempt + 1} failed: {e}, retrying...", file=sys.stderr)
                time.sleep(2 * (attempt + 1))
                continue
            print(f"   ⚠ Dev.to API failed after {max_retries + 1} attempts: {e}", file=sys.stderr)
            return []
    return []


# ── 36氪 ──────────────────────────────────────────────────────────────────

# ── AI 中文总结（per-item + per-topic）──────────────────────────────────────

# 简评 prompt：把单条资讯压成 15-25 字中文要点
# 设计原则：优先中文术语、说人话、带观点、失败兜底不编造
_PER_ITEM_PROMPT = """你是 AI 行业资讯编辑。把以下技术资讯压缩成 15-25 字中文要点。

要求：
1. 优先中文：英文术语首次出现时括号内附中文（如 agentic loop（智能体循环））
2. 说人话：避免直译堆砌，要说清这条资讯到底在讲啥
3. 带观点：产品发布类 → "X 公司发布 Y，主打 Z"；技术文章类 → "作者提出 Z 方法，解决 W 问题"
4. 失败兜底：如果原文信息不足无法总结，直接返回"（无有效内容）"，不要编造

原文标题：{title}
原文摘要：{description}
来源：{source}

返回：只输出中文要点，不要任何前缀。"""


# 综述 prompt：每个 topic 一段 3-5 句中文综述 + 中文料反思 + UI 干活反思
# 设计原则：让 AI 在生成内容时主动反思"还能去哪抓中文料"和"UI 怎么改更干活"
_PER_TOPIC_PROMPT = """你是 AI 行业主编。下方是"{topic_label}"专题今天的 {n} 条资讯。

任务：
1. 归纳 3-5 句中文综述：今天这个领域主要发生了啥？有啥共同趋势？
2. 反思中文料是否够干活：
   - 当前信息能不能帮中国开发者/产品经理做决策？
   - 缺什么中文角度（本地化案例？国内同类对比？价格/合规？用户使用习惯？）
   - 缺什么中文料 → 用一句具体的话建议下一步去抓什么（如"应去知乎/V2EX/掘金抓'Claude Code 国内使用体验'讨论"）
3. 反思 UI 怎么更干活：
   - 当前卡片/列表布局下，用户能不能 3 秒内抓到今天重点？
   - 建议一个具体的 UI 改进点（如"在每条卡片加'对国内开发者相关度'标签"或"顶部加'今日 3 件必看'大字卡片"）

返回格式（严格，三段都必须填，不要省略）：
【今日综述】
（3-5 句中文，说清今天发生了什么、有什么共同趋势）

【中文料反思】
建议抓取：（一句具体的话，去哪个平台抓什么内容）
建议关键词：（2-4 个中文关键词）

【UI 干活反思】
建议改进：（一句具体的 UI 改进点，如"卡片顶部加'对国内开发者相关度'标签"）

原始资讯列表：
{items_text}"""


def _load_summarize_config() -> dict:
    """Load news_summarize block from config.json (safe defaults if missing)."""
    cfg = CONFIG.get("news_summarize", {})
    return {
        "enabled": cfg.get("enabled", True),
        "per_item_max_tokens": cfg.get("per_item_max_tokens", 256),
        "per_topic_max_tokens": cfg.get("per_topic_max_tokens", 1024),
        "min_description_chars": cfg.get("min_description_chars", 30),
        "summary_temperature": cfg.get("summary_temperature", 0.3),
    }


def _ai_summarize_item(item: dict, cfg: dict) -> str | None:
    """Call LLM to produce a 15-25 字 Chinese summary of one news item.
    Returns None on any failure (caller falls back to original description)."""
    desc = (item.get("description") or "").strip()
    if not desc or len(desc) < cfg["min_description_chars"]:
        return None
    title = item.get("title", "")
    source = item.get("source", "")
    prompt = _PER_ITEM_PROMPT.format(title=title, description=desc, source=source)

    try:
        from hunter import _llm_chat
        text = _llm_chat(
            [{"role": "user", "content": prompt}],
            temperature=cfg["summary_temperature"],
            max_tokens=cfg["per_item_max_tokens"],
        )
    except Exception as e:
        print(f"   WARN ai_summarize_item LLM import/call failed: {e}", file=sys.stderr)
        return None

    if not text:
        return None
    text = text.strip()
    # Strip wrapping quotes if model returned them
    text = text.strip("\"'`「」『』")
    # Strip common prefixes
    for prefix in ["中文要点：", "要点：", "总结：", "总结:", "简评：", "摘要：", "回答：", "输出："]:
        if text.startswith(prefix):
            text = text[len(prefix):].strip()
    if not text or "无有效内容" in text:
        return None
    return text[:120]  # hard cap to prevent model rambling


def _ai_summarize_topic(topic_name: str, topic_label: str, items: list[dict], cfg: dict) -> dict | None:
    """Call LLM to produce per-topic Chinese synthesis + Chinese-source reflection + UI reflection.
    Returns dict with keys: summary, reflection_source, reflection_ui. None on failure."""
    if not items:
        return None
    # Build compact items text: number, title, desc[:200], source
    lines = []
    for i, it in enumerate(items[:20], 1):
        d = (it.get("description") or "")[:200].replace("\n", " ")
        lines.append(f"{i}. [{it.get('source','')}] {it.get('title','')} — {d}")
    items_text = "\n".join(lines)
    prompt = _PER_TOPIC_PROMPT.format(
        topic_label=topic_label, n=len(items), items_text=items_text,
    )

    try:
        from hunter import _llm_chat
        text = _llm_chat(
            [{"role": "user", "content": prompt}],
            temperature=cfg["summary_temperature"],
            max_tokens=cfg["per_topic_max_tokens"],
        )
    except Exception as e:
        print(f"   WARN ai_summarize_topic LLM import/call failed: {e}", file=sys.stderr)
        return None

    if not text:
        return None
    text = text.strip()

    # Parse the 3 sections — robust to minor ordering/missing
    out = {"summary": "", "reflection_source": "", "reflection_ui": ""}
    sections = re.split(r"【今日综述】|【中文料反思】|【UI 干活反思】", text)
    # sections[0] is whatever is before 【今日综述】 (usually empty)
    if len(sections) >= 2:
        out["summary"] = sections[1].split("【")[0].strip()
    if len(sections) >= 3:
        out["reflection_source"] = sections[2].split("【")[0].strip()
    if len(sections) >= 4:
        out["reflection_ui"] = sections[3].split("【")[0].strip()
    # Fallback: if parsing failed but we got some text, use it all as summary
    if not out["summary"] and text:
        out["summary"] = text[:500]
    return out if out["summary"] else None


def _attach_ai_summaries(items: list[dict], cfg: dict) -> None:
    """Mutate items in place: add 'ai_summary' field (15-25 字 Chinese)."""
    for item in items:
        if item.get("ai_summary"):
            continue  # already populated
        s = _ai_summarize_item(item, cfg)
        if s:
            item["ai_summary"] = s


def _attach_topic_summaries(all_results: dict, cfg: dict) -> dict[str, dict]:
    """Produce a {topic_name: {summary, reflection_source, reflection_ui}} dict.
    Failed topics are omitted (caller handles empty case)."""
    topics = get_topics()
    out = {}
    for topic_name, topic_val in topics.items():
        items = all_results.get(topic_name, [])
        if not items:
            continue
        query, icon, label, _ = topic_val if len(topic_val) == 4 else (*topic_val, None)
        result = _ai_summarize_topic(topic_name, label, items, cfg)
        if result:
            out[topic_name] = result
            print(f"   📊 [{topic_name}] 综述生成成功（{len(result['summary'])} 字）")
    return out


def fetch_36kr(query: str, max_retries: int = 2) -> list[dict]:
    """Search 36kr via their public API."""
    try:
        encoded = quote(query)
        url = f"https://36kr.com/api/search-column/article?keyword={encoded}&type=1&page=0&pageSize=8"
        r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"}, timeout=15)
        if r.status_code != 200:
            return []
        data = r.json()
        items = data.get("data", {}).get("items", [])[:6]
        results = []
        for item in items:
            created = item.get("published_at", "") or item.get("created_at", "")
            time_ago = relative_time(created) if created else ""
            raw = item.get("intro") or item.get("summary") or item.get("description", "")[:200]
            desc = re.sub(r"<[^>]+>", "", raw).strip()
            desc = re.sub(r" Originally published at.*", "", desc).strip()
            if len(desc) >= 100:
                m = re.search(r'[。！？.!?]', desc[90:])
                if m:
                    desc = desc[:90 + m.start() + 1]
            results.append({
                "title": item.get("title", "")[:150],
                "url": item.get("news_url") or item.get("url", ""),
                "reactions": item.get("digg_count", 0),
                "comments": item.get("comment_count", 0),
                "author": (item.get("user_info") or {}).get("name", "") if isinstance(item.get("user_info"), dict) else "",
                "source": "36kr",
                "description": desc[:200].strip(),
                "time_ago": time_ago,
                "_meta": f'赞 {item.get("digg_count",0)} · 评论 {item.get("comment_count",0)}',
            })
        return results
    except Exception as e:
        print(f"   WARN 36kr search failed: {e}", file=sys.stderr)
        return []


# ── Combined search ────────────────────────────────────────────────────

def combined_search(query: str, hn_limit: int = 6, devto_limit: int = 4, allowed_sources: list | None = None) -> list[dict]:
    """Search Dev.to + 36kr + HN, merge results. Filter by allowed_sources if provided."""
    hn_results = fetch_hn(query, hits_per_page=hn_limit)
    devto_results = fetch_devto(query, per_page=devto_limit)
    kr36_results = fetch_36kr(query)
    # Quality order: Dev.to (articles) > 36kr (news) > HN (fast)
    combined = devto_results + kr36_results + hn_results
    # Filter by source if topic has source restrictions
    if allowed_sources is not None:
        combined = [r for r in combined if r.get("source") in allowed_sources]
    return combined


# ── HTML 报告生成 ──────────────────────────────────────────────────────

# ── Dynamic topics from agents ────────────────────────────────────────────

# Fixed topic list (was _DEFAULT_TOPICS before _build_topics_from_agents was removed)
# Each entry: (search_query, icon, label, allowed_sources)
# allowed_sources=None means all sources; ["HN"] means HN only (excludes Dev.to/36kr spam)
# Narrow agent topics use HN-only to avoid Dev.to full-text search returning generic articles
# that appear across all topics (e.g. "coding agent" Game Jam posts matching every query).
# However, HN-only topics (OpenClaw/Hermes/Cline/ClaudeCode) are returning 60-90d old content
# because the niche queries have low HN volume. We broaden them to all-sources to get fresh
# Dev.to/36kr coverage while relying on stricter cross-topic dedup to prevent pollution.
_TOPICS = {
    "OpenClaw":   ("openclaw coding agent",   "🔵", "OpenClaw 资讯",   None),
    "Hermes":     ("nousresearch hermes-agent", "🟢", "Hermes 资讯",     None),
    "OpenCode":   ("opencode coding agent",    "🟣", "OpenCode 资讯",   None),
    "ClaudeCode": ("claude code", "🟠", "Claude Code 资讯", None),
    "Cline":      ("cline ai coding agent vs cursor", "🟤", "Cline 资讯",      None),
    "Aider":      ("aider OR aiderai", "🔴", "Aider 资讯",      None),
    "Other":      ("computer use agent OR autonomous coding OR LLM coding assistant", "🟡", "其他 AI Agent 资讯", None),
}


def get_topics():
    """Return topics dict: {key: (search_query, icon, label, allowed_sources)}"""
    return dict(_TOPICS)


def format_source_badge(item: dict) -> str:
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
    description = item.get("description", "")
    time_ago = item.get("time_ago", "")
    badge = format_source_badge(item)
    time_str = f'<span class="time-ago">⏱ {time_ago}</span>' if time_ago else ""
    desc_str = f'<div class="news-desc">{description}</div>' if description else ""
    return f"""
    <div class="news-card">
      <div class="news-title"><a href="{url}" target="_blank">{title}</a></div>
      {desc_str}
      <div class="news-meta">{badge} {time_str}</div>
    </div>
    """


# ── 全局去重 ──────────────────────────────────────────────────────────

def _is_stale(item: dict, max_age_days: int = 30) -> bool:
    """Check if a news item is older than max_age_days.

    Items older than this are considered stale and excluded from news feed
    (but still participate in deduplication to prevent duplicates from reappearing).
    30 days aligns with the visual "stale" threshold in webui.py (line 292)."""
    time_ago = item.get("time_ago", "")
    if not time_ago:
        return False
    try:
        # Parse "Nd ago" format
        days = int(time_ago.split("d")[0])
        return days > max_age_days
    except (ValueError, IndexError):
        return False


def global_deduplicate(all_results: dict, max_age_days: int = 90) -> dict:
    """Remove duplicate URLs and near-duplicate titles WITHIN each topic, then across topics.

    Deduplication strategy (two-pass):
    - Pass 1: Per-topic dedup (exact URL + normalized title within same topic)
    - Pass 2: Cross-topic dedup — earlier-iterated topics get priority for shared URLs.
      This means narrow topics (Aider, OpenClaw, etc.) that appear earlier in _TOPICS
      get to claim URLs before broad topics (Other) that appear later.

    Items older than max_age_days are excluded from results.
    """
    # Pass 1: Per-topic dedup
    deduped_per_topic = {}
    for topic_name, items in all_results.items():
        seen_urls = set()
        seen_normalized_titles = set()
        deduped_section = []
        for item in items:
            if _is_stale(item, max_age_days):
                continue
            url_val = item.get("url", "")
            title_val = item.get("title", "")
            normalized = re.sub(r'[\W_]+', ' ', title_val.lower()).strip()
            url_dup = url_val and url_val in seen_urls
            title_dup = normalized and normalized in seen_normalized_titles
            if url_dup or title_dup:
                continue
            if url_val:
                seen_urls.add(url_val)
            if normalized:
                seen_normalized_titles.add(normalized)
            deduped_section.append(item)
        deduped_per_topic[topic_name] = deduped_section

    # Pass 2: Cross-topic dedup — earlier topics get priority for shared URLs
    seen_urls_global = set()
    final_results = {}
    for topic_name, items in deduped_per_topic.items():
        unique_items = []
        for item in items:
            url_val = item.get("url", "")
            title_val = item.get("title", "")
            normalized = re.sub(r'[\W_]+', ' ', title_val.lower()).strip()
            # Skip if this URL or normalized title was already claimed by an earlier topic
            if url_val and url_val in seen_urls_global:
                continue
            if normalized and normalized in seen_urls_global:
                continue
            seen_urls_global.add(url_val)
            if normalized:
                seen_urls_global.add(normalized)
            unique_items.append(item)
        final_results[topic_name] = unique_items

    return final_results


# ── 主报告生成 ─────────────────────────────────────────────────────────

def generate_news_report():
    """Search all topics and generate HTML news report."""
    print("🔍 搜索 HN Algolia + Dev.to...")

    topics = get_topics()
    topic_empty_default = '<p style=\'color:#666;padding:20px;\'>暂无相关资讯</p>'

    all_results = {}
    for topic_name, topic_val in topics.items():
        query, icon, label, allowed_sources = topic_val if len(topic_val) == 4 else (*topic_val, None)
        print(f"   📡 搜索 [{topic_name}]: {query}")
        results = combined_search(query, hn_limit=10, devto_limit=6, allowed_sources=allowed_sources)
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
    for topic_name, topic_val in topics.items():
        query, icon, label, _allowed_sources = topic_val if len(topic_val) == 4 else (*topic_val, None)
        items = all_results.get(topic_name, [])
        cards_html = "".join(render_news_card(i) for i in items)
        empty_html = topic_empty_default if not items else ""
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
  .news-desc {{ font-size: 0.8rem; color: var(--text-secondary); margin-bottom: 8px; line-height: 1.4; }}
  .time-ago {{ font-size: 0.72rem; color: var(--text-secondary); margin-left: 4px; }}

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

    # Also update the JSON cache so Flask API gets fresh data
    data = {
        "updated": now,
        "total": total,
        "topics": {},
    }
    for topic_name, topic_val in topics.items():
        query, icon, label, _allowed_sources = topic_val if len(topic_val) == 4 else (*topic_val, None)
        items = all_results.get(topic_name, [])
        data["topics"][topic_name] = {
            "icon": icon,
            "label": label,
            "count": len(items),
            "items": items,
        }
    NEWS_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)
    print(f"✅ 资讯数据已同步: {NEWS_DATA_FILE} ({total} 条)")

    return total


# ── 搜索历史缓存 (6h 有效期) ────────────────────────────────────────────

SEARCH_HISTORY_FILE = BASE_DIR / "cache" / "search_history.json"
HISTORY_MAX = 100

def _load_history() -> list:
    if not SEARCH_HISTORY_FILE.exists():
        return []
    try:
        with open(SEARCH_HISTORY_FILE) as f:
            return json.load(f)
    except Exception:
        return []

def _save_history(history: list):
    SEARCH_HISTORY_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(SEARCH_HISTORY_FILE, "w") as f:
        json.dump(history[-HISTORY_MAX:], f, ensure_ascii=False)

def get_cached_search(query: str, max_fresh_days: int = 14) -> list | None:
    """Return cached results for a query if < 6h old AND at least one result is fresh (<= max_fresh_days).
    
    If cached results are all older than max_fresh_days, treat cache as stale and return None.
    This prevents narrow topics (e.g. "openclaw coding agent") from serving 60-90d old content
    when their queries have low HN volume and all hits happen to be stale.
    """
    history = _load_history()
    for entry in reversed(history):
        if entry.get("query") != query:
            continue
        age_seconds = _time.time() - entry.get("cached_at", 0)
        if age_seconds >= 6 * 3600:
            continue  # expired by age
        results = entry.get("results", [])
        if not results:
            return None
        # Check if at least one result is fresh enough
        fresh = False
        for r in results:
            time_ago = r.get("time_ago", "")
            m = re.search(r'(\d+)d', time_ago)
            if m:
                days = int(m.group(1))
                if days <= max_fresh_days:
                    fresh = True
                    break
            elif not time_ago or "h" in time_ago or "m" in time_ago:
                # No days field but has hours/minutes → fresh
                fresh = True
                break
        if not fresh:
            # All cached results are stale — don't use cache
            return None
        return results
    return None

def cache_search(query: str, results: list):
    history = _load_history()
    history = [h for h in history if h.get("query") != query]
    import time
    history.append({"query": query, "cached_at": time.time(), "results": results})
    _save_history(history)


# ── JSON 数据生成 (供 WebUI 消费) ────────────────────────────────────────

NEWS_DATA_FILE = BASE_DIR / "cache" / "news.json"


def generate_news_data():
    """Search all topics and save structured JSON to cache/news.json.
    Uses 6h per-query search cache to avoid hammering external APIs.
    """
    print("🔍 搜索 HN Algolia + Dev.to + 36kr...")

    topics = get_topics()

    all_results = {}
    for topic_name, topic_val in topics.items():
        query, icon, label, allowed_sources = topic_val if len(topic_val) == 4 else (*topic_val, None)
        cached = get_cached_search(query)
        if cached:
            # Apply source filter to cached results if topic has restrictions
            if allowed_sources is not None:
                cached = [r for r in cached if r.get("source") in allowed_sources]
            all_results[topic_name] = cached
            print(f"   CACHE [{topic_name}]: {query} (命中,过滤后 {len(cached)} 条)")
            continue
        print(f"   📡 搜索 [{topic_name}]: {query}")
        results = combined_search(query, hn_limit=10, devto_limit=6, allowed_sources=allowed_sources)
        all_results[topic_name] = results
        cache_search(query, results)
        print(f"      → {len(results)} 条结果")

    # Global deduplication across topics
    all_results = global_deduplicate(all_results)

    total = sum(len(v) for v in all_results.values())
    print(f"   ✅ 全局去重后: {total} 条唯一资讯")

    # ── AI 中文总结：每条简评 + 每 topic 综述（并发加速）─────────────
    sum_cfg = _load_summarize_config()
    topic_summaries: dict[str, dict] = {}
    if sum_cfg.get("enabled"):
        from concurrent.futures import ThreadPoolExecutor, as_completed

        # 收集所有需要 AI 总结的 (item_or_topic_marker, payload)
        tasks = []
        for topic_name, items in all_results.items():
            for idx, item in enumerate(items):
                if not item.get("ai_summary"):
                    tasks.append(("item", topic_name, idx, item))
        # Topic 综述（每个 topic 一次）
        topic_task_meta = []  # (topic_name, label, items)
        for topic_name, topic_val in topics.items():
            items = all_results.get(topic_name, [])
            if items:
                query, icon, label, _ = topic_val if len(topic_val) == 4 else (*topic_val, None)
                topic_task_meta.append((topic_name, label, items))

        total_tasks = len(tasks) + len(topic_task_meta)
        print(f"   🧠 并发生成 AI 总结（{len(tasks)} 条简评 + {len(topic_task_meta)} 个综述 = {total_tasks} 次 LLM）...")

        # ── 执行：item 简评 + topic 综述全并发 ───────────────────
        # LLM 调用是 IO-bound，thread pool 完全够用，无需 multiprocess
        # max_workers=3 防止 scnet API 触发 429 限流（实测 8 并发会被拦）
        MAX_WORKERS = 3
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as pool:
            # 提交 item 任务 → value: ("item", topic_name, idx)
            future_to_meta = {}
            for kind, tname, idx, item in tasks:
                fut = pool.submit(_ai_summarize_item, item, sum_cfg)
                future_to_meta[fut] = ("item", tname, idx)
            # 提交 topic 任务 → value: ("topic", topic_name)
            for tname, label, items in topic_task_meta:
                fut = pool.submit(_ai_summarize_topic, tname, label, items, sum_cfg)
                future_to_meta[fut] = ("topic", tname)

            done = 0
            for fut in as_completed(future_to_meta):
                done += 1
                meta = future_to_meta[fut]
                try:
                    res = fut.result()
                except Exception as e:
                    print(f"   ⚠ {meta} exception: {e}", file=sys.stderr)
                    res = None
                if meta[0] == "item":
                    _, tname, idx = meta
                    if res:
                        all_results[tname][idx]["ai_summary"] = res
                else:  # topic
                    if res:
                        topic_summaries[meta[1]] = res

        ai_count = sum(1 for items in all_results.values() for it in items if it.get("ai_summary"))
        print(f"   ✅ AI 总结完成: {ai_count}/{total} 条简评 + {len(topic_summaries)}/{len(topic_task_meta)} 个综述")
    else:
        print(f"   ⏭ AI 总结已禁用（news_summarize.enabled=false）")

    now = datetime.now().strftime("%Y-%m-%d %H:%M")

    data = {
        "updated": now,
        "total": total,
        "ai_summarized": sum_cfg.get("enabled", False),
        "topic_summaries": topic_summaries,
        "topics": {},
    }
    for topic_name, topic_val in topics.items():
        query, icon, label, _allowed_sources = topic_val if len(topic_val) == 4 else (*topic_val, None)
        items = all_results.get(topic_name, [])
        data["topics"][topic_name] = {
            "icon": icon,
            "label": label,
            "count": len(items),
            "items": items,
        }

    NEWS_DATA_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(NEWS_DATA_FILE, "w") as f:
        json.dump(data, f, ensure_ascii=False)

    print(f"✅ 资讯数据已生成: {NEWS_DATA_FILE} ({total} 条)")
    return total


if __name__ == "__main__":
    generate_news_report()
