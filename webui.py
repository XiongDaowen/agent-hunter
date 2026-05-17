#!/usr/bin/env python3
"""agent-hunter WebUI — 基于 Streamlit 的可视化界面"""

import json
import subprocess
import sys
from datetime import datetime
from pathlib import Path

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

# ── 数据加载 ──────────────────────────────────────────────────────────
@st.cache_data(ttl=60)
def load_agents():
    """加载所有 agent 数据"""
    agents = []
    for f in sorted(AGENTS_DIR.glob("*.json")):
        with open(f) as fp:
            agents.append(json.load(fp))
    return agents


@st.cache_data(ttl=60)
def load_meta():
    """加载缓存元数据"""
    if META_FILE.exists():
        with open(META_FILE) as f:
            return json.load(f)
    return {}


def run_command(cmd: str) -> str:
    """运行 CLI 命令并返回输出"""
    try:
        result = subprocess.run(
            [sys.executable, "run.py", cmd],
            capture_output=True, text=True, timeout=300, cwd=BASE_DIR,
        )
        return result.stdout + result.stderr
    except Exception as e:
        return f"执行失败: {e}"


# ── 侧边栏 ────────────────────────────────────────────────────────────
st.sidebar.title("🔍 筛选")

agents = load_agents()
meta = load_meta()

# 搜索框
search = st.sidebar.text_input("搜索", placeholder="名称、描述、标签...")

# 分类筛选
categories = sorted(set(a.get("category", "Other") for a in agents))
selected_cats = st.sidebar.multiselect("分类", categories, default=categories)

# 开源状态
os_options = {"开源": "yes", "部分开源": "partial", "闭源": "no", "未知": "unknown"}
selected_os = st.sidebar.multiselect("开源状态", list(os_options.keys()), default=list(os_options.keys()))

# 排序
sort_by = st.sidebar.selectbox("排序", ["名称", "分类", "最近验证"])

# ── 操作按钮 ──────────────────────────────────────────────────────────
st.sidebar.markdown("---")
st.sidebar.title("⚡ 操作")

if st.sidebar.button("🔍 发现新 Agent", type="primary"):
    with st.spinner("正在搜索新 Agent..."):
        output = run_command("discover")
        st.sidebar.success("发现完成！")
        st.sidebar.code(output[:500])
        st.cache_data.clear()
        agents = load_agents()

if st.sidebar.button("🔄 刷新已有 Agent"):
    with st.spinner("正在刷新..."):
        output = run_command("refresh")
        st.sidebar.success("刷新完成！")
        st.sidebar.code(output[:500])
        st.cache_data.clear()
        agents = load_agents()

if st.sidebar.button("📊 生成报告"):
    with st.spinner("生成中..."):
        output = run_command("report")
        st.sidebar.success("报告已生成！")
        st.sidebar.code(output[:200])

# ── 过滤 ──────────────────────────────────────────────────────────────
filtered = []
for a in agents:
    # 分类
    if a.get("category", "Other") not in selected_cats:
        continue
    # 开源状态
    if a.get("open_source", "unknown") not in [os_options[k] for k in selected_os]:
        continue
    # 搜索
    if search:
        s = search.lower()
        text = f"{a.get('name', '')} {a.get('description', '')} {' '.join(a.get('tags', []))}".lower()
        if s not in text:
            continue
    filtered.append(a)

# 排序
if sort_by == "名称":
    filtered.sort(key=lambda a: a.get("name", ""))
elif sort_by == "分类":
    filtered.sort(key=lambda a: a.get("category", ""))
else:
    filtered.sort(key=lambda a: a.get("last_verified", ""), reverse=True)

# ── 主界面 ────────────────────────────────────────────────────────────
st.title("🤖 AI Agent 产品全景")
st.caption("全球 AI Agent 产品检索与追踪 · 数据自动更新")

# 统计卡片
col1, col2, col3, col4, col5 = st.columns(5)
total = len(agents)
open_count = sum(1 for a in agents if a.get("open_source") == "yes")
partial_count = sum(1 for a in agents if a.get("open_source") == "partial")
closed_count = sum(1 for a in agents if a.get("open_source") == "no")
cat_count = len(set(a.get("category", "Other") for a in agents))

col1.metric("产品总数", total)
col2.metric("分类数", cat_count)
col3.metric("开源", open_count, delta=f"{open_count/total*100:.0f}%" if total else None)
col4.metric("部分开源", partial_count)
col5.metric("闭源", closed_count)

# 分类分布
st.subheader("📊 分类分布")
cat_counts = {}
for a in agents:
    cat = a.get("category", "Other")
    cat_counts[cat] = cat_counts.get(cat, 0) + 1

cols = st.columns(len(cat_counts))
for i, (cat, count) in enumerate(sorted(cat_counts.items())):
    cols[i].metric(cat, count)

# Agent 列表
st.subheader(f"📋 Agent 列表 ({len(filtered)} 个)")

# 按分类分组显示
current_cat = None
for a in filtered:
    if a["category"] != current_cat:
        current_cat = a["category"]
        st.markdown(f"### {current_cat}")

    col1, col2 = st.columns([3, 1])
    with col1:
        st.markdown(f"**[{a['name']}]({a.get('website', '#')})**")
        st.caption(a.get("position", a.get("description", "")[:80]))
        
        # 标签
        if a.get("tags"):
            st.markdown(" · ".join(f"`{t}`" for t in a["tags"][:5]))
        
        # 特性
        if a.get("features"):
            with st.expander(f"特性 ({len(a['features'])})"):
                st.markdown("\n".join(f"- {f}" for f in a["features"]))
    
    with col2:
        # 开源状态
        os_map = {"yes": "🟢 开源", "partial": "🟡 部分开源", "no": "🔴 闭源", "unknown": "⚪ 未知"}
        st.markdown(os_map.get(a.get("open_source", "unknown"), "⚪ 未知"))
        
        # 定价
        if a.get("pricing"):
            st.caption(f"💰 {a['pricing']}")
        
        # 最后验证
        st.caption(f"📅 {a.get('last_verified', '-')}")
        
        # 链接
        links = []
        if a.get("website"):
            links.append(f"[官网]({a['website']})")
        if a.get("github_repo"):
            links.append(f"[GitHub]({a['github_repo']})")
        if a.get("docs_url"):
            links.append(f"[文档]({a['docs_url']})")
        if links:
            st.markdown(" · ".join(links))

    st.divider()

# 页脚
st.markdown("---")
st.caption(f"由 agent-hunter 自动生成 | 更新于 {datetime.now().strftime('%Y-%m-%d %H:%M')}")
