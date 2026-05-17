#!/usr/bin/env python3
"""
agent-hunter — 全球 AI Agent 产品检索与追踪工具

用法:
  python hunter.py update     # 更新所有 agent 条目（检查变化后更新）
  python hunter.py report     # 生成 HTML 报告
  python hunter.py run        # update + report
  python hunter.py status     # 查看缓存状态

设计:
  - 每个 agent 一个 JSON 文件存在 agents/ 目录
  - cache/meta.json 记录每个文件的内容 hash 和最后更新时间
  - 更新时对比 hash，有变化才写新文件、更新缓存
  - 支持每天定时运行，只处理变化的条目
"""

import json
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from logger import info, success, warning, error, debug, step, sub_step

# ── 路径与配置 ──────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"

with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

AGENTS_DIR = BASE_DIR / CONFIG["agents_dir"]
CACHE_DIR = BASE_DIR / CONFIG["cache_dir"]
REPORT_DIR = BASE_DIR / CONFIG["report_dir"]
META_FILE = BASE_DIR / CONFIG["meta_file"]
REPORT_FILE = BASE_DIR / CONFIG["report_file"]
UPDATE_INTERVAL = CONFIG["update_interval_hours"] * 3600

AGENTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

# ── 数据模型 ────────────────────────────────────────────────────────────

REQUIRED_FIELDS = {
    "id": str,
    "name": str,
    "category": str,
    "description": str,
    "features": list,
    "open_source": str,          # "yes" | "partial" | "no"
    "license": str,
    "strengths": list,
    "position": str,
    "website": str,
    "docs_url": str,
    "github_repo": str,
    "last_verified": str,        # ISO 日期
}

OPTIONAL_FIELDS = {
    "pricing": str,
    "logo_url": str,
    "tags": list,
    "notes": str,
}

AGENT_SCHEMA = {**REQUIRED_FIELDS, **OPTIONAL_FIELDS}


def validate_agent(data):
    """验证 agent 数据，返回 (ok, errors)"""
    errors = []
    for field, ftype in REQUIRED_FIELDS.items():
        if field not in data:
            errors.append(f"缺少必填字段: {field}")
        elif not isinstance(data[field], ftype):
            errors.append(f"字段 {field} 类型错误: 期望 {ftype.__name__}, 实际 {type(data[field]).__name__}")
    for field in data:
        if field not in AGENT_SCHEMA:
            errors.append(f"未知字段: {field}")
    if not errors and data["category"] not in CONFIG["categories"]:
        errors.append(f"无效分类: {data['category']}, 允许: {CONFIG['categories']}")
    return (len(errors) == 0, errors)


# ── 缓存层 ──────────────────────────────────────────────────────────────

def file_hash(content: str) -> str:
    """计算内容的 SHA256 哈希"""
    return hashlib.sha256(content.encode("utf-8")).hexdigest()


def load_meta() -> dict:
    """加载缓存元数据"""
    if META_FILE.exists():
        with open(META_FILE) as f:
            return json.load(f)
    return {}


def save_meta(meta: dict):
    """保存缓存元数据"""
    META_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(META_FILE, "w") as f:
        json.dump(meta, f, indent=2, ensure_ascii=False)


def get_agent_path(agent_id: str) -> Path:
    return AGENTS_DIR / f"{agent_id}.json"


def load_agent(agent_id: str) -> dict | None:
    """加载单个 agent JSON"""
    path = get_agent_path(agent_id)
    if path.exists():
        with open(path) as f:
            return json.load(f)
    return None


def save_agent(agent_id: str, data: dict) -> str:
    """保存 agent JSON，返回内容字符串"""
    content = json.dumps(data, indent=2, ensure_ascii=False) + "\n"
    path = get_agent_path(agent_id)
    with open(path, "w") as f:
        f.write(content)
    return content


def list_agent_ids() -> list[str]:
    """列出所有已保存的 agent id"""
    return sorted(
        f.stem for f in AGENTS_DIR.glob("*.json")
    )


def needs_update(agent_id: str, content: str, meta: dict) -> bool:
    """检查 agent 是否需要更新"""
    entry = meta.get(agent_id)
    if entry is None:
        return True  # 新增
    if entry.get("hash") != file_hash(content):
        return True  # 内容有变化
    last_time = entry.get("last_updated", 0)
    if time.time() - last_time > UPDATE_INTERVAL:
        return True  # 超过更新间隔
    return False


# ── 更新逻辑 ────────────────────────────────────────────────────────────

def update_agent(agent_id: str, new_data: dict, force: bool = False) -> dict:
    """
    更新一个 agent 条目。
    返回状态: {"agent_id": str, "action": "created"|"updated"|"skipped", "changed": bool}
    """
    ok, errors = validate_agent(new_data)
    if not ok:
        return {"agent_id": agent_id, "action": "error", "errors": errors, "changed": False}

    new_content = json.dumps(new_data, indent=2, ensure_ascii=False) + "\n"
    meta = load_meta()

    if not force and not needs_update(agent_id, new_content, meta):
        return {"agent_id": agent_id, "action": "skipped", "changed": False}

    # 对比旧数据判断是创建还是更新
    old_data = load_agent(agent_id)
    if old_data is None:
        action = "created"
    else:
        action = "updated"

    # 写文件
    save_agent(agent_id, new_data)

    # 更新缓存
    meta[agent_id] = {
        "hash": file_hash(new_content),
        "last_updated": int(time.time()),
        "last_verified": new_data.get("last_verified", datetime.now(timezone.utc).strftime("%Y-%m-%d")),
    }
    save_meta(meta)

    return {"agent_id": agent_id, "action": action, "changed": True}


def update_all(agents: list[dict], force: bool = False) -> list[dict]:
    """批量更新 agent 列表"""
    results = []
    for data in agents:
        agent_id = data.get("id")
        if not agent_id:
            agent_id = data["name"].lower().replace(" ", "-").replace("/", "-")
            data["id"] = agent_id
        results.append(update_agent(agent_id, data, force))
    return results


# ── 状态查看 ────────────────────────────────────────────────────────────

def show_status():
    """显示所有 agent 的缓存状态"""
    meta = load_meta()
    ids = list_agent_ids()

    print(f"{'Agent ID':<25} {'状态':<10} {'最后验证':<14} {'Hash'}")
    print("-" * 80)
    for aid in ids:
        entry = meta.get(aid)
        if entry:
            status = "已缓存"
            last_v = entry.get("last_verified", "?")
            h = entry["hash"][:12]
        else:
            status = "无缓存"
            last_v = "-"
            h = "-"
        # 检查是否有新数据需要更新
        now = time.time()
        last_up = entry.get("last_updated", 0) if entry else 0
        if entry and (now - last_up > UPDATE_INTERVAL):
            status = "待更新"
        print(f"{aid:<25} {status:<10} {last_v:<14} {h}")

    # 统计
    total = len(ids)
    cached = sum(1 for a in ids if a in meta)
    pending = sum(1 for a in ids if a in meta and time.time() - meta[a].get("last_updated", 0) > UPDATE_INTERVAL)
    print(f"\n总数: {total} | 已缓存: {cached} | 待更新: {pending}")


# ── 主入口 ──────────────────────────────────────────────────────────────

def print_usage():
    print("用法:")
    print("  python hunter.py update        更新所有 agent 条目")
    print("  python hunter.py report        生成 HTML 报告")
    print("  python hunter.py run           更新 + 报告")
    print("  python hunter.py status        查看缓存状态")
    print("  python hunter.py add <file>    从 JSON 文件添加/更新 agent")



# ── 加载所有 agent ────────────────────────────────────────────────────

def load_all_agents() -> list[dict]:
    """从 agents/ 目录加载所有 agent 数据"""
    agents = []
    for fpath in sorted(AGENTS_DIR.glob("*.json")):
        with open(fpath) as f:
            agents.append(json.load(f))
    return agents


# ── LLM 调用 ──────────────────────────────────────────────────────────

def _llm_chat(messages: list[dict], temperature: float = 0.1, max_tokens: int = 4096) -> str | None:
    """调用 LLM（MiniMax M2.7）返回内容文本"""
    import requests

    cfg = CONFIG.get("llm", {})
    base_url = cfg.get("base_url", "")
    api_key = cfg.get("api_key", "")
    model = cfg.get("model", "MiniMax-M2.7")

    if not base_url or not api_key:
        warning("config.json 未配置 llm.base_url / llm.api_key")
        return None

    url = f"{base_url.rstrip('/')}/v1/messages"
    headers = {
        "X-Api-Key": api_key,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json",
    }
    body = {
        "model": model,
        "max_tokens": max_tokens,
        "temperature": temperature,
        "messages": messages,
    }

    try:
        resp = requests.post(url, headers=headers, json=body, timeout=120)
        resp.raise_for_status()
        data = resp.json()
        # Anthropic 兼容格式
        content_blocks = data.get("content", [])
        if isinstance(content_blocks, list):
            texts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
            return "\n".join(texts)
        # OpenAI 兼容格式兜底
        choices = data.get("choices", [])
        if choices:
            return choices[0].get("message", {}).get("content", "")
        return str(data)
    except Exception as e:
        warning(f"LLM 调用失败: {e}")
        return None


# ── 搜索发现 ──────────────────────────────────────────────────────────

def _search_360(query: str, limit: int = 6) -> list[dict]:
    """使用 360 搜索（免费，覆盖知乎/微信公众号/掘金等中文站点）"""
    import requests
    import re
    from urllib.parse import quote

    try:
        url = f"https://www.so.com/s?q={quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        results = []
        # 360 搜索结果结构：h3 标题 + 链接
        # 匹配 <h3><a href="...">标题</a></h3>
        pattern = r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>\s*</h3>'
        matches = re.findall(pattern, resp.text, re.DOTALL)

        for link, title_html in matches:
            # 清理标题
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            # 过滤无效链接
            if title and link and link.startswith('http'):
                results.append({
                    "url": link,
                    "title": title[:120],
                    "content": "",
                    "source": "360_search",
                })
            if len(results) >= limit:
                break

        return results
    except Exception as e:
        warning(f"360搜索失败: {e}")
        return []


def _search_duckduckgo(query: str, limit: int = 6) -> list[dict]:
    """使用 DuckDuckGo 搜索（免费，覆盖全球英文站点）"""
    try:
        from ddgs import DDGS

        results = []
        with DDGS() as ddgs:
            for r in ddgs.text(query, max_results=limit):
                results.append({
                    "url": r.get("href", ""),
                    "title": (r.get("title", "") or "")[:120],
                    "content": (r.get("body", "") or "")[:800],
                    "source": "duckduckgo",
                })
        return results
    except ImportError:
        warning("未安装 ddgs，运行: pip3 install ddgs")
        return []
    except Exception as e:
        warning(f"DuckDuckGo 搜索失败: {e}")
        return []


def _search_firecrawl(query: str, limit: int = 6) -> list[dict]:
    """使用 Firecrawl 搜索网页（需要有效 API key）"""
    import subprocess
    import json as _json

    try:
        result = subprocess.run(
            ["firecrawl", "search", query, "--scrape", "--limit", str(limit), "--json"],
            capture_output=True, text=True, timeout=30,
        )
        if result.returncode != 0:
            return []

        data = _json.loads(result.stdout)
        sources = data.get("data", {}).get("web", [])
        results = []
        for src in sources:
            url = src.get("url", "")
            title = (src.get("title", "") or "")[:120]
            content = (src.get("content", "") or src.get("description", "") or "")[:800]
            if url and title:
                results.append({"url": url, "title": title, "content": content, "source": "firecrawl"})
        return results
    except Exception:
        return []


def discover() -> list[dict]:
    """
    使用多源搜索（360搜索 + DuckDuckGo + Firecrawl）+ LLM 结构化提取，
    发现新的 AI Agent 产品。
    返回不在 agents/ 中的新 agent 列表（已补全字段）。
    """
    import json as _json

    existing_agents = load_all_agents()
    existing_ids = {a["id"] for a in existing_agents}
    existing_names = {a["name"].lower() for a in existing_agents}

    # ── 国内搜索源（360搜索覆盖知乎/微信公众号/掘金/CSDN等） ──
    DOMESTIC_SEARCHES = [
        # 知乎
        ("IDE",   "AI编程助手 IDE 编辑器 推荐 2025 site:zhihu.com"),
        ("CLI",   "AI编码工具 命令行 agent 推荐 2025 site:zhihu.com"),
        ("SDK",   "AI agent开发 框架 SDK 推荐 2025 site:zhihu.com"),
        # 微信公众号（360也能搜到）
        ("IDE",   "AI编程工具 推荐 微信公众号"),
        ("CLI",   "AI编码助手 命令行工具"),
        ("Other", "AI软件工程师 自主编程 工具"),
        # 综合中文搜索
        ("IDE",   "AI IDE编辑器 排名 对比 2025"),
        ("Plugin","AI代码补全插件 VS Code 推荐"),
        ("Other", "AI编程工具 测评 2025 2026"),
        ("TUI",   "终端 AI agent 工具 推荐"),
        ("GUI",   "AI 网页生成器 可视化 工具"),
    ]

    # ── 国外搜索源（DuckDuckGo覆盖ProductHunt/HackerNews/GitHub等） ──
    OVERSEAS_SEARCHES = [
        # 通用英文搜索
        ("IDE",   "best AI code editor IDE tool 2025"),
        ("CLI",   "AI coding agent CLI tool terminal 2025"),
        ("TUI",   "terminal AI agent TUI framework 2025"),
        ("GUI",   "AI web app generator visual builder tool 2025"),
        ("Plugin","AI coding assistant plugin VS Code JetBrains 2025"),
        ("SDK",   "AI agent SDK framework library 2025"),
        ("Other", "AI software engineer autonomous agent platform 2025"),
        # 特定类型搜索
        ("Other", "AI coding tool benchmark comparison 2025 2026"),
        ("Other", "best AI developer tools product hunt 2025"),
        ("Plugin", "AI code completion extension marketplace"),
    ]

    raw_sources = []

    # ── 执行国内搜索（360搜索） ──
    step("国内搜索源（360搜索）")
    for target_cat, query in DOMESTIC_SEARCHES:
        if CONFIG.get("search_sources", {}).get("domestic", {}).get("360_search", {}).get("enabled", True):
            sub_step(f"360: {query[:50]}...")
            sources = _search_360(query, limit=4)
            for s in sources:
                s["category_hint"] = target_cat
            raw_sources.extend(sources)

    # ── 执行国外搜索（DuckDuckGo） ──
    step("国外搜索源（DuckDuckGo）")
    for target_cat, query in OVERSEAS_SEARCHES:
        if CONFIG.get("search_sources", {}).get("overseas", {}).get("duckduckgo", {}).get("enabled", True):
            sub_step(f"DDG: {query[:50]}...")
            sources = _search_duckduckgo(query, limit=4)
            for s in sources:
                s["category_hint"] = target_cat
            raw_sources.extend(sources)

    # ── 可选：Firecrawl 补充搜索 ──
    if CONFIG.get("search_sources", {}).get("domestic", {}).get("firecrawl", {}).get("enabled", False):
        step("Firecrawl 补充搜索（国内）")
        for target_cat, query in DOMESTIC_SEARCHES[:3]:  # 只搜前3个节省额度
            sources = _search_firecrawl(query, limit=3)
            for s in sources:
                s["category_hint"] = target_cat
            raw_sources.extend(sources)

    if CONFIG.get("search_sources", {}).get("overseas", {}).get("firecrawl", {}).get("enabled", False):
        step("Firecrawl 补充搜索（国外）")
        for target_cat, query in OVERSEAS_SEARCHES[:3]:
            sources = _search_firecrawl(query, limit=3)
            for s in sources:
                s["category_hint"] = target_cat
            raw_sources.extend(sources)

    # 去重 URL
    seen_urls = set()
    unique_sources = []
    for s in raw_sources:
        if s["url"] not in seen_urls:
            seen_urls.add(s["url"])
            unique_sources.append(s)

    info(f"收集了 {len(unique_sources)} 个原始页面来源")

    if not unique_sources:
        return []

    # 分批喂给 LLM（每批最多 20 个来源）
    batch_size = 20
    new_entries = []

    for batch_start in range(0, len(unique_sources), batch_size):
        batch = unique_sources[batch_start:batch_start + batch_size]

        # 构造来源文本
        sources_text = ""
        for i, s in enumerate(batch, 1):
            sources_text += f"[{i}] {s['title']}\n    URL: {s['url']}\n    来源: {s.get('source', 'unknown')}\n    内容摘要: {s.get('content', '')[:500]}\n\n"

        system_prompt = """你是一个 AI Agent 产品分析师。你的任务是从网页搜索结果中识别 AI Agent 产品。

只提取符合以下条件的条目：
1. 是一个具体的 AI Agent 产品、工具、框架或平台（不是文章、博客、集合页面）
2. 与 AI 编程、代码生成、AI 代理相关
3. 有明确的官网或 GitHub 仓库

对每个产品输出 JSON 格式（只输出一个 JSON 数组，不要其他文字）：
```json
[
  {
    "name": "产品名称（英文原名）",
    "category": "IDE|CLI|TUI|GUI|Plugin|SDK|Other",
    "description": "一句话中文描述（30-80字）",
    "features": ["特性1", "特性2", "特性3"],
    "open_source": "yes|partial|no|unknown",
    "license": "开源许可证名称或'专有'或'未知'",
    "strengths": ["优势1", "优势2", "优势3"],
    "position": "一句话中文定位（10-30字）",
    "website": "官网URL",
    "docs_url": "文档URL（如果没有则填空字符串）",
    "github_repo": "GitHub仓库URL（如果没有则填空字符串）",
    "pricing": "定价信息（免费/付费/免费+付费/或'未知'）",
    "tags": ["标签1", "标签2"]
  }
]
```

要求：
- 只输出严格有效的 JSON 数组
- 最多输出 5 个产品（宁可少也不要错）
- 不确定的字段填空值而不是猜测
- category 必须从 IDE/CLI/TUI/GUI/Plugin/SDK/Other 中选"""

        user_prompt = f"请分析以下网页搜索结果，识别并提取 AI Agent 产品信息：\n\n{sources_text}"

        info(f"第 {batch_start//batch_size + 1} 批: {len(batch)} 个来源 → LLM 分析...")
        result_text = _llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        if not result_text:
            warning("LLM 无返回，跳过本批")
            continue

        # 提取 JSON
        try:
            # 去掉 markdown 代码块标记
            cleaned = result_text.strip()
            if "```json" in cleaned:
                cleaned = cleaned.split("```json")[1]
                if "```" in cleaned:
                    cleaned = cleaned.split("```")[0]
            elif "```" in cleaned:
                cleaned = cleaned.split("```")[1]
                if "```" in cleaned:
                    cleaned = cleaned.split("```")[0]
            cleaned = cleaned.strip()

            parsed = _json.loads(cleaned)
            if isinstance(parsed, dict):
                parsed = [parsed]

            for item in parsed:
                name = item.get("name", "").strip()
                if not name:
                    continue

                # 智能去重：精确匹配 + 子串匹配
                name_lower = name.lower()
                if name_lower in existing_names:
                    continue
                # 检查是否有已有名字包含这个新名字，或反之
                is_dup = False
                for en in existing_names:
                    if name_lower in en or en in name_lower:
                        is_dup = True
                        break
                if is_dup:
                    continue
                # 也检查 id 匹配
                aid = name.lower().replace(" ", "-").replace("/", "-").replace(".", "-").replace("(", "").replace(")", "")[:60]
                if aid in existing_ids:
                    continue

                entry = {
                    "id": aid,
                    "name": name[:80],
                    "category": item.get("category", "Other"),
                    "description": (item.get("description", "") or "")[:300],
                    "features": (item.get("features") or [])[:10],
                    "open_source": item.get("open_source", "unknown"),
                    "license": item.get("license", "未知"),
                    "strengths": (item.get("strengths") or [])[:5],
                    "position": (item.get("position", "") or "")[:100],
                    "website": item.get("website", ""),
                    "docs_url": item.get("docs_url", ""),
                    "github_repo": item.get("github_repo", ""),
                    "pricing": item.get("pricing", "未知"),
                    "tags": (item.get("tags") or [])[:8],
                    "last_verified": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                }
                new_entries.append(entry)
                existing_ids.add(aid)
                existing_names.add(name_lower)

        except (_json.JSONDecodeError, Exception) as e:
            warning(f"JSON 解析失败: {e}")
            debug(f"原始输出: {result_text[:200]}")
            continue

    if new_entries:
        success(f"LLM 发现 {len(new_entries)} 个新 agent")
        for e in new_entries:
            info(f"  ✨ {e['name']} [{e['category']}]")

    return new_entries


# ── 刷新已有 agent ────────────────────────────────────────────────────

def _build_refresh_query(agent: dict) -> str:
    """为已有 agent 构建刷新搜索查询"""
    name = agent.get("name", "")
    category = agent.get("category", "")
    website = agent.get("website", "")

    # 优先用官网域名搜索
    domain = ""
    if website:
        try:
            from urllib.parse import urlparse
            domain = urlparse(website).netloc.replace("www.", "")
        except Exception:
            pass

    if domain:
        return f"{name} AI tool update 2025 2026 site:{domain}"
    return f"{name} AI {category} update changelog 2025 2026"


def _refresh_single_agent(agent: dict, sources: list[dict]) -> dict | None:
    """用搜索结果刷新单个 agent 的信息，返回更新后的数据或 None"""
    import json as _json

    if not sources:
        return None

    # 构造来源文本
    sources_text = ""
    for i, s in enumerate(sources[:8], 1):  # 最多8个来源，给 LLM 更多参考
        sources_text += f"[{i}] {s['title']}\n    URL: {s['url']}\n    内容: {s.get('content', '')[:500]}\n\n"

    old_data = json.dumps(agent, indent=2, ensure_ascii=False)

    system_prompt = """你是一个 AI Agent 产品信息更新助手。你有某个产品的旧信息，以及最新的搜索结果。

请根据搜索结果，输出完整的更新后 JSON 对象（不是数组）。重点任务：

## 1. URL 准确性验证（最高优先级）
- **website**: 搜索结果中提到的官网地址。如果搜索结果显示旧 website 指向了错误的页面（比如指向了其他项目的 GitHub 仓库、404 页面、或与产品名不符的域名），必须用正确的 URL 替换。优先使用产品官方域名（非 GitHub 的独立域名）。
- **github_repo**: 产品实际的 GitHub 仓库地址。如果旧 github_repo 指向了错误的仓库（仓库名或组织名与产品不符），必须更正。从搜索结果中查找正确的 GitHub 链接。
- **docs_url**: 产品文档地址。如果搜索结果中有文档链接，更新它。
- 如果搜索结果明确显示某个 URL 已失效或错误，不要保留错误的旧值，用搜索到的正确值替换。如果搜索不到正确值，保留原值并标记为需人工审核（设为空字符串）。

## 2. 描述信息更新
- **description**: 根据最新搜索结果更新产品的一句话描述（30-120字中文），反映产品最新状态
- **position**: 更新产品定位描述（10-30字），反映产品当前的市场定位
- **features**: 如果发现新功能特性，添加到列表中（保持最多10个）
- **strengths**: 如果发现新的核心优势，更新（保持最多5个）
- **tags**: 根据最新信息更新标签（保持最多8个）
- **pricing/license**: 如果价格或许可证有变化，更新

## 3. 输出规则
- 输出完整的 JSON 对象，包含所有字段
- 没有变化的字段保持原值
- 不确定的字段不要猜测，保持原值
- id 字段必须保持原值不变
- 只输出严格的 JSON，不要 markdown 代码块或其他文字"""

    user_prompt = f"""旧信息：
{old_data}

最新搜索结果：
{sources_text}

请输出更新后的完整 JSON 对象。"""

    result_text = _llm_chat([
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt},
    ], temperature=0.05, max_tokens=3072)

    if not result_text:
        return None

    try:
        # 提取 JSON
        cleaned = result_text.strip()
        if "```json" in cleaned:
            cleaned = cleaned.split("```json")[1]
            if "```" in cleaned:
                cleaned = cleaned.split("```")[0]
        elif "```" in cleaned:
            cleaned = cleaned.split("```")[1]
            if "```" in cleaned:
                cleaned = cleaned.split("```")[0]
        cleaned = cleaned.strip()

        parsed = _json.loads(cleaned)
        if isinstance(parsed, list):
            parsed = parsed[0] if parsed else None

        if parsed:
            # 保留原 id
            parsed["id"] = agent["id"]
            parsed["last_verified"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
            
            # URL 后处理校验
            parsed = _sanitize_urls(parsed, agent)
            
            return parsed
        return None
    except (_json.JSONDecodeError, Exception) as e:
        warning(f"刷新 {agent.get('name', '?')} 时 JSON 解析失败: {e}")
        debug(f"原始输出: {result_text[:200]}")
        return None


def _sanitize_urls(data: dict, old_data: dict) -> dict:
    """校验和清理 URL 字段"""
    import re
    
    website = (data.get("website") or "").strip()
    github_repo = (data.get("github_repo") or "").strip()
    docs_url = (data.get("docs_url") or "").strip()
    name = data.get("name", "")
    
    # 1. 检查 website 是否仍是 GitHub URL（可能是 LLM 没找到独立官网）
    if website and "github.com" in website and github_repo and website == github_repo:
        # website 和 github_repo 完全相同且都是 GitHub 链接
        # 如果旧数据也是这样，说明确实没有独立官网
        old_website = (old_data.get("website") or "").strip()
        old_github = (old_data.get("github_repo") or "").strip()
        if old_website and "github.com" not in old_website:
            # 旧数据有独立官网但 LLM 改成了 GitHub，恢复旧官网
            data["website"] = old_website
            warning(f"  [{name}] website 被错误改为 GitHub，已恢复: {old_website}")
    
    # 2. 基本 URL 格式校验
    for field in ["website", "github_repo", "docs_url"]:
        url = (data.get(field) or "").strip()
        if url and not url.startswith("http"):
            # 尝试修复没有协议的 URL
            if "." in url:
                data[field] = "https://" + url
                warning(f"  [{name}] {field} 缺少协议，已自动补全: {data[field]}")
            else:
                # 无效 URL，清空
                data[field] = ""
                warning(f"  [{name}] {field} 格式无效，已清空: {url}")


def refresh_agents(batch_size: int = 5, max_batches: int = 3) -> dict:
    """
    刷新已有 agent 的信息。
    每次只处理 batch_size 个 agent，避免 API 调用过多。
    返回统计: {"total": int, "refreshed": int, "errors": int, "skipped": int}
    """
    import json as _json

    agents = load_all_agents()
    if not agents:
        warning("agents/ 目录为空")
        return {"total": 0, "refreshed": 0, "errors": 0, "skipped": 0}

    # 按 last_verified 排序，优先刷新最久未更新的
    agents.sort(key=lambda a: a.get("last_verified", "1970-01-01"))

    # 只处理前 batch_size * max_batches 个
    to_refresh = agents[:batch_size * max_batches]
    total = len(to_refresh)

    stats = {"total": total, "refreshed": 0, "errors": 0, "skipped": 0}

    step(f"刷新 {total} 个 agent 的信息（每批 {batch_size} 个）")

    for batch_idx in range(0, total, batch_size):
        if batch_idx // batch_size >= max_batches:
            break

        batch = to_refresh[batch_idx:batch_idx + batch_size]
        info(f"第 {batch_idx//batch_size + 1} 批: {len(batch)} 个 agent")

        for agent in batch:
            aid = agent.get("id", "?")
            name = agent.get("name", "?")

            # 构建搜索查询
            query = _build_refresh_query(agent)
            sub_step(f"[{aid}] {name}")
            debug(f"  搜索: {query}")

            # 搜索（360 + DuckDuckGo）
            sources = []
            if CONFIG.get("search_sources", {}).get("domestic", {}).get("360_search", {}).get("enabled", True):
                sources.extend(_search_360(query, limit=3))
            if CONFIG.get("search_sources", {}).get("overseas", {}).get("duckduckgo", {}).get("enabled", True):
                sources.extend(_search_duckduckgo(query, limit=3))

            if not sources:
                warning(f"  [{aid}] 无搜索结果，跳过")
                stats["skipped"] += 1
                continue

            # 刷新信息
            updated = _refresh_single_agent(agent, sources)
            if updated:
                # 对比是否有实际变化
                old_json = json.dumps(agent, sort_keys=True, ensure_ascii=False)
                new_json = json.dumps(updated, sort_keys=True, ensure_ascii=False)
                if old_json != new_json:
                    # 有变化，保存
                    result = update_agent(aid, updated, force=True)
                    if result["action"] in ("created", "updated"):
                        success(f"  [{aid}] 已更新")
                        stats["refreshed"] += 1
                    else:
                        stats["skipped"] += 1
                else:
                    # 无变化，只更新 last_verified
                    agent["last_verified"] = datetime.now(timezone.utc).strftime("%Y-%m-%d")
                    save_agent(aid, agent)
                    meta = load_meta()
                    meta[aid] = {
                        "hash": file_hash(json.dumps(agent, indent=2, ensure_ascii=False) + "\n"),
                        "last_updated": int(time.time()),
                        "last_verified": agent["last_verified"],
                    }
                    save_meta(meta)
                    info(f"  [{aid}] 无变化")
                    stats["skipped"] += 1
            else:
                warning(f"  [{aid}] 刷新失败")
                stats["errors"] += 1

    success(f"刷新完成: 总计 {stats['total']} | 更新 {stats['refreshed']} | 跳过 {stats['skipped']} | 错误 {stats['errors']}")
    return stats

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print_usage()
        sys.exit(1)

    command = sys.argv[1]

    if command == "status":
        show_status()
    elif command == "report":
        from report_gen import generate_report
        generate_report()
    elif command == "update":
        info("请通过 load_agents() 传入 agent 数据后调用 update_all()")
        info("或使用 'python hunter.py run'")
    elif command == "run":
        info("请通过主入口传入 agent 列表")
    elif command == "add" and len(sys.argv) >= 3:
        filepath = sys.argv[2]
        with open(filepath) as f:
            data = json.load(f)
        if isinstance(data, list):
            results = update_all(data)
        else:
            results = [update_agent(data.get("id", data["name"].lower().replace(" ", "-")), data)]
        for r in results:
            action = r["action"]
            aid = r["agent_id"]
            if action == "error":
                error(f"{aid}: 验证失败 - {r['errors']}")
            else:
                success(f"{aid}: {action}") if action != "skipped" else info(f"{aid}: {action}")
    else:
        print_usage()
        sys.exit(1)
