#!/usr/bin/env python3
"""agent-hunter WebUI — 基于 Streamlit 的可视化界面（美化版）"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

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

# ── 自定义 CSS ───────────────────────────────────────────────────────
st.markdown("""
<style>
    /* 全局样式 */
    .main .block-container {
        padding-top: 2rem;
        padding-bottom: 3rem;
        max-width: 1400px;
    }
    
    /* Hero Section */
    .hero {
        background: linear-gradient(135deg, #1a1d2e 0%, #2d1b4e 50%, #1a2d4e 100%);
        border-radius: 16px;
        padding: 3rem 2rem;
        margin-bottom: 2rem;
        text-align: center;
        border: 1px solid #2a2f45;
    }
    .hero h1 {
        font-size: 2.5rem;
        font-weight: 700;
        background: linear-gradient(135deg, #6c8cff, #a78bfa);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.5rem;
    }
    .hero p {
        color: #8b8fa8;
        font-size: 1.1rem;
    }
    
    /* 统计卡片 */
    .stat-card {
        background: linear-gradient(135deg, #1a1d2e, #1e2235);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid #2a2f45;
        text-align: center;
        transition: all 0.3s ease;
    }
    .stat-card:hover {
        border-color: #6c8cff;
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(108, 140, 255, 0.15);
    }
    .stat-card .icon {
        font-size: 2rem;
        margin-bottom: 0.5rem;
    }
    .stat-card .value {
        font-size: 2rem;
        font-weight: 700;
        color: #6c8cff;
    }
    .stat-card .label {
        font-size: 0.85rem;
        color: #8b8fa8;
        margin-top: 0.25rem;
    }
    
    /* Agent 卡片 */
    .agent-card {
        background: #1a1d2e;
        border-radius: 12px;
        padding: 1.25rem;
        border: 1px solid #2a2f45;
        margin-bottom: 1rem;
        transition: all 0.2s ease;
    }
    .agent-card:hover {
        border-color: #6c8cff;
        box-shadow: 0 4px 16px rgba(108, 140, 255, 0.1);
    }
    
    /* 标签 */
    .tag {
        display: inline-block;
        background: rgba(108, 140, 255, 0.15);
        color: #6c8cff;
        padding: 0.2rem 0.6rem;
        border-radius: 6px;
        font-size: 0.75rem;
        margin-right: 0.4rem;
        margin-bottom: 0.3rem;
    }
    
    /* 开源状态标签 */
    .badge-yes { background: rgba(74, 222, 128, 0.15); color: #4ade80; }
    .badge-partial { background: rgba(250, 204, 21, 0.15); color: #facc15; }
    .badge-no { background: rgba(248, 113, 113, 0.15); color: #f87171; }
    
    /* 分类标题 */
    .category-title {
        font-size: 1.3rem;
        font-weight: 600;
        color: #6c8cff;
        margin: 2rem 0 1rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #2a2f45;
    }
    
    /* 侧边栏 */
    .css-1d391kg, .css-1lcbmhc {
        background: #1a1d2e;
    }
    
    /* 隐藏 Streamlit 默认元素 */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
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

# ── Hero Section ──────────────────────────────────────────────────────
total = len(agents)
open_count = sum(1 for a in agents if a.get("open_source") == "yes")
partial_count = sum(1 for a in agents if a.get("open_source") == "partial")
closed_count = sum(1 for a in agents if a.get("open_source") == "no")
cat_count = len(set(a.get("category", "Other") for a in agents))

st.markdown(f"""
<div class="hero">
    <h1>🤖 AI Agent 产品全景</h1>
    <p>全球 AI Agent 产品检索与追踪 · 数据自动更新</p>
    <p style="margin-top: 1rem; font-size: 0.9rem;">
        📦 {total} 个产品 &nbsp;|&nbsp; 🏷 {cat_count} 个分类 &nbsp;|&nbsp; 
        🟢 {open_count} 开源 &nbsp;|&nbsp; 🟡 {partial_count} 部分开源 &nbsp;|&nbsp; 
        🔴 {closed_count} 闭源
    </p>
</div>
""", unsafe_allow_html=True)

# ── 侧边栏 ────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🔍 筛选")
    
    search = st.text_input("搜索", placeholder="名称、描述、标签...")
    
    categories = sorted(set(a.get("category", "Other") for a in agents))
    selected_cats = st.multiselect("分类", categories, default=categories)
    
    os_options = {"🟢 开源": "yes", "🟡 部分开源": "partial", "🔴 闭源": "no", "⚪ 未知": "unknown"}
    selected_os = st.multiselect("开源状态", list(os_options.keys()), default=list(os_options.keys()))
    
    sort_by = st.selectbox("排序", ["名称", "分类", "最近验证"])
    
    st.markdown("---")
    st.markdown("### ⚡ 操作")
    
    if st.button("🔍 发现新 Agent", type="primary", use_container_width=True):
        with st.spinner("正在搜索新 Agent..."):
            output = run_command("discover")
            st.success("发现完成！")
            with st.expander("查看日志"):
                st.code(output[:500])
            st.cache_data.clear()
            st.rerun()
    
    if st.button("🔄 刷新已有 Agent", use_container_width=True):
        with st.spinner("正在刷新..."):
            output = run_command("refresh")
            st.success("刷新完成！")
            with st.expander("查看日志"):
                st.code(output[:500])
            st.cache_data.clear()
            st.rerun()
    
    if st.button("📊 生成报告", use_container_width=True):
        with st.spinner("生成中..."):
            output = run_command("report")
            st.success("报告已生成！")

# ── 过滤 & 排序 ──────────────────────────────────────────────────────
filtered = []
for a in agents:
    if a.get("category", "Other") not in selected_cats:
        continue
    if a.get("open_source", "unknown") not in [os_options[k] for k in selected_os]:
        continue
    if search:
        s = search.lower()
        text = f"{a.get('name', '')} {a.get('description', '')} {' '.join(a.get('tags', []))}".lower()
        if s not in text:
            continue
    filtered.append(a)

if sort_by == "名称":
    filtered.sort(key=lambda a: a.get("name", ""))
elif sort_by == "分类":
    filtered.sort(key=lambda a: a.get("category", ""))
else:
    filtered.sort(key=lambda a: a.get("last_verified", ""), reverse=True)

# ── 统计图表 ──────────────────────────────────────────────────────────
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📊 分类分布")
    cat_counts = {}
    for a in agents:
        cat = a.get("category", "Other")
        cat_counts[cat] = cat_counts.get(cat, 0) + 1
    
    fig = go.Figure(data=[go.Pie(
        labels=list(cat_counts.keys()),
        values=list(cat_counts.values()),
        hole=0.4,
        marker=dict(colors=['#6c8cff', '#a78bfa', '#4ade80', '#facc15', '#f87171', '#60a5fa', '#c084fc']),
        textinfo='label+percent',
        textposition='auto',
    )])
    fig.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e4f0'),
        showlegend=False,
    )
    st.plotly_chart(fig, use_container_width=True)

with col2:
    st.markdown("### 📈 开源状态")
    os_counts = {"开源": open_count, "部分开源": partial_count, "闭源": closed_count}
    fig2 = go.Figure(data=[go.Bar(
        x=list(os_counts.keys()),
        y=list(os_counts.values()),
        marker=dict(color=['#4ade80', '#facc15', '#f87171']),
        text=list(os_counts.values()),
        textposition='outside',
    )])
    fig2.update_layout(
        margin=dict(l=20, r=20, t=20, b=20),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        font=dict(color='#e2e4f0'),
        yaxis=dict(showgrid=False),
        xaxis=dict(showgrid=False),
        showlegend=False,
    )
    st.plotly_chart(fig2, use_container_width=True)

# ── Agent 列表 ────────────────────────────────────────────────────────
st.markdown(f"### 📋 Agent 列表 ({len(filtered)} 个)")

# 按分类分组显示
current_cat = None
for a in filtered:
    if a["category"] != current_cat:
        current_cat = a["category"]
        st.markdown(f'<div class="category-title">{current_cat}</div>', unsafe_allow_html=True)
    
    # 开源状态样式
    os_class = {"yes": "badge-yes", "partial": "badge-partial", "no": "badge-no", "unknown": "badge-no"}
    os_label = {"yes": "开源", "partial": "部分开源", "no": "闭源", "unknown": "未知"}
    badge_cls = os_class.get(a.get("open_source", "unknown"), "badge-no")
    badge_txt = os_label.get(a.get("open_source", "unknown"), "未知")
    
    # 标签 HTML
    tags_html = ""
    if a.get("tags"):
        tags_html = " ".join(f'<span class="tag">{t}</span>' for t in a["tags"][:5])
    
    # 链接
    links = []
    if a.get("website"):
        links.append(f'<a href="{a["website"]}" target="_blank">🌐 官网</a>')
    if a.get("github_repo"):
        links.append(f'<a href="{a["github_repo"]}" target="_blank">🐙 GitHub</a>')
    if a.get("docs_url"):
        links.append(f'<a href="{a["docs_url"]}" target="_blank">📄 文档</a>')
    links_html = " &nbsp;|&nbsp; ".join(links)
    
    # 特性列表
    features_html = ""
    if a.get("features"):
        features_html = "<br>".join(f"• {f}" for f in a["features"][:3])
        if len(a["features"]) > 3:
            features_html += f"<br><i style='color:#8b8fa8'>+{len(a['features'])-3} 更多...</i>"
    
    st.markdown(f"""
    <div class="agent-card">
        <div style="display: flex; justify-content: space-between; align-items: flex-start; margin-bottom: 0.5rem;">
            <div>
                <a href="{a.get('website', '#')}" target="_blank" style="font-size: 1.1rem; font-weight: 600; color: #e2e4f0; text-decoration: none;">
                    {a['name']}
                </a>
                <div style="color: #8b8fa8; font-size: 0.85rem; margin-top: 0.25rem;">
                    {a.get('position', a.get('description', '')[:80])}
                </div>
            </div>
            <span class="badge {badge_cls}" style="padding: 0.2rem 0.6rem; border-radius: 6px; font-size: 0.75rem;">
                {badge_txt}
            </span>
        </div>
        
        {tags_html}
        
        <div style="margin-top: 0.75rem; font-size: 0.85rem; color: #8b8fa8;">
            {features_html}
        </div>
        
        <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 0.75rem; padding-top: 0.5rem; border-top: 1px solid #2a2f45; font-size: 0.8rem; color: #8b8fa8;">
            <div>
                {"💰 " + a.get('pricing', '-') if a.get('pricing') else ''}
                &nbsp;&nbsp; 📅 {a.get('last_verified', '-')}
            </div>
            <div>{links_html}</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ── 页脚 ──────────────────────────────────────────────────────────────
st.markdown("---")
st.markdown(f"""
<div style="text-align: center; color: #8b8fa8; font-size: 0.85rem; padding: 1rem;">
    由 <a href="https://github.com/xiowen/agent-hunter" style="color: #6c8cff; text-decoration: none;">agent-hunter</a> 自动生成 | 
    更新于 {datetime.now().strftime('%Y-%m-%d %H:%M')}
</div>
""", unsafe_allow_html=True)
