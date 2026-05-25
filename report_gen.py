#!/usr/bin/env python3
"""
报告生成模块 — 从 agents/ 目录读取数据，生成卡片式 HTML 报告。
"""

import json
import os
from datetime import datetime
from pathlib import Path

from logger import success, warning

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"

with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

AGENTS_DIR = BASE_DIR / CONFIG["agents_dir"]
REPORT_FILE = BASE_DIR / CONFIG["report_file"]
META_FILE = BASE_DIR / CONFIG["meta_file"]
CACHE_DIR = BASE_DIR / CONFIG["cache_dir"]
RELEASES_FILE = BASE_DIR / "data" / "releases.json"

# ── 模板 ────────────────────────────────────────────────────────────────

HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<meta name="description" content="收录 78+ 个 AI Agent 产品，涵盖 IDE、CLI、TUI、GUI、Plugin、SDK 等分类，实时追踪 AI 编程助手发展动态">
<title>AI Agent 产品全景报告</title>
<style>
  :root {{
    --bg: #0f1117;
    --card: #1a1d2e;
    --card-hover: #22263b;
    --border: #2a2f45;
    --text: #e2e4f0;
    --text-secondary: #8b8fa8;
    --accent: #6c8cff;
    --accent-green: #4ade80;
    --accent-yellow: #facc15;
    --accent-red: #f87171;
    --accent-purple: #a78bfa;
  }}
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, 'Noto Sans SC', sans-serif;
    background: var(--bg);
    color: var(--text);
    line-height: 1.6;
    padding: 0;
  }}
  .container {{ max-width: 1400px; margin: 0 auto; padding: 24px; }}

  /* 头部 */
  .header {{
    text-align: center;
    padding: 48px 24px 32px;
    border-bottom: 1px solid var(--border);
    margin-bottom: 32px;
  }}
  .header h1 {{
    font-size: 2.2rem;
    font-weight: 700;
    background: linear-gradient(135deg, var(--accent), var(--accent-purple));
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
    margin-bottom: 8px;
  }}
  .header p {{
    color: var(--text-secondary);
    font-size: 1rem;
  }}
  .header .meta {{
    margin-top: 12px;
    font-size: 0.85rem;
    color: var(--text-secondary);
  }}
  .header .meta span {{ margin: 0 12px; }}

  /* 统计栏 */
  .stats {{
    display: flex;
    gap: 16px;
    justify-content: center;
    flex-wrap: wrap;
    margin-bottom: 32px;
  }}
  .stat-card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 16px 28px;
    text-align: center;
    min-width: 120px;
  }}
  .stat-card .num {{
    font-size: 1.8rem;
    font-weight: 700;
    color: var(--accent);
  }}
  .stat-card .label {{
    font-size: 0.8rem;
    color: var(--text-secondary);
    margin-top: 4px;
  }}

  /* 分类标签 */
  .category-nav {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
    justify-content: center;
    margin-bottom: 32px;
    padding: 0;
  }}
  .category-nav a {{
    text-decoration: none;
    padding: 6px 16px;
    border-radius: 20px;
    font-size: 0.85rem;
    background: var(--card);
    border: 1px solid var(--border);
    color: var(--text-secondary);
    transition: all 0.15s;
  }}
  .category-nav a:hover {{
    background: var(--card-hover);
    color: var(--text);
    border-color: var(--accent);
  }}

/* 分类标题 */
  .section-title {{
    font-size: 1.3rem;
    font-weight: 600;
    margin: 40px 0 16px;
    padding-bottom: 8px;
    border-bottom: 2px solid var(--border);
  }}
  /* Per-category title colors */
  .section-title-IDE    {{ color: #818cf8; }}
  .section-title-CLI    {{ color: #22c55e; }}
  .section-title-TUI    {{ color: #a855f7; }}
  .section-title-GUI    {{ color: #ec48bb; }}
  .section-title-Plugin {{ color: #fb923c; }}
  .section-title-SDK    {{ color: #0ea5e9; }}
  .section-title-Runtime{{ color: #eab308; }}
  .section-title-Other  {{ color: #9ca3af; }}

  /* 卡片网格 */
  .grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
    gap: 16px;
    margin-bottom: 24px;
  }}
  .card {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 20px;
    transition: all 0.15s;
    display: flex;
    flex-direction: column;
  }}
  .card:hover {{
    background: var(--card-hover);
    border-color: var(--accent);
    transform: translateY(-2px);
  }}

/* 卡片标题 */
  .card-title {{
    font-size: 1.15rem;
    font-weight: 600;
  }}
  .card-title a {{
    color: var(--text);
    text-decoration: none;
  }}
  .card-title a:hover {{ color: var(--accent); }}
  /* Per-category card title colors */
  .card-title-IDE a    {{ color: #818cf8 !important; }}
  .card-title-CLI a    {{ color: #22c55e !important; }}
  .card-title-TUI a    {{ color: #a855f7 !important; }}
  .card-title-GUI a    {{ color: #ec48bb !important; }}
  .card-title-Plugin a {{ color: #fb923c !important; }}
  .card-title-SDK a    {{ color: #0ea5e9 !important; }}
  .card-title-Runtime a{{ color: #eab308 !important; }}
  .card-title-Other a  {{ color: #9ca3af !important; }}
  .card-title-IDE a:hover    {{ color: #a5b4fc !important; }}
  .card-title-CLI a:hover    {{ color: #4ade80 !important; }}
  .card-title-TUI a:hover    {{ color: #c084fc !important; }}
  .card-title-GUI a:hover    {{ color: #f472b6 !important; }}
  .card-title-Plugin a:hover{{ color: #fdba74 !important; }}
  .card-title-SDK a:hover    {{ color: #38bdf8 !important; }}
  .card-title-Runtime a:hover{{ color: #fde047 !important; }}
  .card-title-Other a:hover  {{ color: #d1d5db !important; }}

  /* 开源标签 */
  .badge {{
    display: inline-block;
    font-size: 0.7rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 6px;
    white-space: nowrap;
  }}
  .badge-yes {{ background: rgba(74,222,128,0.15); color: var(--accent-green); }}
  .badge-partial {{ background: rgba(250,204,21,0.15); color: var(--accent-yellow); }}
  .badge-no {{ background: rgba(248,113,113,0.15); color: var(--accent-red); }}

  /* 分类标签 */
  .cat-tag {{
    display: inline-block;
    font-size: 0.65rem;
    font-weight: 600;
    padding: 2px 8px;
    border-radius: 4px;
    white-space: nowrap;
    margin-left: 8px;
    vertical-align: middle;
  }}
  .cat-IDE {{ background: rgba(99,102,241,0.15); color: #818cf8; }}
  .cat-CLI {{ background: rgba(34,197,94,0.15); color: #22c55e; }}
  .cat-TUI {{ background: rgba(168,85,247,0.15); color: #a855f7; }}
  .cat-GUI {{ background: rgba(236,72,153,0.15); color: #ec48bb; }}
  .cat-Plugin {{ background: rgba(249,115,22,0.15); color: #fb923c; }}
  .cat-SDK {{ background: rgba(14,165,233,0.15); color: #0ea5e9; }}
  .cat-Runtime {{ background: rgba(234,179,8,0.15); color: #eab308; }}
  .cat-Other {{ background: rgba(107,114,128,0.15); color: #9ca3af; }}

  /* TOP 5 热门排名 */
  .top5-section {{
    margin-bottom: 18px;
    padding: 10px 14px 12px;
    background: rgba(108,140,255,0.05);
    border: 1px solid rgba(108,140,255,0.12);
    border-radius: 10px;
  }}
  .top5-header {{
    font-size: 0.75rem;
    font-weight: 600;
    color: var(--accent);
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }}
  .top5-list {{
    list-style: none;
    padding: 0;
    margin: 0;
  }}
  .top5-list li {{
    display: flex;
    align-items: center;
    padding: 3px 0;
    font-size: 0.8rem;
    color: var(--text-secondary);
    border-bottom: 1px solid rgba(255,255,255,0.04);
  }}
  .top5-list li:last-child {{ border-bottom: none; }}
  .top5-rank {{
    display: inline-flex;
    align-items: center;
    justify-content: center;
    width: 18px;
    height: 18px;
    border-radius: 50%;
    font-size: 0.7rem;
    font-weight: 700;
    margin-right: 8px;
    flex-shrink: 0;
  }}
  .rank-1 .top5-rank {{ background: rgba(250,204,21,0.2); color: #facc15; }}
  .rank-2 .top5-rank {{ background: rgba(156,163,175,0.2); color: #9ca3af; }}
  .rank-3 .top5-rank {{ background: rgba(205,127,50,0.2); color: #cd7f32; }}
  .rank-other .top5-rank {{ background: rgba(108,140,255,0.1); color: var(--accent); }}
  .top5-name {{
    color: var(--text);
    font-weight: 500;
    flex: 1;
    min-width: 0;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }}
  .top5-name a {{ color: var(--text); text-decoration: none; }}
  .top5-name a:hover {{ color: var(--accent); }}
  .top5-meta {{
    font-size: 0.7rem;
    color: var(--text-secondary);
    margin-left: 8px;
    flex-shrink: 0;
  }}
  .top5-badge {{
    font-size: 0.65rem;
    padding: 1px 6px;
    border-radius: 4px;
    margin-left: 6px;
    flex-shrink: 0;
  }}
  .top5-badge.verified {{ background: rgba(74,222,128,0.12); color: #4ade80; }}
  .top5-badge.new {{ background: rgba(108,140,255,0.12); color: var(--accent); }}
  .top5-badge.updated {{ background: rgba(250,204,21,0.12); color: #facc15; }}

  /* 卡片内容 */
  .card-desc {{
    color: var(--text-secondary);
    font-size: 0.88rem;
    margin: 8px 0 12px;
    flex-grow: 1;
  }}
  .card-position {{
    font-size: 0.8rem;
    color: var(--accent-purple);
    margin-bottom: 10px;
    font-style: italic;
  }}
  .card-tags {{
    display: flex;
    flex-wrap: wrap;
    gap: 4px;
    margin-bottom: 10px;
  }}
  .card-tags .tag {{
    background: rgba(108,140,255,0.1);
    color: var(--accent);
    font-size: 0.75rem;
    padding: 2px 8px;
    border-radius: 4px;
  }}

  /* 特性列表 */
  .features {{
    margin-bottom: 10px;
  }}
  .features summary {{
    font-size: 0.8rem;
    color: var(--text-secondary);
    cursor: pointer;
    user-select: none;
  }}
  .features summary:hover {{ color: var(--text); }}
  .features ul {{
    margin: 6px 0 0 16px;
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.7;
  }}

  /* 优势列表 */
  .strengths {{ font-size: 0.82rem; margin-bottom: 10px; }}
  .strengths strong {{ color: var(--accent-green); font-weight: 500; }}
  .strengths span {{ color: var(--text-secondary); }}

  /* 链接 */
  .card-links {{
    display: flex;
    gap: 10px;
    flex-wrap: wrap;
    margin-top: auto;
    padding-top: 10px;
    border-top: 1px solid var(--border);
  }}
  .card-links a {{
    font-size: 0.78rem;
    color: var(--accent);
    text-decoration: none;
    padding: 3px 10px;
    border-radius: 6px;
    background: rgba(108,140,255,0.08);
  }}
  .card-links a:hover {{
    background: rgba(108,140,255,0.18);
    text-decoration: underline;
  }}

  /* 页脚 */
  .footer {{
    text-align: center;
    padding: 32px;
    color: var(--text-secondary);
    font-size: 0.82rem;
    border-top: 1px solid var(--border);
    margin-top: 40px;
  }}

  /* 许可证 */
  .license {{
    font-size: 0.75rem;
    color: var(--text-secondary);
    margin-bottom: 8px;
  }}

  /* 平板布局 */
  @media (max-width: 900px) {{
    .grid {{ grid-template-columns: repeat(2, 1fr); }}
  }}
  
  /* 手机布局 */
  @media (max-width: 600px) {{
    .grid {{ grid-template-columns: 1fr; }}
    .header h1 {{ font-size: 1.6rem; }}
  }}

  /* ── Release Changelog Section ─────────────────────────────── */
  .releases-section {{
    margin: 32px 0;
  }}
  .releases-controls {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }}
  .releases-search {{
    flex: 1;
    min-width: 200px;
    padding: 8px 14px;
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 8px;
    color: var(--text);
    font-size: 0.9rem;
    outline: none;
    transition: border-color 0.2s;
  }}
  .releases-search:focus {{
    border-color: var(--accent);
  }}
  .releases-filter {{
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }}
  .filter-btn {{
    padding: 5px 12px;
    border-radius: 16px;
    font-size: 0.78rem;
    cursor: pointer;
    border: 1px solid var(--border);
    background: var(--card);
    color: var(--text-secondary);
    transition: all 0.2s;
  }}
  .filter-btn:hover {{
    border-color: var(--accent);
    color: var(--text);
  }}
  .filter-btn.active {{
    background: rgba(108,140,255,0.2);
    border-color: var(--accent);
    color: var(--accent);
  }}
  .releases-header {{
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 20px;
  }}
  .releases-header h2 {{
    font-size: 1.4rem;
    font-weight: 600;
    background: linear-gradient(135deg, #00d4ff, #a78bfa);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    background-clip: text;
  }}
  .release-item {{
    background: var(--card);
    border: 1px solid var(--border);
    border-radius: 12px;
    padding: 18px 20px;
    margin-bottom: 14px;
  }}
  .release-item:hover {{
    border-color: var(--accent);
  }}
  .release-top {{
    display: flex;
    align-items: center;
    gap: 10px;
    margin-bottom: 10px;
    flex-wrap: wrap;
  }}
  .release-name {{
    font-weight: 600;
    font-size: 1rem;
    color: var(--text);
  }}
  .release-version {{
    font-size: 0.85rem;
    color: var(--accent);
    background: rgba(108,140,255,0.1);
    padding: 2px 10px;
    border-radius: 10px;
  }}
  .release-date {{
    font-size: 0.8rem;
    color: var(--text-secondary);
  }}
  .release-tag {{
    font-size: 0.72rem;
    padding: 2px 8px;
    border-radius: 8px;
    font-weight: 600;
  }}
  .release-tag.new {{
    background: rgba(74,222,128,0.15);
    color: #4ade80;
  }}
  .release-tag.updated {{
    background: rgba(250,204,21,0.15);
    color: #facc15;
  }}
  .release-body {{
    font-size: 0.83rem;
    color: var(--text-secondary);
    line-height: 1.7;
    margin-bottom: 10px;
  }}
  .release-body li {{
    margin-bottom: 4px;
  }}
  .diff-summary {{
    margin-top: 10px;
    padding: 10px 14px;
    background: rgba(0,212,255,0.06);
    border-left: 3px solid var(--accent);
    border-radius: 0 8px 8px 0;
    font-size: 0.82rem;
    color: var(--text-secondary);
    line-height: 1.6;
  }}
  .diff-summary strong {{
    color: var(--accent);
  }}
</style>
</head>
<body>
<div class="container">
"""

FOOTER = """
</div>
<div class="footer">
  <p>由 agent-hunter 自动生成 | 数据更新于 {update_time}</p>
  <p>项目地址: <a href="https://github.com/xiowen/agent-hunter" style="color:var(--accent)">github.com/xiowen/agent-hunter</a></p>
</div>
</body>
</html>
"""


def badge_class(open_source: str) -> str:
    mapping = {"yes": "badge-yes", "partial": "badge-partial", "no": "badge-no"}
    return mapping.get(open_source, "badge-no")


def badge_label(open_source: str) -> str:
    mapping = {"yes": "开源", "partial": "部分开源", "no": "闭源"}
    return mapping.get(open_source, open_source)


def render_release_item(name: str, data: dict) -> str:
    """渲染单个 Release Changelog 条目"""
    tag_name = data.get("tag_name", "")
    published_at = data.get("published_at", "")[:10]
    changelog_zh = data.get("changelog_zh", "").strip()
    diff_summary = data.get("diff_summary", "").strip()
    html_url = data.get("html_url", "")
    body_text = data.get("body", "")[:200].lower()  # for filtering

    # Compute days since published
    import datetime
    days_since = 999
    try:
        dt = datetime.datetime.strptime(published_at[:10], "%Y-%m-%d")
        days_since = (datetime.datetime.now() - dt).days
    except Exception:
        pass

    # Determine tag class
    tag_class = "updated"
    if days_since <= 14:
        tag_class = "new"

    # changelog_zh 可能是多行，每行以 · 或数字开头
    bullets_html = ""
    if changelog_zh:
        bullets = []
        for line in changelog_zh.split("\n"):
            line = line.strip()
            if not line:
                continue
            # 保留原样，去掉开头的 · 或数字编号
            if line.startswith("·"):
                line = line[1:].strip()
            elif line[0].isdigit() and ". " in line[:4]:
                line = line.split(". ", 1)[1].strip() if ". " in line else line
            bullets.append(f"<li>{line}</li>")
        if bullets:
            bullets_html = f"<ul>{''.join(bullets)}</ul>"

    diff_html = ""
    if diff_summary:
        # 清理 LLM 可能返回的重复前缀（LLM 返回的 diff_summary 已带 "相较上一版本：" 前缀）
        clean_diff = diff_summary.replace("相较上一版本：", "").strip()
        diff_html = f'<div class="diff-summary"><strong>相较上一版本：</strong>{clean_diff}</div>'

    return f"""
    <div class="release-item" data-name="{name}" data-body="{body_text}" data-tag="{tag_class}" data-days="{days_since}">
      <div class="release-top">
        <span class="release-name">{name}</span>
        <span class="release-tag {tag_class}">{"🆕 新版" if tag_class == "new" else "🔄 更新"}</span>
        <a href="{html_url}" target="_blank" class="release-version">{tag_name}</a>
        <span class="release-date">📅 {published_at}</span>
      </div>
      {f'<div class="release-body">{bullets_html}</div>' if bullets_html else ''}
      {diff_html}
    </div>
    """


def compute_hot_score(agent: dict) -> int:
    """Compute hot score: MIT license +1, github_repo +2, tags +1 each, features +2 each.
    Returns integer score for ranking."""
    score = 0
    if agent.get("license", "").upper() in ("MIT", "APACHE-2.0", "GPL", "BSD"):
        score += 1
    if agent.get("github_repo", "").strip():
        score += 2
    score += len(agent.get("tags", []))
    score += len(agent.get("features", [])) * 2
    return score


def render_top5_section(cat: str, agents_cat: list) -> str:
    """Render TOP 5 hot ranking section for a category.

    Args:
        cat: category name
        agents_cat: list of agent dicts in this category
    Returns HTML string. Empty string if fewer than 2 agents.
    """
    if len(agents_cat) < 2:
        return ""
    # 按热度降序，取前5
    sorted_agents = sorted(agents_cat, key=lambda a: compute_hot_score(a), reverse=True)
    top5 = sorted_agents[:5]
    items_html = ""
    for i, agent in enumerate(top5):
        rank_class = "rank-1" if i == 0 else ("rank-2" if i == 1 else ("rank-3" if i == 2 else "rank-other"))
        name_html = f'<a href="#{agent["id"]}">{agent["name"]}</a>'
        # badge
        badge = ""
        verified = agent.get("last_verified", "")
        if verified:
            from datetime import datetime
            try:
                days_ago = (datetime.now() - datetime.strptime(verified, "%Y-%m-%d")).days
                if days_ago <= 7:
                    badge = '<span class="top5-badge verified">verified</span>'
            except Exception:
                pass
        if not badge and agent.get("github_repo"):
            badge = '<span class="top5-badge new">🔥 hot</span>'
        items_html += f"""
        <li class="{rank_class}">
          <span class="top5-rank">{i + 1}</span>
          <span class="top5-name">{name_html}</span>
          <span class="top5-meta">{agent.get("category", "")}</span>
          {badge}
        </li>"""
    return f"""
    <div class="top5-section">
      <div class="top5-header">🏆 分类热度 TOP5</div>
      <ol class="top5-list">{items_html}</ol>
    </div>"""


def render_releases_section(releases: dict) -> str:
    """渲染所有 Release 条目（带搜索和过滤功能）"""
    items_html = ""
    # 按发布时间倒序
    sorted_releases = sorted(
        releases.items(),
        key=lambda x: x[1].get("published_at", ""),
        reverse=True,
    )
    for name, data in sorted_releases:
        items_html += render_release_item(name, data)

    controls_html = """
      <div class="releases-controls">
        <input type="text" class="releases-search" id="releases-search"
               placeholder="搜索版本名称、仓库或更新内容..."
               oninput="filterReleases()">
        <div class="releases-filter">
          <button class="filter-btn active" data-filter="all" onclick="setFilter(this)">全部</button>
          <button class="filter-btn" data-filter="new" onclick="setFilter(this)">🆕 新版</button>
          <button class="filter-btn" data-filter="updated" onclick="setFilter(this)">🔄 更新</button>
          <button class="filter-btn" data-filter="week" onclick="setFilter(this)">7天内</button>
          <button class="filter-btn" data-filter="month" onclick="setFilter(this)">30天内</button>
        </div>
      </div>
      <script>
      function filterReleases() {
        var q = document.getElementById('releases-search').value.toLowerCase();
        var activeFilter = document.querySelector('.filter-btn.active').dataset.filter;
        var items = document.querySelectorAll('.release-item');
        var count = 0;
        items.forEach(function(item) {
          var text = (item.getAttribute('data-name') || '') + (item.getAttribute('data-body') || '');
          var visible = text.includes(q);
          var tag = item.getAttribute('data-tag') || '';
          var days = parseInt(item.getAttribute('data-days') || '999');
          if (activeFilter === 'new' && !tag.includes('new')) visible = false;
          if (activeFilter === 'updated' && !tag.includes('updated')) visible = false;
          if (activeFilter === 'week' && days > 7) visible = false;
          if (activeFilter === 'month' && days > 30) visible = false;
          item.style.display = visible ? '' : 'none';
          if (visible) count++;
        });
        var zeroMsg = document.getElementById('releases-zero');
        if (zeroMsg) zeroMsg.style.display = count === 0 ? '' : 'none';
      }
      function setFilter(btn) {
        document.querySelectorAll('.filter-btn').forEach(function(b){b.classList.remove('active')});
        btn.classList.add('active');
        filterReleases();
      }
      // Auto-run on page load
      document.addEventListener('DOMContentLoaded', filterReleases);
      </script>
    """
    return f"""
    <div class="releases-section">
      <div class="releases-header">
        <h2>🚀 开源 Agent 版本更新</h2>
      </div>
      {controls_html}
      <div id="releases-list">{items_html}</div>
      <p id="releases-zero" style="display:none;color:var(--text-secondary);text-align:center;padding:20px;">没有匹配的结果</p>
    </div>
    """


def render_card(agent: dict) -> str:
    features_html = ""
    if agent.get("features"):
        items = "".join(f"<li>{f}</li>" for f in agent["features"])
        features_html = f"""
        <details class="features">
          <summary>特性 ({len(agent['features'])})</summary>
          <ul>{items}</ul>
        </details>
        """

    strengths_html = ""
    if agent.get("strengths"):
        s_list = " · ".join(agent["strengths"])
        strengths_html = f'<div class="strengths"><strong>优势:</strong> <span>{s_list}</span></div>'

    tags_html = ""
    if agent.get("tags"):
        tags_html = '<div class="card-tags">' + "".join(
            f'<span class="tag">{t}</span>' for t in agent["tags"]
        ) + "</div>"

    pricing_html = ""
    if agent.get("pricing"):
        pricing_html = f'<span class="tag">{agent["pricing"]}</span>'

    links = ""
    if agent.get("website"):
        links += f'<a href="{agent["website"]}" target="_blank">🌐 官网</a>'
    if agent.get("docs_url"):
        links += f'<a href="{agent["docs_url"]}" target="_blank">📄 文档</a>'
    if agent.get("github_repo"):
        links += f'<a href="{agent["github_repo"]}" target="_blank">🐙 GitHub</a>'

    return f"""
    <div class="card" id="{agent['id']}">
      <div class="card-header">
        <div class="card-title card-title-{agent.get('category', 'Other')}"><a href="{agent.get('website', '#')}" target="_blank">{agent['name']}</a><span class="cat-tag cat-{agent.get('category', 'Other')}">{agent.get('category', 'Other')}</span></div>
        <span class="badge {badge_class(agent.get('open_source', 'no'))}">{badge_label(agent.get('open_source', 'no'))}</span>
      </div>
      {pricing_html}
      <div class="card-desc">{agent['description']}</div>
      <div class="card-position">「{agent['position']}」</div>
      {tags_html}
      {features_html}
      {strengths_html}
      <div class="license">📜 {agent.get('license', '-')}</div>
      <div class="card-links">{links}</div>
    </div>
    """


def generate_report():
    """从 agents/ 加载数据，生成 HTML 报告"""
    meta = {}
    if META_FILE.exists():
        with open(META_FILE) as f:
            meta = json.load(f)

    # 读所有 agent
    agents = []
    for fpath in sorted(AGENTS_DIR.glob("*.json")):
        with open(fpath) as f:
            agent = json.load(f)
            agents.append(agent)

    if not agents:
        warning("agents/ 目录为空，没有数据可生成报告")
        return

    # 按分类分组
    categories = {}
    for cat in CONFIG["categories"]:
        categories[cat] = []
    for agent in agents:
        cat = agent.get("category", "Other")
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(agent)

    # 组装 HTML
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    total = len(agents)
    cat_count = len([c for c in categories.values() if c])

    nav_links = "".join(
        f'<a href="#cat-{cat.lower()}">{cat} ({len(items)})</a>'
        for cat, items in categories.items() if items
    )

    sections = ""
    for cat, items in categories.items():
        if not items:
            continue
        top5_html = render_top5_section(cat, items)
        cards = "".join(render_card(a) for a in items)
        sections += f"""
        <h2 class="section-title section-title-{cat}" id="cat-{cat.lower()}">{cat} ({len(items)})</h2>
        {top5_html}
        <div class="grid">{cards}</div>
        """

    html = HEADER.format(
        total=total,
        categories=cat_count,
    )
    html += f"""
    <div class="header">
      <h1>🤖 AI Agent 产品全景报告</h1>
      <p>全球 AI Agent 产品检索与追踪 · 涵盖 IDE / CLI / TUI / GUI / Plugin / SDK</p>
      <div class="meta">
        <span>📦 {total} 个产品</span>
        <span>🏷 {cat_count} 个分类</span>
        <span>🕐 更新于 {now}</span>
      </div>
    </div>
    <div class="stats">
      <div class="stat-card"><div class="num">{total}</div><div class="label">产品总数</div></div>
      <div class="stat-card"><div class="num">{cat_count}</div><div class="label">分类数</div></div>
      <div class="stat-card"><div class="num">{sum(1 for a in agents if a.get('open_source') == 'yes')}</div><div class="label">开源</div></div>
      <div class="stat-card"><div class="num">{sum(1 for a in agents if a.get('open_source') == 'partial')}</div><div class="label">部分开源</div></div>
      <div class="stat-card"><div class="num">{sum(1 for a in agents if a.get('open_source') == 'no')}</div><div class="label">闭源</div></div>
      <div class="stat-card"><div class="num">{sum(1 for a in agents if a.get('github_repo', '').strip())}</div><div class="label">有 GitHub</div></div>
    </div>
    """

    # ── Release Changelog Section ─────────────────────────────────
    releases = {}
    if RELEASES_FILE.exists():
        with open(RELEASES_FILE) as f:
            releases_data = json.load(f)
            releases = releases_data.get("releases", {})

    if releases:
        html += render_releases_section(releases)

    html += '<div class="category-nav">' + nav_links + '</div>'
    html += sections

    html += FOOTER.format(update_time=now)

    # 写文件
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        f.write(html)

    success(f"报告已生成: {REPORT_FILE} ({total} 个产品)")


if __name__ == "__main__":
    generate_report()
