#!/usr/bin/env python3
"""Verify state files after iteration."""
import json
import os

state_file = '/home/xiowen/.hermes/scripts/agent-evolution-state.json'
with open(state_file) as f:
    d = json.load(f)

print(f'iteration_count: {d["iteration_count"]}')
print(f'last_run: {d["last_run"]}')
print(f'done_categories: {len(d["done_categories"])}')
print(f'failed_patterns: {len(d["failed_patterns"])}')

log_file = '/home/xiowen/agent-hunter/iteration-log.md'
size = os.path.getsize(log_file)
lines = len(open(log_file).readlines())
print(f'iteration-log.md: {size} bytes, {lines} lines')

print('All OK')