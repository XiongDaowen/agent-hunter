#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/xiowen/agent-hunter')
import hunter as h
print("CONFIG LLM:", h.CONFIG.get('llm'))
print("base_url:", h.CONFIG.get('llm', {}).get('base_url'))