#!/usr/bin/env python3
"""Test _llm_chat exactly as hunter does"""
import sys
import json
import os
sys.path.insert(0, '/home/xiowen/agent-hunter')
os.chdir('/home/xiowen/agent-hunter')

# Import the module fresh
if 'hunter' in sys. modules:
    del sys.modules['hunter']
    
from hunter import _llm_chat

# Make exactly the same call that discover does
system_prompt = """你是一个专业的 AI Agent 产品分析师，擅长从搜索结果中识别和提取 AI Agent 产品信息。
请从以下网页搜索结果中提取 AI Agent 产品信息。
每个产品请提取：名称、描述、官方链接、分类。
只返回有效的 AI Agent 产品，格式为 JSON 数组。
如果未识别到任何有效产品，请返回空数组：[]"""

user_prompt = "请分析以下网页搜索结果，识别并提取 AI Agent 产品信息：\n\ntest content"

result = _llm_chat([
    {"role": "system", "content": system_prompt},
    {"role": "user", "content": user_prompt},
])

print(f"Result type: {type(result)}")
print(f"Result: {result}")