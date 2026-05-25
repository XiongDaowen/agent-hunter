#!/usr/bin/env python3
"""Clean up iteration-log.md: reduce excessive blank lines."""
import os

log_file = '/home/xiowen/agent-hunter/iteration-log.md'

with open(log_file) as f:
    content = f.read()

# Remove trailing empty lines
content = content.rstrip('\n')

# Normalize multiple blank lines between entries to max 2 newlines
lines = content.split('\n')
cleaned = []
skip = 0
for i, line in enumerate(lines):
    if skip > 0:
        skip -= 1
        continue
    if line == '':
        j = i
        while j < len(lines) and lines[j] == '':
            j += 1
        blank_count = j - i
        if blank_count > 2:
            cleaned.append('')
            cleaned.append('')
            skip = blank_count - 2 - 1
        else:
            cleaned.append(line)
    else:
        cleaned.append(line)

result = '\n'.join(cleaned) + '\n'
print(f'Original: {len(content)} bytes, {len(lines)} lines')
print(f'Cleaned: {len(result)} bytes, {len(result.split(chr(10)))} lines')
print(f'Size reduction: {len(content) - len(result)} bytes ({100*(len(content)-len(result))/len(content):.1f}%)')

with open(log_file, 'w') as f:
    f.write(result)
print('Done')