#!/usr/bin/env python3
"""Detailed debug of _llm_chat"""
import sys
import json
import os
import traceback
sys.path.insert(0, '/home/xiowen/agent-hunter')
os.chdir('/home/xiowen/agent-hunter')

# Reload hunter to get fresh config
if 'hunter' in sys.modules:
    del sys.modules['hunter']

# Monkey patch to add debug
import hunter as h_module
original_llm_chat = h_module._llm_chat

def debug_llm_chat(messages, temperature=0.1, max_tokens=4096):
    print("=== DEBUG _llm_chat ===")
    cfg = h_module.CONFIG.get("llm", {})
    print(f"LLM Config: {cfg}")
    print(f"messages count: {len(messages)}")
    print(f"temperature: {temperature}, max_tokens: {max_tokens}")
    print("=======================")
    
    try:
        result = original_llm_chat(messages, temperature, max_tokens)
        print(f"Result length: {len(result) if result else 0}")
        print(f"Result: {repr(result)[:200]}")
        return result
    except Exception as e:
        print(f"Exception in _llm_chat: {e}")
        traceback.print_exc()
        raise

h_module._llm_chat = debug_llm_chat

# Now run discover
result = h_module.discover()
print(f"Discover result: {result}")