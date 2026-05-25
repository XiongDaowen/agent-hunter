#!/usr/bin/env python3
"""agent-hunter WebUI — 基于 Streamlit 的可视化界面（分类导航版）"""

import json
import subprocess
import sys
from datetime import datetime
from difflib import SequenceMatcher
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
        try:
            with open(f) as fp:
                agents.append(json.load(fp))
        except (json.JSONDecodeError, OSError) as e:
            st.warning(f"⚠️ 跳过损坏的 agent 文件: {f.name} ({e})")
            continue
    return agents


@st.cache_data(ttl=60)
def load_meta():
    if META_FILE.exists():
        try:
            with open(META_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, OSError) as e:
            st.warning(f"⚠️ 跳过损坏的 meta.json ({e})，将重建")
    return {}


# 分类图标映射
CATEGORY_COLORS = {
    "IDE": "#a78bfa",
    "CLI": "#4ade80",
    "TUI": "#f472b6",
    "GUI": "#f9a8d4",
    "Plugin": "#fb923c",
    "SDK": "#60a5fa",
    "Runtime": "#facc15",
    "Other": "#94a3b8",
}

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
    """Comprehensive hot score (used when GitHub stars data is unavailable).

    Scoring dimensions:
      - Open source: yes=5, partial=3, no=0
      - Features count: +1 each
      - Strengths count: +2 each
      - Tags count: +0.5 each
      - Has GitHub link: +3
      - Has docs link: +2
      - Has website: +1
    Returns integer score.
    """
    score = 0
    # Open source bonus
    os_map = {"yes": 5, "partial": 3, "no": 0, "unknown": 0}
    score += os_map.get(a.get("open_source", "unknown"), 0)
    # Content richness
    score += len(a.get("features", [])) * 1
    score += len(a.get("strengths", [])) * 2
    score += (len(a.get("tags", [])) * 5) // 10  # integer division → always int
    # Link completeness
    if a.get("github_repo"): score += 3
    if a.get("docs_url"): score += 2
    if a.get("website"): score += 1
    return score


def fuzzy_score(query: str, text: str) -> int:
    """计算模糊匹配分数 (0-100)。"""
    if not query or not text:
        return 0
    query = query.lower()
    text = text.lower()
    # 精确匹配得满分
    if query in text:
        return 100
    # 使用 SequenceMatcher 计算相似度
    return int(SequenceMatcher(None, query, text).ratio() * 100)


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

# Enrich agents with last_updated from meta.json
for a in agents:
    name_key = a.get("name", "").lower().replace(" ", "-")
    if name_key in meta:
        a["last_updated"] = meta[name_key].get("last_updated", "")

# ── 主 Tab 切换 ─────────────────────────────────────────────────────
tab1, tab2 = st.tabs(["📦 产品列表", "📰 每日资讯"])

# ── Tab 2: 每日资讯 ──────────────────────────────────────────────────
with tab2:
    st.subheader("📰 每日资讯（HN + Dev.to）")
    if st.button("🔄 刷新资讯", use_container_width=True):
        with st.spinner("正在搜索（约30秒）..."):
            output = run_command("news")
            st.success("资讯已更新！")
            with st.expander("📄 搜索日志"):
                st.code(output)
            st.rerun()

    news_data_file = BASE_DIR / "cache" / "news.json"
    if news_data_file.exists():
        with open(news_data_file) as f:
            news_data = json.load(f)

        total = news_data.get("total", 0)
        updated = news_data.get("updated", "")
        st.caption(f"📅 更新时间: {updated} | 共 {total} 条")

        for topic_name, topic in news_data.get("topics", {}).items():
            icon = topic.get("icon", "📌")
            label = topic.get("label", topic_name)
            items = topic.get("items", [])
            count = topic.get("count", len(items))

            if not items:
                continue

            with st.expander(f"{icon} {label} ({count})", expanded=False):
                for item in items:
                    title = item.get("title", "无标题")
                    url = item.get("url", "#")
                    desc = item.get("description", "")
                    source = item.get("source", "")
                    time_ago = item.get("time_ago", "")
                    meta = item.get("_meta", "")

                    # Source badge color
                    if source == "HN":
                        src_color = "#ff6600"
                    elif source == "Dev.to":
                        src_color = "#3b49df"
                    else:
                        src_color = "#94a3b8"

                    col1, col2 = st.columns([4, 1])
                    with col1:
                        st.markdown(f"**[{title}]({url})**")
                        if desc:
                            st.caption(desc[:120])
                        st.caption(f":{src_color}[{source}] {meta}")
                    with col2:
                        st.caption(f"⏱ {time_ago}" if time_ago else "")
                    st.divider()

    # ── 版本更新 ────────────────────────────────────────────────
    st.markdown("---")
    st.subheader("🚀 开源项目版本更新")
    releases_file = BASE_DIR / "data" / "releases.json"
    if releases_file.exists():
        with open(releases_file) as f:
            rdata = json.load(f)
        releases = rdata.get("releases", {})
        if releases:
            sorted_r = sorted(releases.items(), key=lambda x: x[1].get("published_at", ""), reverse=True)
            from datetime import datetime as dt
            for name, data in sorted_r:
                tag = data.get("tag_name", "")
                pub = data.get("published_at", "")[:10]
                url = data.get("html_url", "")
                cl = data.get("changelog_zh", "").strip()
                diff = data.get("diff_summary", "").strip()
                try:
                    days = (dt.now() - dt.strptime(pub, "%Y-%m-%d")).days
                    fresh = "🆕" if days <= 14 else "🔄"
                except Exception:
                    fresh = "🔄"
                repo = "/".join(name.split("/")[-2:]) if "/" in name else name
                with st.container(border=True):
                    c1, c2 = st.columns([4, 1])
                    with c1:
                        st.markdown(f"**{fresh} {repo}**  [{tag}]({url})")
                    with c2:
                        st.caption(f"📅 {pub}")
                    if cl:
                        bullets = []
                        for line in cl.split("\n"):
                            line = line.strip()
                            if not line:
                                continue
                            if line.startswith("·"):
                                line = line[1:].strip()
                            bullets.append(line)
                        if bullets:
                            with st.expander(f"📋 更新内容 ({len(bullets)} 项)", expanded=False):
                                for b in bullets:
                                    st.write(f"- {b}")
                    if diff:
                        st.caption(f"📊 **相较上一版本：** {diff.replace('相较上一版本：', '').strip()}")

    else:
        st.info("暂无资讯数据，点击上方「刷新资讯」")

# ── 侧边栏 ──────────────────────────────────────────────────────────
with st.sidebar:
    st.subheader("🔍 筛选与排序")

    search = st.text_input("搜索", placeholder="名称/描述/标签...（支持模糊匹配）", label_visibility="collapsed")

    categories = sorted(set(a.get("category", "Other") for a in agents))
    selected_cats = st.multiselect("分类", categories, default=categories)

    os_options = {"🟢 开源": "yes", "🟡 部分开源": "partial", "🔴 闭源": "no", "⚪ 未知": "unknown"}
    selected_os = st.multiselect("开源状态", list(os_options.keys()), default=list(os_options.keys()))
    os_only = st.toggle("🟢 仅显示开源", value=False, help="只显示完全开源的产品")
    gh_only = st.toggle("🐙 仅显示有 GitHub", value=False, help="只显示有 GitHub 链接的产品")

    # Last verified filter: hide agents not verified within N days
    st.caption("⏱️ 验证时间")
    max_age_col1, max_age_col2 = st.columns([1, 1])
    with max_age_col1:
        max_age_days = st.number_input("天内", min_value=0, max_value=365, value=0, step=7, label_visibility="collapsed")
    with max_age_col2:
        st.caption(f"未验证 > {max_age_days}天" if max_age_days > 0 else "显示全部")

    sort_options = ["🔥 综合热度", "📛 名称 A-Z", "📂 分类", "🕐 最近验证", "📜 许可证", "🕐 最近更新"]
    sort_by = st.selectbox("排序方式", sort_options)

    # 提示：如何重置筛选
    st.caption("💡 提示：刷新页面可重置所有筛选条件")

    st.markdown("---")
    st.subheader("⚡ 操作")

    if st.button("🔍 发现新 Agent", type="primary", use_container_width=True):
        with st.spinner("正在搜索新 Agent（这可能需要 1-3 分钟）..."):
            output = run_command("discover")
            st.success("发现完成！")
            # 解析输出，提取新增 agent 摘要
            lines = output.split("\n")
            new_agents_found = [l for l in lines if "✨" in l or "LLM 发现" in l]
            new_count = sum(1 for l in lines if "created" in l and "action" not in l)
            source_count = 1 if any("收集了" in l for l in lines) else 0
            if new_agents_found:
                st.caption("📋 新增摘要")
                for line in new_agents_found:
                    st.write(line.strip())
                st.caption(f"✅ 发现 {new_count} 个新 Agent，共扫描 {source_count} 个来源")
            else:
                st.info("🔍 未发现新 Agent（数据库已是最新，或搜索源无可用结果）")
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
            else:
                st.info("✅ 所有 Agent 已是最新状态，无需更新")
            errors = [l for l in lines if "错误" in l or "失败" in l]
            if errors:
                st.caption(f"⚠️ 注意 ({len(errors)} 项)")
                for line in errors:
                    st.write(line.strip())
            with st.expander("📄 完整日志"):
                st.code(output)
            st.cache_data.clear()
            st.rerun()

# ── Comparison state (initialize once, skip on rerun) ──────────────────
if "compare_selected" not in st.session_state:
    st.session_state.compare_selected = set()
if "show_compare" not in st.session_state:
    st.session_state.show_compare = False

# ── Tab 1: Product List ───────────────────────────────────────────────
with tab1:

    # ── Hero + 统计 ─────────────────────────────────────────────────
    total = len(agents)
    open_count = sum(1 for a in agents if a.get("open_source") == "yes")
    partial_count = sum(1 for a in agents if a.get("open_source") == "partial")
    closed_count = sum(1 for a in agents if a.get("open_source") == "no")
    cat_count = len(set(a.get("category", "Other") for a in agents))

    st.markdown("""
    <div style="background: linear-gradient(135deg, #0f172a 0%, #1e1b4b 50%, #0f172a 100%); border-radius: 16px; padding: 1.5rem 2rem 0.5rem; margin-bottom: 0.5rem; text-align: center; border: 1px solid #334155;">
        <h1 style="font-size: 2rem; font-weight: 800; background: linear-gradient(135deg, #60a5fa, #a78bfa, #f472b6); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin-bottom: 0.2rem;">🤖 AI Agent 产品全景</h1>
        <p style="color: #94a3b8; font-size: 0.95rem;">全球 AI Agent 产品检索与追踪 · 数据自动更新</p>
    </div>
    """, unsafe_allow_html=True)

    cols = st.columns(6)
    with cols[0]: st.metric("📦 产品总数", total)
    with cols[1]: st.metric("🏷️ 分类数", cat_count)
    with cols[2]: st.metric("🟢 开源", open_count)
    with cols[3]: st.metric("🟡 部分开源", partial_count)
    with cols[4]: st.metric("🔴 闭源", closed_count)
    gh_count = sum(1 for a in agents if a.get("github_repo"))
    with cols[5]: st.metric("🐙 有GitHub", gh_count)

    # Category distribution
    COLORS = {
        "IDE": "#a78bfa", "CLI": "#34d399", "TUI": "#f87171",
        "GUI": "#f472b6", "Plugin": "#fb923c", "SDK": "#60a5fa", "Runtime": "#fbbf24"
    }
    cat_counts = {}
    for a in agents:
        cat = a.get("category", "Other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    sorted_cats = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)
    max_count = sorted_cats[0][1] if sorted_cats else 1

    bar_cols = st.columns(len(sorted_cats))
    for i, (cat, n) in enumerate(sorted_cats):
        with bar_cols[i]:
            pct = int(n / max_count * 100)
            icon = CATEGORY_ICONS.get(cat, "🤖")
            color = COLORS.get(cat, "#94a3b8")
            bar_w = max(pct, 8)
            html = (
                '<div style="text-align:center">'
                '<div style="font-size:1.2rem">' + icon + '</div>'
                '<div style="background:#1e293b;border-radius:6px;height:8px;width:100%;margin:4px 0">'
                '<div style="background:' + color + ';height:8px;border-radius:6px;width:' + str(bar_w) + '%"></div>'
                '</div>'
                '<div style="font-size:0.8rem;color:#e2e8f0">' + str(n) + '</div>'
                '<div style="font-size:0.7rem;color:#64748b">' + cat + '</div>'
                '</div>'
            )
            st.markdown(html, unsafe_allow_html=True)

    cat_line = " · ".join(f"{CATEGORY_ICONS.get(c, '🤖')} {c} ({n})" for c, n in sorted_cats)
    st.caption(cat_line)

    # ── 数据洞察 ────────────────────────────────────────────────
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

    # ── Comparison Bar (shown when ≥2 agents selected) ──────────────────
    sel = st.session_state.compare_selected
    sel_len = len(sel)
    if sel_len >= 2:
        st.info(f"📊 已选中 {sel_len} 个 Agent。")
        comp_col1, comp_col2, comp_col3 = st.columns([1, 1, 4])
        with comp_col1:
            max_compare = 5
            if st.button(f"🔍 对比 ({sel_len})", type="primary", disabled=(sel_len > max_compare)):
                st.session_state.show_compare = True
        with comp_col2:
            if st.button("🗑️ 清空选择"):
                st.session_state.compare_selected = set()
                st.session_state.show_compare = False
        if sel_len > max_compare:
            st.warning(f"⚠️ 最多对比 {max_compare} 个 Agent，当前 {sel_len} 个已选中")
    elif sel_len == 1:
        st.caption("💡 至少选中 2 个 Agent 才能对比（点击卡片内的 ☑ 按钮添加）")
    # else: no agents selected — silent

    # ── 过滤 ────────────────────────────────────────────────────────────
    # 预计算开源状态过滤集，避免每次循环都重复创建列表
    valid_open_sources = {os_options[k] for k in selected_os}
    # 如果开启了"仅显示开源"开关，强制覆盖为只有 "yes"
    if os_only:
        valid_open_sources = {"yes"}
    filtered = []
    for a in agents:
        if a.get("category", "Other") not in selected_cats:
            continue
        if a.get("open_source", "unknown") not in valid_open_sources:
            continue
        if gh_only and not a.get("github_repo"):
            continue
        # Filter by last verified age (naive date parsing — last_verified uses local date format YYYY-MM-DD)
        if max_age_days > 0:
            last_verified = a.get("last_verified", "")
            if last_verified:
                try:
                    from datetime import datetime, timezone
                    from dateutil import parser as dateutil_parser
                    lv_date = dateutil_parser.parse(last_verified)
                    # Normalize to naive for consistent comparison with datetime.now()
                    if lv_date.tzinfo is not None:
                        lv_date = lv_date.replace(tzinfo=None)
                    age_days = (datetime.now() - lv_date).days
                    if age_days > max_age_days:
                        continue
                except (ValueError, TypeError):
                    pass
            # Agents without last_verified are kept (show them unless explicitly excluded)
        if search:
            s = search.lower().strip()
            if not s:
                a["_search_score"] = 100
            else:
                # 多层级搜索匹配：name > description > tags（权重递增）
                name_lower = a.get("name", "").lower()
                desc_lower = a.get("description", "").lower()
                tags_str = " ".join(a.get("tags", [])).lower()

                name_score = fuzzy_score(s, name_lower)  # 100=精确包含, 0-99=模糊相似度
                desc_score = int(fuzzy_score(s, desc_lower) * 0.6)   # 降权
                tags_score = int(fuzzy_score(s, tags_str) * 0.4)     # 再降权

                combined_score = max(name_score, desc_score, tags_score)

                if combined_score < 25:  # 阈值（原30），更宽容匹配
                    continue
                a["_search_score"] = combined_score
                a["_name_score"] = name_score
        else:
            a["_search_score"] = 100
            a["_name_score"] = 50
        filtered.append(a)

    # ── 排序 ────────────────────────────────────────────────────────────
    if sort_by == "📛 名称 A-Z":
        filtered.sort(key=lambda a: a.get("name", ""))
    elif sort_by == "📂 分类":
        filtered.sort(key=lambda a: (a.get("category", ""), a.get("name", "")))
    elif sort_by == "🕐 最近验证":
        filtered.sort(key=lambda a: a.get("last_verified", ""), reverse=True)
    elif sort_by == "📜 许可证":
        filtered.sort(key=lambda a: a.get("license", "zzz"))
    elif sort_by == "🕐 最近更新":
        # Sort by last_updated field (release/changelog date) descending
        filtered.sort(key=lambda a: a.get("last_updated", ""), reverse=True)
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

    # Pre-compute category agent lists once to avoid O(n²) re-computation in the loop
    cat_agents_cache = {}
    for a in filtered:
        cat = a.get("category", "Other")
        if cat not in cat_agents_cache:
            cat_agents_cache[cat] = []
        cat_agents_cache[cat].append(a)

    # ── Agent count header ─────────────────────────────────────────────
    if active_category == "__ALL__":
        display_count = len(filtered)
    else:
        display_count = sum(1 for a in filtered if a["category"] == active_category)
    st.divider()
    st.subheader(f"📋 {'全部' if active_category == '__ALL__' else active_category} · {display_count} 个")

    # ── No results state ──────────────────────────────────────────────
    if display_count == 0:
        st.warning("🔍 未找到匹配的产品，请尝试以下方式：")
        col1, col2 = st.columns(2)
        with col1:
            st.markdown("**可能原因：**")
            st.markdown("- 筛选条件过于严格（分类/开源状态/GitHub过滤）")
            st.markdown("- 搜索词没有匹配到任何 agent")
            st.markdown("- 活跃分类下没有符合条件的产品")
        with col2:
            st.markdown("**快速修复：**")
            if st.button("🔄 清空所有筛选条件", use_container_width=True, key="clear_filters_no_results"):
                # Reset all filter widgets by clearing session state and rerunning
                st.session_state.clear()
                st.rerun()
            if search:
                st.caption(f"当前搜索词：`{search}`")
                if st.button("❌ 清除搜索词", key="clear_search_noResults"):
                    st.session_state.clear()
                    st.rerun()
        st.markdown("---")

# ── TOP5 Category Ranking ──────────────────────────────────────────
    def render_webui_top5(cat_name: str, cat_list: list):
        """Render compact TOP5 ranking for a category in WebUI with colored medals."""
        if len(cat_list) < 2:
            return
        scored = [(agent_hot_score(a), a) for a in cat_list]
        scored.sort(key=lambda x: x[0], reverse=True)
        top5 = scored[:5]
        medals = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣"]
        parts = []
        for i, (s, a) in enumerate(top5):
            name = a['name']
            score = f"{s}"
            if i < 3:
                parts.append(f"**{medals[i]} {name}**({score})")
            else:
                parts.append(f"{medals[i]} **{name}**({score})")
        st.caption("🏆 TOP5: " + " · ".join(parts))

    # Show TOP5 ranking for selected single category
    if active_category != "__ALL__" and active_category in cat_agents_cache:
        with st.expander("🏆 分类热度 TOP5", expanded=False):
            render_webui_top5(active_category, cat_agents_cache[active_category])

    current_cat = None

    for a in filtered:
        if active_category != "__ALL__" and a["category"] != active_category:
            continue

        if a["category"] != current_cat:
            current_cat = a["category"]
            cat_icon = CATEGORY_ICONS.get(current_cat, "🤖")
            cat_color_hdr = CATEGORY_COLORS.get(current_cat, "#94a3b8")
            if active_category == "__ALL__":
                st.markdown(f"<h4 style='color:{cat_color_hdr}; margin-bottom:0.2rem;'>{cat_icon} {current_cat} · {len(cat_agents_cache[current_cat])} 个</h4>", unsafe_allow_html=True)

        cat_icon = CATEGORY_ICONS.get(a["category"], "🤖")
        os_status = a.get("open_source", "unknown")
        os_color, os_label = OS_STYLE.get(os_status, ("grey", "⚪ 未知"))

        cat_color = CATEGORY_COLORS.get(a["category"], "#94a3b8")
        with st.container(border=True):
            h1, h2, h3 = st.columns([5, 1, 1])
            with h1:
                st.markdown(f"<span style='color:{cat_color}; font-weight:700;'>{cat_icon} {a['name']}</span>", unsafe_allow_html=True)
            with h2:
                st.markdown(f":{os_color}[{os_label}]")
            with h3:
                checked = a["name"] in st.session_state.compare_selected
                changed = st.checkbox("☑", value=checked, key=f"cb_{a['name']}")
                if changed:
                    if checked:
                        st.session_state.compare_selected.discard(a["name"])
                    else:
                        if len(st.session_state.compare_selected) < 5:
                            st.session_state.compare_selected.add(a["name"])

            if a.get("position"):
                st.caption(f"「{a['position']}」")
            if a.get("description"):
                desc_text = a.get("description", "")
                # Truncate long descriptions to prevent card overflow
                MAX_DESC_LEN = 150
                if len(desc_text) > MAX_DESC_LEN:
                    st.caption(desc_text[:MAX_DESC_LEN] + "…")
                else:
                    st.write(desc_text)

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
            feat_n = len(a.get('features', []))
            str_n = len(a.get('strengths', []))
            st.caption(f"🔥 热度: {hot} · 🔧 {feat_n} 特性 · 💪 {str_n} 优势")

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

# ── Date badge (prominent, color-coded by age) ──────────────────
        from datetime import datetime as dt
        lv = a.get("last_verified", "")
        badge_html = ""
        if lv:
            try:
                from dateutil import parser as dp
                lv_dt = dp.parse(lv)
                if lv_dt.tzinfo: lv_dt = lv_dt.replace(tzinfo=None)
                age = (dt.now() - lv_dt).days
                if age <= 7:
                    badge_style = "background:#064e3b;color:#34d399;"
                elif age <= 30:
                    badge_style = "background:#1e3a5f;color:#60a5fa;"
                elif age <= 90:
                    badge_style = "background:#3b1c1c;color:#fbbf24;"
                else:
                    badge_style = "background:#3b0d0d;color:#f87171;"
                badge_html = f"<span style='{badge_style}border-radius:6px;padding:2px 8px;font-size:0.75rem;margin-left:4px;'>{lv}</span>"
            except Exception:
                badge_html = f"<span style='background:#334155;color:#94a3b8;border-radius:6px;padding:2px 8px;font-size:0.75rem;margin-left:4px;'>{lv}</span>"

        parts = []
        if a.get("pricing"):
            parts.append(f"💰 {a['pricing']}")
        if a.get("license") and a.get("license") != "未知":
            parts.append(f"📜 {a['license']}")
        parts.append(f"📅 {lv or '-'}")
        st.caption(" · ".join(parts) + ("&nbsp;" + badge_html if badge_html else ""), unsafe_allow_html=True)

    # ── Comparison Modal ─────────────────────────────────────────────────
    if st.session_state.get("show_compare", False) and len(st.session_state.compare_selected) >= 2:
        st.divider()
        # Compact navigation header inside the modal
        st.markdown("👆 [▲ 返回产品列表](#tab1)", unsafe_allow_html=True)
        st.subheader("📊 Agent 对比视图")
        compare_names = list(st.session_state.compare_selected)
        # Build a matrix of agents by name
        agents_by_name = {a["name"]: a for a in agents}
        comp_agents = [agents_by_name[n] for n in compare_names if n in agents_by_name]

        if comp_agents:
            # ── Field comparison rows ─────────────────────────────────────
            fields = [
                ("分类", "category"),
                ("开源", "open_source"),
                ("许可证", "license"),
                ("定价", "pricing"),
                ("官网", "website"),
                ("GitHub", "github_repo"),
                ("文档", "docs_url"),
                ("热度评分", None),  # computed
                ("特性数", None),  # computed
                ("优势数", None),  # computed
                ("标签数", None),  # computed
                ("最后验证", "last_verified"),  # data quality indicator
                ("最后更新", "last_updated"),  # release/changelog date
            ]
            for label, key in fields:
                row_cols = st.columns([2] + [1] * len(comp_agents))
                with row_cols[0]:
                    st.markdown(f"**{label}**")
                for i, a in enumerate(comp_agents):
                    with row_cols[i + 1]:
                        if key is None:
                            if label == "热度评分":
                                st.write(str(agent_hot_score(a)))
                            elif label == "特性数":
                                st.write(str(len(a.get("features", []))))
                            elif label == "优势数":
                                st.write(str(len(a.get("strengths", []))))
                            elif label == "标签数":
                                st.write(str(len(a.get("tags", []))))
                            else:
                                st.write("-")
                        else:
                            val = a.get(key, "-") or "-"
                            if key in ("website", "github_repo", "docs_url") and val and val != "-":
                                st.markdown(f"[🔗]({val})")
                            else:
                                st.write(str(val)[:30])

            # ── Description comparison ────────────────────────────────────
            st.markdown("**描述**")
            for a in comp_agents:
                desc_text = a.get('description', '-')
                # Truncate long descriptions to prevent overly tall comparison rows
                MAX_COMPARE_DESC = 120
                if len(desc_text) > MAX_COMPARE_DESC:
                    desc_text = desc_text[:MAX_COMPARE_DESC] + "…"
                with st.container():
                    st.markdown(f"**{a['name']}**: {desc_text}")

            # ── Features comparison (table) ──────────────────────────────
            if any(a.get("features") for a in comp_agents):
                st.markdown("**✨ 特性对比**")
                # Collect all unique features from selected agents
                all_features = []
                for a in comp_agents:
                    for f in a.get("features", []):
                        if f not in all_features:
                            all_features.append(f)
                # Render markdown table: rows=features, cols=agent names
                # Use medium font for readability; truncate agent names to 20 chars
                headers = ["✨ 特性"] + [a["name"][:20].ljust(20) for a in comp_agents]
                col_count = len(headers)
                header_row = "| " + " | ".join(headers) + " |"
                sep_row = "| " + " | ".join(["---"] * col_count) + " |"
                table_lines = [header_row, sep_row]
                for f in all_features[:20]:  # cap rows at 20 (increased from 15)
                    row = [f[:45]]  # increased from 40
                    for a in comp_agents:
                        row.append("✅" if f in a.get("features", []) else "—")
                    table_lines.append("| " + " | ".join(row) + " |")
                st.markdown("\n".join(table_lines))
                st.caption(f"共 {len(all_features)} 个特性，显示前 {min(20, len(all_features))} 个")

            # ── Pricing comparison (table) ────────────────────────────────
            if any(a.get("pricing") for a in comp_agents):
                st.markdown("**💰 价格对比**")
                pricing_rows = []
                for a in comp_agents:
                    p = a.get("pricing", "-")
                    pricing_rows.append((a["name"][:20].ljust(20), p if p else "-"))
                if pricing_rows:
                    # Simple vertical list layout for pricing (avoids wide-table issues)
                    for name_col, price_col in pricing_rows:
                        st.markdown(f"| **{name_col}** | {price_col} |")
                    st.caption("💡 价格信息仅供参考，以各产品官网为准")

            # ── Strengths comparison (table) ─────────────────────────────────
            if any(a.get("strengths") for a in comp_agents):
                st.markdown("**💪 优势对比**")
                all_strengths = []
                for a in comp_agents:
                    for s in a.get("strengths", []):
                        if s not in all_strengths:
                            all_strengths.append(s)
                headers_s = ["💪 优势"] + [a["name"][:20].ljust(20) for a in comp_agents]
                col_count_s = len(headers_s)
                header_row_s = "| " + " | ".join(headers_s) + " |"
                sep_row_s = "| " + " | ".join(["---"] * col_count_s) + " |"
                table_lines_s = [header_row_s, sep_row_s]
                for s in all_strengths[:15]:  # increased from 10
                    row_s = [s[:45]]  # increased from 40
                    for a in comp_agents:
                        row_s.append("✅" if s in a.get("strengths", []) else "—")
                    table_lines_s.append("| " + " | ".join(row_s) + " |")
                st.markdown("\n".join(table_lines_s))
                st.caption(f"共 {len(all_strengths)} 个优势，显示前 {min(15, len(all_strengths))} 个")

            # Close comparison button
            if st.button("🔒 关闭对比视图"):
                st.session_state.show_compare = False
                st.rerun()

    # ── 页脚 ────────────────────────────────────────────────────────────
    st.divider()
    st.caption(
        f"由 [agent-hunter](https://github.com/xiowen/agent-hunter) 自动生成 | "
        f"更新于 {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    )
