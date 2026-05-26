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
import re  # JSON 修复用
import hashlib
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

from logger import info, success, warning, error, debug, step, sub_step


# ── JSON 修复函数 ────────────────────────────────────────────────────────

def _fix_json_string(text: str) -> str:
    """尝试修复 LLM 返回的有语法错误的 JSON"""
    if not text:
        return text

    # 修复常见的 JSON 语法错误
    import re

    # 1. 修复缺少引号包裹的字符串键（"key": 变成 key": ）
    # 匹配不带引号的键后跟冒号: key": -> "key":
    text = re.sub(r'(\w+)":', r'"\1":', text)

    # 2. 修复键值对之间缺少逗号 ("} " 变成 ", ")
    text = re.sub(r'("])(\s+)(")', r'\1,\2\3', text)

    # 3. 移除尾随逗号 (如 [1,2,3,] -> [1,2,3])
    text = re.sub(r',(\s*[}\]])', r'\1', text)

    # 4. 修复单引号替换为双引号
    text = re.sub(r"'([^']*)'", r'"\1"', text)

    # 5. 修复没有引号的字符串值
    # 匹配 : 后面跟着字母数字开头的值（非 [ { " 开头）
    text = re.sub(r':\s*([a-zA-Z][a-zA-Z0-9_]*)', r': "\1"', text)

    return text


def _safe_json_parse(text: str):
    """安全解析 JSON，失败时尝试修复后再次解析"""
    import json as _json

    # 第一次尝试直接解析
    try:
        return _json.loads(text)
    except _json.JSONDecodeError:
        pass

    # 第二次尝试修复后解析
    fixed = _fix_json_string(text)
    try:
        return _json.loads(fixed)
    except _json.JSONDecodeError:
        pass

    # 第三次尝试：提取 JSON 数组部分
    match = re.search(r'\[.*\]', text, re.DOTALL)
    if match:
        try:
            return _json.loads(match.group(0))
        except _json.JSONDecodeError:
            pass

    # 第四次尝试：修复后再次提取数组
    fixed_match = re.search(r'\[.*\]', fixed, re.DOTALL)
    if fixed_match:
        try:
            return _json.loads(fixed_match.group(0))
        except _json.JSONDecodeError:
            pass

    # 所有尝试都失败，抛出原始异常
    raise _json.JSONDecodeError("无法解析 JSON", text, 0)


# ── 路径与配置 ──────────────────────────────────────────────────────────

BASE_DIR = Path(__file__).parent
CONFIG_FILE = BASE_DIR / "config.json"

with open(CONFIG_FILE) as f:
    CONFIG = json.load(f)

AGENTS_DIR = BASE_DIR / CONFIG["agents_dir"]
CACHE_DIR = BASE_DIR / CONFIG["cache_dir"]
META_FILE = BASE_DIR / CONFIG["meta_file"]
UPDATE_INTERVAL = CONFIG["update_interval_hours"] * 3600

AGENTS_DIR.mkdir(parents=True, exist_ok=True)
CACHE_DIR.mkdir(parents=True, exist_ok=True)

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
    """调用 LLM，添加完善的错误处理和重试逻辑"""
    import os
    import requests
    from requests.exceptions import ConnectionError, Timeout, ReadTimeout, ProxyError
    import time

    cfg = CONFIG.get("llm", {})
    # 优先使用环境变量，其次使用 config.json
    import os as _os
    base_url = _os.environ.get("LLM_BASE_URL") or cfg.get("base_url", "")
    api_key = _os.environ.get("LLM_API_KEY") or cfg.get("api_key", "")
    model = cfg.get("model", "MiniMax-M2.7")

    if not base_url or not api_key:
        warning("未配置 LLM（环境变量或 config.json）")
        return None

    # 检查 LLM 不可用标记（401 后写入）- 改为立即重试
    flag_file = os.path.join(os.path.dirname(os.path.abspath(__file__)), "cache", "llm_unavailable.flag")
    if os.path.exists(flag_file):
        # 移除此检查，改为每次都重试（已切换到新的 API）
        os.remove(flag_file)
        info("LLM 不可用标记已清除，重试调用")

    # 检测 API 格式：OpenAI 兼容用 /chat/completions，Anthropic 用 /messages
    base = base_url.rstrip("/")
    if "/anthropic" in base or "/v1/messages" in base:
        # Anthropic 兼容格式
        url = f"{base}/v1/messages"
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
    else:
        # OpenAI 兼容格式（scnet 等）
        url = f"{base}/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "content-type": "application/json",
        }
        body = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }

    # 增强重试逻辑：区分错误类型，差异化处理
    max_retries = 3  # 增加到 3 次重试
    retry_codes = {429, 500, 502, 503, 504}  # 可重试的 HTTP 状态码
    
    for attempt in range(max_retries + 1):
        resp = None
        try:
            info(f"LLM 调用尝试 {attempt + 1}/{max_retries + 1}...")
            # 使用分离的连接超时和读取超时
            resp = requests.post(
                url, headers=headers, json=body,
                timeout=(10, 120),  # (connect_timeout, read_timeout) - 增加超时到 120s
                allow_redirects=True
            )
            info(f"  -> resp.status_code={resp.status_code}, resp.text[:100]={resp.text[:100]}")
            
            # 401 认证失败：标记并退出
            if resp.status_code == 401:
                warning(f"LLM API 认证失败 (401)，标记为不可用 6 小时")
                os.makedirs(os.path.dirname(flag_file), exist_ok=True)
                with open(flag_file, "w") as f:
                    f.write(f"401 at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                return None

            resp.raise_for_status()
            info("  -> 解析 JSON...")
            data = resp.json()
            info(f"  -> data.keys={list(data.keys()) if isinstance(data, dict) else type(data)}")
            
            # Anthropic 兼容格式（仅当 content_blocks 有实际内容时使用）
            content_blocks = data.get("content", [])
            if isinstance(content_blocks, list) and content_blocks:
                texts = [b.get("text", "") for b in content_blocks if b.get("type") == "text"]
                if texts:
                    info(f"  -> Anthropic 路径: texts={texts[:2]}")
                    return "\n".join(texts)
            # OpenAI 兼容格式
            info(f"  -> 尝试 OpenAI 格式...")
            # OpenAI 兼容格式
            choices = data.get("choices", [])
            if choices:
                msg_content = choices[0].get("message", {}).get("content", "")
                finish_reason = choices[0].get("finish_reason", "")
                # 调试：记录返回内容长度和 finish_reason
                info(f"LLM 返回: content_len={len(msg_content) if msg_content else 0}, finish_reason={finish_reason}")
                if msg_content:
                    return msg_content
                # content 为空，检查是否有 reasoning_content
                reasoning = choices[0].get("message", {}).get("reasoning_content", "")
                if reasoning:
                    warning("LLM 返回了 reasoning 但无 content，尝试使用 reasoning")
                    return reasoning
                warning(f"LLM content 为空，响应数据: {data.get('usage', {})}")
                return ""
            warning(f"LLM choices 为空: {data}")
            return str(data)

        except requests.Timeout as e:
            warning(f"LLM 请求超时: {e}")
            if attempt < max_retries:
                wait = 2 ** attempt  # 指数退避: 1s, 2s, 4s
                warning(f"{wait}s 后重试...")
                time.sleep(wait)
                continue
            return None
        except ProxyError as e:
            # 代理错误重试
            warning(f"LLM 代理错误: {e}")
            if attempt < max_retries:
                wait = 2 ** attempt
                warning(f"{wait}s 后重试...")
                time.sleep(wait)
                continue
            warning(f"LLM 调用失败（代理错误）: {e}")
            return None
        except ConnectionError as e:
            # 连接错误重试
            warning(f"LLM 连接错误: {e}")
            if attempt < max_retries:
                wait = 2 ** attempt
                warning(f"{wait}s 后重试...")
                time.sleep(wait)
                continue
            warning(f"LLM 调用失败（连接错误）: {e}")
            return None
        except requests.exceptions.HTTPError as e:
            warning(f"LLM HTTP错误: {e}, status={resp.status_code if resp else 'N/A'}")
            if resp and resp.status_code == 401:
                # 401 在重试块里再处理一次
                warning(f"LLM API 认证失败 (401)，标记为不可用 6 小时")
                os.makedirs(os.path.dirname(flag_file), exist_ok=True)
                with open(flag_file, "w") as f:
                    f.write(f"401 at {time.strftime('%Y-%m-%d %H:%M:%S')}")
                return None
            # 429 或 5xx 错误：指数退避重试
            if resp and resp.status_code in retry_codes:
                if attempt < max_retries:
                    wait = 2 ** attempt * 2  # 429/5xx 需要更长等待: 2s, 4s, 8s
                    if resp.status_code == 429:
                        # 尝试从响应头获取重试时间
                        retry_after = resp.headers.get("Retry-After")
                        if retry_after and retry_after.isdigit():
                            wait = int(retry_after)
                    warning(f"LLM 服务错误 ({resp.status_code})，{wait}s 后重试...")
                    time.sleep(wait)
                    continue
            # 其他 HTTP 错误重试
            if attempt < max_retries:
                wait = 2 ** attempt
                warning(f"LLM 调用失败 ({e})，{wait}s 后重试...")
                time.sleep(wait)
                continue
            warning(f"LLM 调用失败: {e}")
            return None
        except Exception as e:
            warning(f"LLM 未知错误: {type(e).__name__}: {e}")
            if attempt < max_retries:
                wait = 2 ** attempt
                warning(f"{wait}s 后重试...")
                time.sleep(wait)
                continue
            warning(f"LLM 调用失败: {e}")
            return None

    warning("LLM 重试次数耗尽")
    return None


# ── 搜索发现 ──────────────────────────────────────────────────────────

def _verify_agent_entry(entry: dict, timeout: int = 5) -> dict | None:
    """
    验证 entry 的 website 和 github_repo 是否真实可访问。
    同时检查 LLM 提供的 _source_evidence 是否包含"无法确认真实性"标记。
    返回更新后的 entry，或 None 表示不可信应丢弃。
    """
    import requests
    from urllib.parse import urlparse

    website = entry.get("website", "")
    github_repo = entry.get("github_repo", "")
    source_evidence = entry.get("_source_evidence", "")

    # 标记无法确认真实性的条目直接过滤
    if "无法确认真实性" in source_evidence or "可信度低" in source_evidence:
        warning(f"  ⚠️  {entry.get('name', '?')} 可信度低，过滤")
        return None

    verified_website = False
    verified_github = False

    headers = {"User-Agent": "Mozilla/5.0 (compatible; agent-hunter/1.0)"}

    # 验证 website
    if website:
        try:
            r = requests.head(website, timeout=timeout, headers=headers, allow_redirects=True)
            if r.status_code < 400:
                verified_website = True
            else:
                # 试试 GET（有些服务器对 HEAD 返回 405）
                try:
                    r2 = requests.get(website, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
                    if r2.status_code < 400:
                        verified_website = True
                except Exception:
                    pass
        except requests.exceptions.ConnectionError:
            # 网络层拒绝连接（被墙/超时/DNS失败）— 不归咎于 URL 本身，保留条目
            verified_website = True
        except requests.exceptions.Timeout:
            # 连接超时 — 环境网络问题，不归咎于 URL，保留条目
            verified_website = True
        except Exception:
            pass

    # 验证 github_repo
    if github_repo and "github.com" in github_repo:
        try:
            r = requests.head(github_repo, timeout=timeout, headers=headers, allow_redirects=True)
            if r.status_code < 400:
                verified_github = True
            else:
                try:
                    r2 = requests.get(github_repo, timeout=timeout, headers=headers, allow_redirects=True, stream=True)
                    if r2.status_code < 400:
                        verified_github = True
                except Exception:
                    pass
        except requests.exceptions.ConnectionError:
            # 网络层拒绝连接 — 环境问题，保留条目
            verified_github = True
        except requests.exceptions.Timeout:
            # 连接超时 — 环境问题，保留条目
            verified_github = True
        except Exception:
            pass

    # 至少有一个 URL 可验证才保留
    if not verified_website and not verified_github:
        warning(f"  ⚠️  {entry.get('name', '?')} website/github 均无法访问，过滤")
        return None

    # 清理内部字段后返回
    entry["verified_website"] = verified_website
    entry["verified_github"] = verified_github
    entry.pop("_source_evidence", None)
    return entry

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


def _search_sogou(query: str, limit: int = 6) -> list[dict]:
    """使用搜狗搜索（360 被反爬时的备用中文搜索源）"""
    import requests
    import re
    from urllib.parse import quote

    try:
        url = f"https://www.sogou.com/web?query={quote(query)}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9",
            "Accept-Encoding": "gzip, deflate",
            "Referer": "https://www.sogou.com/",
        }
        resp = requests.get(url, headers=headers, timeout=15)
        resp.raise_for_status()

        results = []
        # 搜狗搜索结果：/link?url=... 重定向
        # 需要解析真实的跳转 URL
        pattern = r'<h3[^>]*>\s*<a[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        matches = re.findall(pattern, resp.text, re.DOTALL)

        for link, title_html in matches:
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            # 处理搜狗重定向链接
            if title and '/link?url=' in link:
                # 提取真实 URL（从重定向参数）
                real_url_match = re.search(r'url=([^&]+)', link)
                if real_url_match:
                    import base64
                    encoded_url = real_url_match.group(1)
                    try:
                        # Base64 解码
                        real_url = base64.b64decode(encoded_url).decode('utf-8')
                        link = real_url
                    except:
                        # 解码失败，跳过
                        continue
            if title and (link.startswith('http') or link.startswith('//')):
                if link.startswith('//'):
                    link = 'https:' + link
                results.append({
                    "url": link,
                    "title": title[:120],
                    "content": "",
                    "source": "sogou_search",
                })
            if len(results) >= limit:
                break

        return results
    except Exception as e:
        warning(f"搜狗搜索失败: {e}")
        return []


def _search_duckduckgo(query: str, limit: int = 6) -> list[dict]:
    """使用 DuckDuckGo 搜索（免费，覆盖全球英文站点）"""
    import requests

    try:
        url = "https://html.duckduckgo.com/html/"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml",
        }
        params = {"q": query}
        resp = requests.get(url, headers=headers, params=params, timeout=15)
        resp.raise_for_status()

        results = []
        # 解析 DuckDuckGo HTML 结果
        import re
        # 匹配 <a class="result__a" href="...">Title</a> 和后面的 <a class="result__snippet" href="...">snippet</a>
        pattern = r'<a class="result__a"[^>]*href="([^"]+)"[^>]*>(.*?)</a>'
        snippet_pattern = r'<a class="result__snippet"[^>]*>(.*?)</a>'

        matches = re.findall(pattern, resp.text, re.DOTALL)
        snippets = re.findall(snippet_pattern, resp.text, re.DOTALL)

        for i, (link, title_html) in enumerate(matches[:limit]):
            title = re.sub(r'<[^>]+>', '', title_html).strip()
            snippet = ""
            if i < len(snippets):
                s = re.sub(r'<[^>]+>', '', snippets[i]).strip()
                snippet = s[:800] if s else ""
            if title and link and link.startswith('http'):
                results.append({
                    "url": link,
                    "title": title[:120],
                    "content": snippet,
                    "source": "duckduckgo",
                })
        return results
    except Exception as e:
        warning(f"DuckDuckGo 搜索失败: {e}")
        return []


def _search_hn_algolia(query: str, limit: int = 5) -> list[dict]:
    """使用 Hacker News Algolia API 搜索（免费，无需 API key）"""
    import requests
    import re

    try:
        url = f"https://hn.algolia.com/api/v1/search"
        params = {
            "query": query,
            "tags": "story",
            "hitsPerPage": limit,
        }
        resp = requests.get(url, params=params, timeout=15)
        resp.raise_for_status()
        data = resp.json()

        results = []
        for hit in data.get("hits", []):
            story_url = hit.get("url", "")
            title = hit.get("title", "") or ""
            author = hit.get("author", "")
            points = hit.get("points", 0)
            num_comments = hit.get("num_comments", 0)

            # HN stories 有时无 url（纯文字帖），跳过
            if not story_url or not title:
                continue

            # 清理标题
            title = re.sub(r'<[^>]+>', '', title).strip()

            # 构造 meta 描述
            meta = f"{points} points | {num_comments} comments | by {author}"

            results.append({
                "url": story_url,
                "title": title[:120],
                "content": meta,
                "source": "hn_algolia",
            })

        return results
    except Exception as e:
        warning(f"HN Algolia 搜索失败: {e}")
        return []


def _search_firecrawl(query: str, limit: int = 6) -> list[dict]:
    """使用 Firecrawl 搜索网页（需要有效 API key）"""
    import subprocess
    import json as _json

    firecrawl_cmd = str(Path.home() / ".hermes/node/bin/firecrawl")
    try:
        result = subprocess.run(
            [firecrawl_cmd, "search", query, "--scrape", "--limit", str(limit), "--json", "-o", "/tmp/firecrawl_search.json"],
            capture_output=True, text=True, timeout=8,
        )
        if result.returncode != 0 or not Path("/tmp/firecrawl_search.json").exists():
            return []

        with open("/tmp/firecrawl_search.json") as f:
            data = _json.load(f)

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
        # 新增：更多发现路径
        ("IDE",   "Cursor 替代 工具 2025"),
        ("Plugin","AI代码审查 工具 推荐"),
        ("Other", "AI 编程 开源 工具 2025"),
        ("SDK",   "AI agent 框架 推荐 2025"),
        ("Other", "Claude Code 替代 工具"),
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
        # 新增：更多发现路径
        ("IDE",   "Cursor alternative AI code editor 2025"),
        ("Plugin", "AI code review tool GitHub 2025"),
        ("CLI",   "open source AI coding assistant CLI 2025"),
        ("Other", "AI programmer assistant tool 2025"),
        ("SDK",   "multi-agent AI framework library 2025"),
        # 品牌/竞品专项搜索（防止遗漏知名产品）
        ("CLI",   "Claude Code alternative CLI coding agent"),
        ("CLI",   "DeepSeek coding agent terminal TUI"),
        ("IDE",   "Cursor替代 AI代码编辑器 2025 2026"),
        ("CLI",   "Aider alternative AI coding CLI"),
        ("TUI",   "open source terminal AI agent 2025 2026"),
        ("Plugin", "GitHub Copilot alternative VS Code extension"),
        ("SDK",   "AI agent framework LangChain AutoGen alternative"),
        ("GUI",   "bolt.new alternative web app generator"),
    ]

    raw_sources = []

    # ── 执行国内搜索 ──
    # 优先使用 firecrawl（如果有效），备选 360
    domestic_fc = CONFIG.get("search_sources", {}).get("domestic", {}).get("firecrawl", {}).get("enabled", False) == True
    domestic_360 = CONFIG.get("search_sources", {}).get("domestic", {}).get("360_search", {}).get("enabled", False) == True

    if domestic_fc:
        step("国内搜索源（Firecrawl）")
        for target_cat, query in DOMESTIC_SEARCHES:
            sub_step(f"Firecrawl: {query[:50]}...")
            sources = _search_firecrawl(query, limit=4)
            for s in sources:
                s["category_hint"] = target_cat
            raw_sources.extend(sources)
        # 如果 firecrawl 无结果，自动启用 360 备用，360 失败则使用 sogou
        domestic_count = sum(1 for s in raw_sources if s.get("source") == "firecrawl")
        if domestic_count == 0 and domestic_360:
            warning("Firecrawl 无结果，启用 360 备用...")
            for target_cat, query in DOMESTIC_SEARCHES:
                sub_step(f"360(fallback): {query[:50]}...")
                sources = _search_360(query, limit=4)
                # 360 无结果时尝试 sogou
                if not sources and CONFIG.get("search_sources", {}).get("domestic", {}).get("sogou_search", {}).get("enabled", False):
                    sub_step(f"搜狗备用: {query[:40]}...")
                    sources = _search_sogou(query, limit=4)
                for s in sources:
                    s["category_hint"] = target_cat
                raw_sources.extend(sources)
    elif domestic_360:
        step("国内搜索源（360+搜狗）")
        for target_cat, query in DOMESTIC_SEARCHES:
            sub_step(f"360: {query[:50]}...")
            sources = _search_360(query, limit=4)
            # 360 无结果时尝试 sogou
            if not sources and CONFIG.get("search_sources", {}).get("domestic", {}).get("sogou_search", {}).get("enabled", False):
                sub_step(f"搜狗: {query[:40]}...")
                sources = _search_sogou(query, limit=4)
            for s in sources:
                s["category_hint"] = target_cat
            raw_sources.extend(sources)

    # ── 执行国外搜索 ──
    # 优先使用 firecrawl（如果有效），备选 HN Algolia（DuckDuckGo 在 WSL 下常超时不可靠）
    overseas_fc = CONFIG.get("search_sources", {}).get("overseas", {}).get("firecrawl", {}).get("enabled", False) == True
    overseas_hn = True  # HN Algolia 可靠免费，直接启用

    if overseas_fc:
        step("国外搜索源（Firecrawl）")
        for target_cat, query in OVERSEAS_SEARCHES:
            sub_step(f"Firecrawl: {query[:50]}...")
            sources = _search_firecrawl(query, limit=4)
            for s in sources:
                s["category_hint"] = target_cat
            raw_sources.extend(sources)
        # firecrawl 无结果时补充 HN Algolia
        overseas_count = sum(1 for s in raw_sources if s.get("source") == "firecrawl")
        if overseas_count == 0:
            warning("Firecrawl 无结果，补充 HN Algolia...")
            for target_cat, query in OVERSEAS_SEARCHES:
                sub_step(f"HN Algolia: {query[:50]}...")
                sources = _search_hn_algolia(query, limit=4)
                for s in sources:
                    s["category_hint"] = target_cat
                raw_sources.extend(sources)
    else:
        # 默认使用 HN Algolia（DuckDuckGo 在 WSL 下常超时，直接跳过）
        step("国外搜索源（HN Algolia）")
        for target_cat, query in OVERSEAS_SEARCHES:
            sub_step(f"HN Algolia: {query[:50]}...")
            sources = _search_hn_algolia(query, limit=4)
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

        system_prompt = """你是一个 AI Agent 产品分析师。你的任务是从网页搜索结果中识别 AI Agent 产品，并严格验证其真实性。

只提取符合以下条件的条目：
1. 是一个具体的 AI Agent 产品、工具、框架或平台（不是文章、博客、集合页面）
2. 与 AI 编程、代码生成、AI 代理相关
3. 有明确的官网或 GitHub 仓库（必须可访问，不能是猜测或编造的 URL）

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
    "website": "官网URL（必须是真实的、可访问的 URL，不允许留空或编造）",
    "docs_url": "文档URL（如果没有则填空字符串）",
    "github_repo": "GitHub仓库URL（如果没有则填空字符串）",
    "pricing": "定价信息（免费/付费/免费+付费/或'未知'）",
    "tags": ["标签1", "标签2"],
    "_source_evidence": "从哪个搜索结果推导出来的，简单说明"
  }
]
```

验证规则（必须满足）：
- website 必须是真实可访问的 URL，不允许是 deepseek.com 这类通用官网（必须是具体项目页）
- github_repo 必须是真实的 GitHub 仓库 URL，不允许留空但声称 open_source=yes
- 如果某产品找不到真实可验证的项目页，必须在 _source_evidence 中写明"无法确认真实性，可信度低"
- 如果无法从搜索摘要中确认 product name / website / github_repo 任何一项，丢弃该条目，不要输出

要求：
- 只输出严格有效的 JSON 数组
- 最多输出 5 个产品（宁可少也不要错）
- 不确定的字段填空值而不是猜测
- category 必须从 IDE/CLI/TUI/GUI/Plugin/SDK/Other 中选"""

        user_prompt = f"请分析以下网页搜索结果，识别并提取 AI Agent 产品信息：\n\n{sources_text}"

        info( f"第 {batch_start//batch_size + 1} 批: {len(batch)} 个来源 → LLM 分析...")
        result_text = _llm_chat([
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ])

        if not result_text:
            warning("LLM 无返回，跳过本批")
            continue

        # 调试：打印 LLM 返回内容的前 500 字符
        debug(f"LLM 返回原始内容 (前500字符): {result_text[:500]}")

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

            # 使用安全的 JSON 解析（自动修复语法错误）
            parsed = _safe_json_parse(cleaned)
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
                # 验证真实性和可访问性
                verified = _verify_agent_entry(entry)
                if verified is None:
                    continue
                new_entries.append(verified)
                existing_ids.add(aid)
                existing_names.add(name_lower)

        except (_json.JSONDecodeError, Exception) as e:
            warning(f"JSON 解析失败: {e}")
            debug(f"原始输出: {result_text[:200]}")
            continue

    if new_entries:
        success(f"LLM 验证通过 {len(new_entries)} 个新 agent")
        for e in new_entries:
            vw = "✓web" if e.get("verified_website") else ""
            vg = "✓gh" if e.get("verified_github") else ""
            info(f"  ✨ {e['name']} [{e['category']}] {vw} {vg}")

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

        # 使用安全的 JSON 解析（自动修复语法错误）
        parsed = _safe_json_parse(cleaned)
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

            # 搜索（firecrawl 优先，备选 360 + DDG）
            sources = []
            domestic_fc = CONFIG.get("search_sources", {}).get("domestic", {}).get("firecrawl", {}).get("enabled", False) == True
            overseas_fc = CONFIG.get("search_sources", {}).get("overseas", {}).get("firecrawl", {}).get("enabled", False) == True

            if domestic_fc:
                sources.extend(_search_firecrawl(query, limit=3))
            if overseas_fc:
                sources.extend(_search_firecrawl(query, limit=3))

            # 如果 firecrawl 无结果，启用备用源
            if not sources:
                if CONFIG.get("search_sources", {}).get("domestic", {}).get("360_search", {}).get("enabled", False) == True:
                    sources.extend(_search_360(query, limit=3))
                    # 360 无结果时使用 sogou 备用
                    if not sources and CONFIG.get("search_sources", {}).get("domestic", {}).get("sogou_search", {}).get("enabled", False):
                        sources.extend(_search_sogou(query, limit=3))
                if CONFIG.get("search_sources", {}).get("overseas", {}).get("duckduckgo", {}).get("enabled", False) == True:
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
