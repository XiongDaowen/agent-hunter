#!/usr/bin/env python3
import sys
sys.path.insert(0, '/home/xiowen/agent-hunter')
from hunter import _llm_chat

result = _llm_chat([{"role": "user", "content": "Say 'OK' in one word"}])
print(f"Result: {result}")