import urllib.request,json
try: print(json.dumps(json.load(urllib.request.urlopen('http://localhost:8000/health',timeout=4)),indent=2))
except Exception as e: raise SystemExit(f'Backend health check failed: {e}')
