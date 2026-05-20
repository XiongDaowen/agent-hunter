#!/usr/bin/env python3
"""agent-hunter WebUI — 基于 Streamlit 的可视化界面（分类导航版）"""

import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path
from collections import Counter

import streamlit as st

# ── 配置 ──────────────────────────────────────────────────────────────
BASE_DIR = Path(__file__).parent
AGENTS_DIR = BASE_DIR / "agents"
CACHE_DIR = BASE_DIR / "cache"
META_FILE = CACHE_DIR / "meta.json"

st.set_page_config(
    page_title="AI Agent 产品全景",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── 暗色主题 CSS ──────────────────────────────────────────────────────
st.markdown("""
<style>
    /* 全局暗色 */
    .stApp { background: #0f172a; }
    .stMainBlockContainer { padding-top: 0.5rem !important; }
    
    /* 侧边栏 */
    section[data-testid="stSidebar"] { background: #1e293b; }
    section[data-testid="stSidebar"] * { color: #e2e8f0 !important; }
    section[data-testid="stSidebar"] input, section[data-testid="stSidebar"] select, section[data-testid="stSidebar"] textarea { color: #e2e8f0 !important; }
    section[data-testid="stSidebar"] button { background: #334155 !important; border-color: #475569 !important; color: #e2e8f0 !important; }
    section[data-testid="stSidebar"] button:hover { border-color: #60a5fa !important; color: #60a5fa !important; }
    
    /* Pills 分类导航 */
    [data-testid="stPills"] { margin-bottom: 0.5rem !important; }
    [data-testid="stPills"] button { background: #1e293b !important; color: #94a3b8 !important; border: 1px solid #334155 !important; border-radius: 8px !important; padding: 0.5rem 1rem !important; transition: all 0.2s; }
    [data-testid="stPills"] button:hover { border-color: #60a5fa !important; color: #e2e8f0 !important; }
    [data-testid="stPills"] button[aria-selected="true"] { background: linear-gradient(135deg, #3b82f6, #8b5cf6) !important; color: white !important; border-color: transparent !important; }
    
    /* 指标卡片 */
    [data-testid="stMetric"] { background: rgba(255,255,255,0.03) !important; border: 1px solid #334155 !important; border-radius: 12px !important; padding: 1rem !important; }
    [data-testid="stMetric"] label { color: #64748b !important; }
    [data-testid="stMetricValue"] { color: #e2e8f0 !important; }
    
    /* 容器卡片 */
    .stContainer { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 16px !important; padding: 1.5rem !important; }
    
    /* expander */
    .stExpander { background: #1e293b !important; border: 1px solid #334155 !important; border-radius: 12px !important; }
    
    /* 进度条 */
    .stProgress > div > div { background: linear-gradient(90deg, #3b82f6, #a78bfa) !important; }
    
    /* Tab */
    .stTabs [data-baseweb="tab"] { background: #1e293b; color: #94a3b8; border-radius: 8px 8px 0 0; }
    .stTabs [aria-selected="true"] { background: #334155; color: #60a5fa; }
    
    hr { border-color: #334155 !important; }
    
    ::-webkit-scrollbar { width: 8px; }
    ::-webkit-scrollbar-track { background: #0f172a; }
    ::-webkit-scrollbar-thumb { background: #334155; border-radius: 4px; }
</style>
""", unsafe_allow_html=True)

# ── 数据加载 ──────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_agents():
    agents = []
    for f in sorted(AGENTS_DIR.glob("*.json")):
        with open(f) as fp:
            agents.append(json.load(fp))
    return agents


@st.cache_data(ttl=60)
def load_meta():
    if META_FILE.exists():
        with open(META_FILE) as f:
            return json.load(f)
    return {}


# 分类图标映射
CATEGORY_ICONS = {
    "IDE": "💻",
    "CLI": "⌨️",
    "TUI": "🖥️",
    "GUI": "🎨",
    "Plugin": "🔌",
    "SDK": "📦",
    "Runtime": "⚙️",
    "Other": "🤖",
}

OS_STYLE = {
    "yes": ("green", "🟢 开源"),
    "partial": ("orange", "🟡 部分开源"),
    "no": ("red", "🔴 闭源"),
    "unknown": ("grey", "⚪ 未知"),
}


def agent_hot_score(a: dict) -> int:
    """综合热度评分 (没有 github stars 数据时的替代方案)。
    
    评分维度:
      - 开源状态: yes=5, partial=3, no=0
      - 特性数量: 每个 +1
      - 优势数量: 每个 +2
      - 标签数量: 每个 +0.5
      - 有 GitHub 链接: +3
      - 有文档链接: +2
      - 有官网: +1
    """
    score = 0
    # 开源加分
    os_map = {"yes": 5, "partial": 3, "no": 0, "unknown": 0}
    score += os_map.get(a.get("open_source", "unknown"), 0)
    # 内容丰富度
    score += len(a.get("features", [])) * 1
    score += len(a.get("strengths", [])) * 2
    score += len(a.get("tags", [])) * 0.5
    # 链接完整度
    if a.get("github_repo"): score += 3
    if a.get("docs_url"): score += 2
    if a.get("website"): score += 1
    return score


def run_command(cmd: str) -> str:
    try:
        result = subprocess.run(
            [sys.executable, "run.py", cmd],
            capture_output=True, text=True, timeout=300, cwd=BASE_DIR,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"执行失败: {e}"


# ── 加载数据 ──────────────────────────────────────────────────────────
agents = load_agents()
meta = load_meta()

# ── Hero + 统计 ─────────────────────────────────────────────────────
total = len(agents)
open_count = sum(1 for a in agents if a.get("open_source") == "yes")
partial_count = sum(1 for a in agents if a.get("open_source") == "partial")
closed_count = sum(1 for a in agents if a.get("open_source") == "no")
cat_count = len(set(a.get("category", "Other") for a in agents))

st.markdown("""
<div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); border-radius: 20px; padding: 2rem 2rem 0.5rem; margin-bottom: 1rem; text-align: center; border: 1px solid #334155;">
    <h1 style="font-size: 2.5rem; font-weight: 800; background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.3rem;">🤖 AI Agent 产品全景</h1>
    <p style="color: #94a3b8; font-size: 1.1rem;">全球 AI Agent 产品检索与追踪 · 数据自动更新</p>
</div>
""", unsafe_allow_html=True)

cols = st.columns(5)
with cols[0]: st.metric("📦 产品总数", total)
with cols[1]: st.metric("🏷️ 分类数", cat_count)
with cols[2]: st.metric("🟢 开源", open_count)
with cols[3]: st.metric("🟡 部分开源", partial_count)
with cols[4]: st.metric("🔴 闭源", closed_count)

# ── 分类统计 ──────────────────────────────────────────────────────
cat_counts = {}
for a in agents:
    cat = a.get("category", "Other")
    cat_counts[cat] = cat_counts.get(cat, 0) + 1

sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
cat_line = " · ".join(f"{CATEGORY_ICONS.get(c, '🤖')} {c} ({n})" for c, n in sorted_cats)
st.caption(cat_line)

# ── 数据洞察 Tab ──────────────────────────────────────────────────
license_counts = Counter(a.get("license", "未知") for a in agents)
tag_counts = Counter()
for a in agents:
    for tag in a.get("tags", []):
        tag_counts[tag] += 1

open_pct = round(open_count / total * 100) if total else 0
partial_pct = round(partial_count / total * 100) if total else 0
closed_pct = round(closed_count / total * 100) if total else 0
top_tags = tag_counts.most_common(8)

st.markdown("---")
st.subheader("📊 数据洞察")

mi1, mi2, mi3, mi4 = st.columns(4)
mi1.metric("开源占比", f"{open_pct}%")
mi2.metric("部分开源", f"{partial_pct}%")
mi3.metric("闭源", f"{closed_pct}%")
top_lic = license_counts.most_common(1)[0] if license_counts else ("-", 0)
mi4.metric("主流许可证", top_lic[0], help=f"共 {top_lic[1]} 个产品")

if top_tags:
    st.caption("🏷️ 热门标签")
    tags_md = " · ".join(f"**{tag}** ({count})" for tag, count in top_tags)
    st.markdown(tags_md)

# ── 主 Tab 切换 ─────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📦 产品列表", "📰 每日资讯"])

# ── Tab 2: 每日资讯 ──────────────────────────────────────────────────
with tab2:
    st.subheader("📰 每日资讯（HN + Dev.to）")
    if st.button("🔄 刷新资讯", use_container_width=True):
        with st.spinner("正在搜索（30秒内）..."):
            output = run_command("news")
            st.success("资讯已更新！")
            with st.expander("📄 搜索日志"):
                st.code(output)
            st.rerun()

    news_path = BASE_DIR / "report" / "news.html"
    if news_path.exists():
        st.caption(f"📄 [打开资讯报告](/{news_path.relative_to(BASE_DIR)})")
        # 显示资讯条数
        with open(news_path) as f:
            content = f.read()
        card_count = len(re.findall(r'class="news-card"', content))
        st.metric("📬 资讯条数", card_count)
    else:
        st.info("点击上方「刷新资讯」生成第一份报告")

# ── 侧边栏 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🔍 筛选与排序")

    search = st.text_input("搜索", placeholder="名称、描述、标签...", label_visibility="collapsed")

    categories = sorted(set(a.get("category", "Other") for a in agents))
    selected_cats = st.multiselect("分类", categories, default=categories)

    os_options = {"🟢 开源": "yes", "🟡 部分开源": "partial", "🔴 闭源": "no", "⚪ 未知": "unknown"}
    selected_os = st.multiselect("开源状态", list(os_options.keys()), default=list(os_options.keys()))

    sort_options = ["🔥 综合热度", "📛 名称 A-Z", "📂 分类", "🕐 最近验证"]
    sort_by = st.selectbox("排序方式", sort_options)

    st.markdown("---")
    st.subheader("⚡ 操作")

    if st.button("🔍 发现新 Agent", type="primary", use_container_width=True):
        with st.spinner("正在搜索新 Agent（这可能需要 1-3 分钟）..."):
            output = run_command("discover")
            st.success("发现完成！")
            # 解析输出，提取新增 agent 摘要
            lines = output.split("\n")
            new_agents_found = [l for l in lines if "✨" in l or "LLM 发现" in l]
            if new_agents_found:
                st.caption("📋 新增摘要")
                for line in new_agents_found:
                    st.write(line.strip())
            st.caption(f"新增 {sum(1 for l in lines if 'created' in l and 'action' not in l)} 个，共处理 {sum(1 for l in lines if '收集了' in l)} 个来源")
            with st.expander("📄 完整日志"):
                st.code(output)
            st.cache_data.clear()
            st.rerun()

    if st.button("🔄 刷新已有 Agent", use_container_width=True):
        with st.spinner("正在刷新（这可能需要 1-3 分钟）..."):
            output = run_command("refresh")
            st.success("刷新完成！")
            # 解析输出，提取变更摘要
            lines = output.split("\n")
            updated = [l for l in lines if "已更新" in l]
            if updated:
                st.caption(f"📋 更新摘要 ({len(updated)} 个)")
                for line in updated:
                    st.write(line.strip())
            errors = [l for l in lines if "错误" in l or "失败" in l]
            if errors:
                st.caption(f"⚠️ 注意 ({len(errors)} 项)")
                for line in errors:
                    st.write(line.strip())
            with st.expander("📄 完整日志"):
                st.code(output)
            st.cache_data.clear()
            st.rerun()

    if st.button("📊 生成报告", use_container_width=True):
        with st.spinner("生成中..."):
            output = run_command("report")
            st.success("报告已生成！")
            # 显示报告链接
            report_path = BASE_DIR / "report" / "index.html"
            if report_path.exists():
                st.caption(f"📄 [打开报告](/{report_path.relative_to(BASE_DIR)}) — {report_path}")

# ── Tab 1: 产品列表 ─────────────────────────────────────────────────
with tab1:

    # ── 过滤 ────────────────────────────────────────────────────────────
    filtered = []
    for a in agents:
        if a.get("category", "Other") not in selected_cats:
            continue
        if a.get("open_source", "unknown") not in [os_options[k] for k in selected_os]:
            continue
        if search:
            s = search.lower()
            text = f"{a.get('name', '')} {a.get('description', '')} {' '.join(a.get('tags', []))}" .lower()
            if s not in text:
                continue
        filtered.append(a)

    # ── 排序 ────────────────────────────────────────────────────────────
    if sort_by == "📛 名称 A-Z":
        filtered.sort(key=lambda a: a.get("name", ""))
    elif sort_by == "📂 分类":
        filtered.sort(key=lambda a: (a.get("category", ""), a.get("name", "")))
    elif sort_by == "🕐 最近验证":
        filtered.sort(key=lambda a: a.get("last_verified", ""), reverse=True)
    else:  # 综合热度
        filtered.sort(key=agent_hot_score, reverse=True)

    # ── 分类导航 Pills ─────────────────────────────────────────────────
    category_options = ["🔥 全部"] + [f"{CATEGORY_ICONS.get(c, '🤖')} {c} ({n})" for c, n in sorted_cats]
    category_values = ["__ALL__"] + [c for c, _ in sorted_cats]

    pill_to_cat = dict(zip(category_options, category_values))

    selected_pill = st.pills(
        "分类导航",
        options=category_options,
        default="🔥 全部",
        label_visibility="collapsed",
    )
    active_category = pill_to_cat.get(selected_pill, "__ALL__")

    # ── Agent 列表 ──────────────────────────────────────────────────────
    if active_category == "__ALL__":
        display_count = len(filtered)
    else:
        display_count = sum(1 for a in filtered if a["category"] == active_category)
    st.divider()
    st.subheader(f"📋 {'全部' if active_category == '__ALL__' else active_category} · {display_count} 个")

    current_cat = None
    for a in filtered:
        if active_category != "__ALL__" and a["category"] != active_category:
            continue

        if a["category"] != current_cat:
            current_cat = a["category"]
            cat_icon = CATEGORY_ICONS.get(current_cat, "🤖")
            cat_agents = [x for x in filtered if x["category"] == current_cat]
            if active_category == "__ALL__":
                st.subheader(f"{cat_icon} {current_cat} · {len(cat_agents)} 个")

        os_status = a.get("open_source", "unknown")
        os_color, os_label = OS_STYLE.get(os_status, ("grey", "⚪ 未知"))

        with st.container(border=True):
            h1, h2 = st.columns([5, 1])
            with h1:
                st.subheader(a["name"])
            with h2:
                st.markdown(f":{os_color}[{os_label}]")

            if a.get("position"):
                st.caption(f"「{a['position']}」")
            if a.get("description"):
                st.write(a.get("description", ""))

            if a.get("tags"):
                st.caption(" ".join(f"`{t}`" for t in a["tags"][:8]))

            link_cols = st.columns([1, 1, 1, 3])
            col_idx = 0
            if a.get("website"):
                with link_cols[col_idx]:
                    st.link_button("🌐 官网", a["website"])
                col_idx += 1
            if a.get("github_repo"):
                with link_cols[col_idx]:
                    st.link_button("🐙 GitHub", a["github_repo"])
                col_idx += 1
            if a.get("docs_url"):
                with link_cols[col_idx]:
                    st.link_button("📄 文档", a["docs_url"])
                col_idx += 1

            hot = agent_hot_score(a)
            st.caption(f"🔥 热度评分: {hot}  ·  {len(a.get('features', []))} 特性  ·  {len(a.get('strengths', []))} 优势")

            exp_col1, exp_col2 = st.columns(2)
            with exp_col1:
                if a.get("strengths"):
                    with st.expander("💪 核心优势"):
                        for s in a["strengths"][:5]:
                            st.write(f"- {s}")
            with exp_col2:
                if a.get("features"):
                    with st.expander(f"✨ 特性 ({len(a['features'])})"):
                        for f in a["features"][:10]:
                            st.write(f"- {f}")
                        if len(a["features"]) > 10:
                            st.caption(f"... 还有 {len(a['features']) - 10} 个")

            parts = []
            if a.get("pricing"):
                parts.append(f"💰 {a['pricing']}")
            if a.get("license") and a.get("license") != "未知":
                parts.append(f"📜 {a['license']}")
            parts.append(f"📅 {a.get('last_verified', '-')}")
            st.caption(" · ".join(parts))

    # ── 页脚 ────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        f"由 [agent-hunter](https://github.com/xiowen/agent-hunter) 自动生成 | "
        f"更新于 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
