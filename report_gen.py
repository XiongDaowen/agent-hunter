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

# ── 模板 ────────────────────────────────────────────────────────────────

HEADER = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
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
    color: var(--accent);
  }}

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

  /* 卡片头部 */
  .card-header {{
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    margin-bottom: 8px;
  }}
  .card-title {{
    font-size: 1.15rem;
    font-weight: 600;
  }}
  .card-title a {{
    color: var(--text);
    text-decoration: none;
  }}
  .card-title a:hover {{ color: var(--accent); }}

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

  @media (max-width: 600px) {{
    .grid {{ grid-template-columns: 1fr; }}
    .header h1 {{ font-size: 1.6rem; }}
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
        <div class="card-title"><a href="{agent.get('website', '#')}" target="_blank">{agent['name']}</a></div>
        <span class="badge {badge_class(agent.get('open_source', 'no'))}">{badge_label(agent.get('open_source', 'no'))}</span>
      </div>
      {pricing_html}
      <div class="card-desc">{agent['description']}</div>
      <div class="card-position">「{agent['position']}」</div>
      {tags_html}
      {features_html}
      {strengths_html}
      <div class="license">许可证: {agent.get('license', '-')}</div>
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
        cards = "".join(render_card(a) for a in items)
        sections += f"""
        <h2 class="section-title" id="cat-{cat.lower()}">{cat} ({len(items)})</h2>
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
    </div>
    <div class="category-nav">{nav_links}</div>
    {sections}
    """

    html += FOOTER.format(update_time=now)

    # 写文件
    REPORT_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_FILE, "w") as f:
        f.write(html)

    success(f"报告已生成: {REPORT_FILE} ({total} 个产品)")


if __name__ == "__main__":
    generate_report()
