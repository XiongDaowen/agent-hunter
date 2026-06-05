import urllib.request
import json

req = urllib.request.Request(
    'http://localhost:8501/api/news/refresh',
    data=b'',
    headers={'Content-Type': 'application/json'},
    method='POST'
)
with urllib.request.urlopen(req, timeout=180) as resp:
    result = json.loads(resp.read())
    print('OK' if result.get('ok') else result)