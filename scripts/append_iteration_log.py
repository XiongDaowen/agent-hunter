#!/usr/bin/env python3
"""插入新的迭代记录到 iteration-log.md，按日期顺序排列。

用法:
  python3 append_iteration_log.py <log_file> <new_entry_file>
  python3 append_iteration_log.py <log_file>                      # 从 stdin 读取新条目

新条目格式: (---\n## YYYY-MM-DD HH:MM ...\n...\n)
会自动找到正确的位置插入，保持时间正序。
"""

import re
import sys
import os
from datetime import datetime


ENTRY_PATTERN = re.compile(r'^## (\d{4}-\d{2}-\d{2} \d{2}:\d{2})', re.MULTILINE)


def parse_datetime(s: str) -> datetime | None:
    try:
        return datetime.strptime(s.strip(), '%Y-%m-%d %H:%M')
    except ValueError:
        return None


def read_entries(text: str) -> list[dict]:
    """Split file into entries by '## YYYY-MM-DD HH:MM' headers."""
    lines = text.split('\n')
    entries = []
    current = []
    current_dt = None
    for line in lines:
        m = ENTRY_PATTERN.match(line)
        if m:
            if current and current_dt is not None:
                entries.append({'dt': current_dt, 'text': '\n'.join(current)})
            current_dt = parse_datetime(m.group(1))
            current = [line]
        else:
            current.append(line)
    if current and current_dt is not None:
        entries.append({'dt': current_dt, 'text': '\n'.join(current)})

    # Return non-date parts too (header, trailing empty lines)
    return entries


def main():
    if len(sys.argv) < 2:
        print("Usage: append_iteration_log.py <log_file> [new_entry_file]")
        sys.exit(1)

    log_file = sys.argv[1]

    # Read new entry
    if len(sys.argv) >= 3:
        with open(sys.argv[2]) as f:
            new_text = f.read().strip()
    else:
        new_text = sys.stdin.read().strip()

    if not new_text:
        print("error: empty entry")
        sys.exit(1)

    # Parse new entry date
    m = ENTRY_PATTERN.search(new_text)
    if not m:
        print("error: new entry missing '## YYYY-MM-DD HH:MM' header")
        sys.exit(1)
    new_dt = parse_datetime(m.group(1))
    if new_dt is None:
        print(f"error: cannot parse date from '{m.group(1)}'")
        sys.exit(1)

    # Read existing file
    if os.path.exists(log_file):
        with open(log_file) as f:
            content = f.read()
    else:
        content = '# Agent Daily Report 迭代日志\n\n'

    # Split into header (before first entry) and entries
    entries = read_entries(content)

    # Find insertion point (file is newest-first, so find first entry older than new_dt)
    insert_idx = len(entries)
    for i, e in enumerate(entries):
        if e['dt'] and new_dt > e['dt']:
            # new entry is newer than this entry → insert BEFORE it
            insert_idx = i
            break
        if e['dt'] and new_dt == e['dt']:
            # Same time: insert after existing (more recent edits go later)
            insert_idx = i + 1
            break

    entries.insert(insert_idx, {'dt': new_dt, 'text': new_text})

    # Rebuild file
    result_parts = []
    for i, e in enumerate(entries):
        result_parts.append(e['text'])

    with open(log_file, 'w') as f:
        f.write('\n\n'.join(result_parts) + '\n')

    print(f"✔ 已插入记录 [{m.group(1)}] 到第 {insert_idx + 1} 条位置 (共 {len(entries)} 条)")


if __name__ == '__main__':
    main()