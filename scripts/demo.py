import json
import urllib.request

if __name__ == "__main__":
    print(json.dumps(json.load(urllib.request.urlopen("http://127.0.0.1:8000/health", timeout=5)), indent=2))
