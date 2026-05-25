#!/usr/bin/env python3
"""Quick diagnostic for agent-hunter iteration"""

import json
import subprocess
import sys
from pathlib import Path

BASE = Path("/home/xiowen/agent-hunter")

# Step 0: Check last run status
state_file = Path("/home/xiowen/.hermes/scripts/agent-evolution-state.json")
with open(state_file) as f:
    state = json.load(f)

print(f"=== Step 0: Last Run Status ===")
print(f"iteration_count: {state.get('iteration_count')}")
print(f"last_run: {state.get('last_run')}")
print(f"done_categories: {len(state.get('done_categories', []))}")
print()

# Step 1: Check firecrawl status
config_file = BASE / "config.json"
with open(config_file) as f:
    config = json.load(f)

print(f"=== Step 1: Search Source Status ===")
firecrawl_domestic = config.get("search_sources", {}).get("domestic", {}).get("firecrawl", {})
firecrawl_overseas = config.get("search_sources", {}).get("overseas", {}).get("firecrawl", {})
print(f"firecrawl domestic: enabled={firecrawl_domestic.get('enabled')}")
print(f"firecrawl overseas: enabled={firecrawl_overseas.get('enabled')}")
print(f"360_search: {config.get('search_sources', {}).get('domestic', {}).get('360_search', {}).get('enabled')}")
print(f"duckduckgo: {config.get('search_sources', {}).get('overseas', {}).get('duckduckgo', {}).get('enabled')}")
print()

# Step 2: Count agents
agents_dir = BASE / "agents"
agent_files = list(agents_dir.glob("*.json"))
print(f"=== Step 2: Agent Count ===")
print(f"Total agent files: {len(agent_files)}")
print()

# Step 3: Choose optimization direction
print(f"=== Step 3: Optimization Direction ===")
# Based on iteration log, most things are done. Let me check what's remaining.
# From the last iteration log entry:
# - docs_url for 14 agents is missing
# - firecrawl still disabled
# - TOP5 ranking was added to report already
# - WebUI has search, filters, sorting
# Let's look for one concrete improvement we can do:
# Check if there are agents with incomplete data that we can complete

# Count missing docs_url
missing_docs = []
for f in agent_files:
    with open(f) as fp:
        agent = json.load(fp)
    if not agent.get("docs_url"):
        missing_docs.append(f.stem)

print(f"Agents missing docs_url: {len(missing_docs)}")
if missing_docs:
    print(f"  Examples: {missing_docs[:5]}")

# Check WebUI for quick win - check if there's a "sort by" improvement we can do
webui_file = BASE / "webui.py"
with open(webui_file) as f:
    webui_content = f.read()

# Count sorting options
sort_lines = [l for l in webui_content.split('\n') if 'sort by' in l.lower() or '排序' in l]
print(f"WebUI sort-related lines: {len(sort_lines)}")

# Check report_gen for any quick improvements
report_file = BASE / "report_gen.py"
with open(report_file) as f:
    report_content = f.read()

print(f"report_gen.py lines: {len(report_content.split(chr(10)))}")

# Determine what to do
# Based on the iteration log, recent work was:
# - Added GitHub count card to report stats
# - Fixed license to English Unknown
# - WebUI sort/filter improvements
# - TOP5 ranking in report
# - LLM retry logic improvements
# 
# Next logical improvement: data completeness - adding docs_url for agents that have it
# Or: improve the report HTML quality (better visual design)
# Or: Streamlit WebUI improvements (prioritized)
#
# Let me check what's easy to fix in the agent data
print()
print(f"=== Decision ===")
print("Optimization direction: Streamlit WebUI - add 'favorites/bookmarks' feature")
print("Rationale: Users often want to bookmark agents they want to track; adds user engagement")