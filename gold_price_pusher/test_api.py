import urllib.request
import json

url = "https://api.jisuapi.com/gold/london?appkey=33c976a06affe275"

try:
    with urllib.request.urlopen(url, timeout=10) as response:
        data = json.loads(response.read().decode('utf-8'))
        print(json.dumps(data, indent=2, ensure_ascii=False))
except Exception as e:
    print(f"Error: {e}")
