import urllib.request
import json

base_url = "http://127.0.0.1:55898/api/v1"

endpoints = [
    ("/attendance", "GET", None),
    ("/employees", "GET", None),
    ("/settings", "GET", None),
    ("/ai/ask", "POST", json.dumps({"question": "hello"}).encode('utf-8'))
]

for ep, method, data in endpoints:
    url = base_url + ep
    req = urllib.request.Request(url, method=method, data=data)
    if data:
        req.add_header('Content-Type', 'application/json')
    try:
        with urllib.request.urlopen(req) as response:
            print(f"[{method}] {ep} -> {response.status}")
    except urllib.error.HTTPError as e:
        print(f"[{method}] {ep} -> FAILED: {e.code}")
        print(e.read().decode())
    except Exception as e:
        print(f"[{method}] {ep} -> FAILED: {e}")
