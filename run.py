#!/usr/bin/env python3
"""
agent-hunter 主入口 — 发现、更新和报告 AI Agent 产品。

设计:
  - agents/ 目录是唯一权威数据源（每个 agent 一个 JSON）
  - 搜索发现 → 自动 merge 新 agent → 更新 hash 缓存
  - WebUI (webui.py) 是唯一前端界面

用法:
  python run.py               搜索发现 + 更新（默认）
  python run.py update        仅增量更新（不从外面搜索）
  python run.py discover      仅搜索发现新 agent
  python run.py news          生成每日资讯数据 (cache/news.json)
  python run.py force         强制全部更新
  python run.py status        查看缓存状态
  python run.py list          列出所有 agent
"""

import json
import sys
from pathlib import Path

BASE_DIR = Path(__file__).parent
sys.path.insert(0, str(BASE_DIR))

from hunter import (
    update_all,
    update_agent,
    load_meta,
    list_agent_ids,
    load_agent,
    load_all_agents,
    discover,
    refresh_agents,
)
from news import generate_news_data
from logger import info, success, warning, error, step


def run_discover():
    """搜索发现新 agent，自动 merge 到 agents/ 目录"""
    step("搜索发现新 AI Agent 产品")
    new_agents = discover()

    if not new_agents:
        info("没有发现新 agent")
        return []

    info(f"合并 {len(new_agents)} 个新 agent...")
    results = update_all(new_agents, force=True)
    created = sum(1 for r in results if r["action"] == "created")
    errors = [r for r in results if r["action"] == "error"]
    success(f"新增: {created}")
    if errors:
        for e in errors:
            error(f"{e['agent_id']}: {e['errors']}")

    return new_agents


def run_update(force: bool = False):
    """从 agents/ 目录读取所有 agent 并更新缓存"""
    agents = load_all_agents()
    if not agents:
        warning("agents/ 目录为空，没有数据可更新")
        return

    action_type = "强制" if force else "增量"
    step(f"{action_type}更新 {len(agents)} 个 agent 条目")
    results = update_all(agents, force=force)
    created = sum(1 for r in results if r["action"] == "created")
    updated = sum(1 for r in results if r["action"] == "updated")
    skipped = sum(1 for r in results if r["action"] == "skipped")
    errors = [r for r in results if r["action"] == "error"]

    success(f"新增: {created}")
    info(f"更新: {updated}")
    info(f"跳过: {skipped}")
    if errors:
        for e in errors:
            error(f"{e['agent_id']}: {e['errors']}")


def run_list():
    """列出所有已知 agent"""
    ids = list_agent_ids()
    meta = load_meta()
    for aid in ids:
        agent = load_agent(aid)
        if agent:
            entry = meta.get(aid, {})
            status = "缓存" if entry else "未缓存"
            info(f"  {aid:<30} [{agent.get('category', '?'):<8}] {agent['name']:<25} {status}")
    info(f"\n共 {len(ids)} 个 agent")


def run_refresh(batch_size: int = 5, max_batches: int = 3):
    """刷新已有 agent 的信息"""
    stats = refresh_agents(batch_size=batch_size, max_batches=max_batches)
    return stats


if __name__ == "__main__":
    if len(sys.argv) < 2:
        # 默认: 搜索发现 → 刷新 → 更新
        run_discover()
        run_refresh(batch_size=5, max_batches=2)
        run_update()
    else:
        command = sys.argv[1]
        if command == "update":
            force = "--force" in sys.argv or "-f" in sys.argv
            run_update(force=force)
        elif command == "discover":
            run_discover()
        elif command == "status":
            from hunter import show_status
            show_status()
        elif command == "force":
            run_discover()
            run_update(force=True)
        elif command == "add":
            if len(sys.argv) < 3:
                error("用法: python run.py add <file>")
                sys.exit(1)
            with open(sys.argv[2]) as f:
                data = json.load(f)
            if isinstance(data, list):
                results = update_all(data)
            else:
                results = update_all([data])
            for r in results:
                info(f"{r['action']}: {r['agent_id']}")
        elif command == "list":
            run_list()
        elif command == "refresh":
            batch = int(sys.argv[2]) if len(sys.argv) > 2 else 5
            batches = int(sys.argv[3]) if len(sys.argv) > 3 else 3
            run_refresh(batch_size=batch, max_batches=batches)
        elif command == "news":
            generate_news_data()
        else:
            error(f"未知命令: {command}")
            info("支持: update, discover, status, add, list, refresh, force (空=全部)")
