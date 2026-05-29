import json
from pathlib import Path

BASE_DIR = Path("/home/xiowen/agent-hunter")
CACHE_DIR = BASE_DIR / "cache"
news_data_file = CACHE_DIR / "news.json"

print("File exists:", news_data_file.exists())
print("File size:", news_data_file.stat().st_size if news_data_file.exists() else 0)

with open(news_data_file) as f:
    d = json.load(f)

print("Total:", d["total"])
print("Topics:", list(d["topics"].keys()))

# Simulate the insight calculation
topics = list(d.get("topics", {}).items())
devto_count = 0
hn_count = 0
total_read_time = 0
read_time_count = 0
hottest_topic = ""
hottest_count = 0
most_recent_item = None
most_recent_topic = ""
item_hours = {}

for topic_name, topic in topics:
    items = topic.get("items", [])
    count = topic.get("count", len(items))
    if count > hottest_count:
        hottest_count = count
        hottest_topic = topic.get("label", topic_name)
    for item in items:
        source = item.get("source", "")
        if "Dev.to" in source or "devto" in source.lower():
            devto_count += 1
        elif "HN" in source or "hn" in source.lower():
            hn_count += 1
        rt = item.get("read_time", 0)
        if rt and rt > 0:
            total_read_time += rt
            read_time_count += 1
        ta = item.get("time_ago", "")
        if ta:
            h_match = __import__('re').match(r"(\d+)h ago", ta)
            d_match = __import__('re').match(r"(\d+)d ago", ta)
            if h_match:
                hours = int(h_match.group(1))
                item_hours[id(item)] = hours
                if most_recent_item is None or hours < item_hours.get(id(most_recent_item), 999):
                    most_recent_item = item
                    most_recent_topic = topic.get("label", topic_name)
            elif d_match:
                days = int(d_match.group(1))
                hours = days * 24
                item_hours[id(item)] = hours
                if most_recent_item is None or hours < item_hours.get(id(most_recent_item), 999):
                    most_recent_item = item
                    most_recent_topic = topic.get("label", topic_name)

avg_read = round(total_read_time / read_time_count, 1) if read_time_count > 0 else 0

def cn(num):
    return {0:"零",1:"一",2:"二",3:"三",4:"四",5:"五",6:"六",7:"七",8:"八",9:"九"}.get(num, str(num))

print("\n--- Insights that would be generated ---")
print(f"topics count: {len(topics)}")
print(f"total: {d['total']}")
print(f"devto: {devto_count}, hn: {hn_count}")
print(f"hottest: {hottest_topic} ({hottest_count})")
print(f"avg_read: {avg_read}")
if most_recent_item:
    print(f"most_recent: {most_recent_topic} - {most_recent_item.get('title', '')[:40]}... ({most_recent_item.get('time_ago', '')})")

insight_lines = []
insight_lines.append(f"📊 共追踪 **{cn(len(topics))} 个话题**，收录 **{d['total']} 条**最新资讯")
insight_lines.append(f"🔍 数据来源：**Dev.to {devto_count} 条** · **HN {hn_count} 条**")
if hottest_topic:
    insight_lines.append(f"🔥 最活跃话题：**{hottest_topic}**（{hottest_count} 条）")
if avg_read > 0:
    insight_lines.append(f"📖 Dev.to 文章平均阅读时间：**{avg_read} 分钟**")
if most_recent_item:
    insight_lines.append(f"⏰ 最新动态：**{most_recent_topic}** — 「{most_recent_item.get('title', '')[:40]}...」({most_recent_item.get('time_ago', '')})")

print("\nFinal insight text:")
print("\n\n".join(insight_lines))