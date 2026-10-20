import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from app import create_app

paths = ['/', '/dashboard', '/login', '/api/data', '/api/parcelles']

app = create_app()
c = app.test_client()

for p in paths:
    try:
        r = c.get(p)
        text = r.get_data(as_text=True)
        summary = text[:200].replace('\n', ' ') if text else ''
        print(f"{p} {r.status_code} len={len(text)} preview={summary!r}")
    except Exception as e:
        print(f"{p} ERROR {e}")
