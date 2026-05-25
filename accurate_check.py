#!/usr/bin/env python3
import os
import json
from collections import defaultdict

# 更详细的检查
print("=== Category Accuracy Check ===\n")

for f in os.listdir('agents'):
    if not f.endswith('.json'):
        continue
    d = json.load(open(f'agents/{f}'))
    name = d.get('name', 'Unknown')
    cat = d.get('category', 'Unknown')
    desc = d.get('description', '').lower()
    website = d.get('website', '')
    
    # IDE 应该是代码编辑器
    if cat == 'IDE':
        if 'editor' not in desc and 'ide' not in desc and 'code' not in desc:
            print(f"[{cat}] {name}: suspicious")
            print(f"  desc: {d.get('description', '')[:80]}")
            print()
    
    # GUI 应该是 web/云端/可视化
    if cat == 'GUI':
        is_gui = any(kw in desc for kw in ['web', '云', '平台', '可视化', 'browser', '界面'])
        if not is_gui:
            print(f"[{cat}] {name}: might be wrong category")
            print(f"  desc: {d.get('description', '')[:80]}")
            print()
    
    # Plugin 应该是编辑器插件
    if cat == 'Plugin':
        if 'plugin' not in desc and 'extension' not in desc and 'vs code' not in desc and 'jetbrains' not in desc and 'vim' not in desc:
            print(f"[{cat}] {name}: suspicious")
            print(f"  desc: {d.get('description', '')[:80]}")
            print()

print("=== Done ===")