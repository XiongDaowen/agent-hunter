import requests
import re

url = 'https://hn.algolia.com/api/v1/search'
params = {'query': 'AI coding agent terminal', 'tags': 'story', 'hitsPerPage': 3}
resp = requests.get(url, params=params, timeout=15)
data = resp.json()
print('Status:', resp.status_code)
print('Hits:', len(data.get('hits', [])))
for hit in data.get('hits', [])[:3]:
    print(' -', hit.get('title', '')[:60], '|', hit.get('url', '')[:50])
