#!/usr/bin/env python3
"""Test firecrawl status by doing a small scrape."""
import sys
sys.path.insert(0, '/home/xiowen/agent-hunter')
from hunter import FirecrawlSearch

fc = FirecrawlSearch()
# Test with a simple page
result = fc.search("AI coding tool", limit=2)
print("Result:", result)
print("Empty:", result is None or result == [] or (isinstance(result, dict) and len(result.get('results', result if isinstance(result, list) else [])) == 0))