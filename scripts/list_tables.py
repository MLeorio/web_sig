from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

url = os.getenv('DATABASE_URL')
if not url:
    print('No DATABASE_URL')
    raise SystemExit(1)

engine = create_engine(url)
with engine.connect() as conn:
    res = conn.execute(text("SELECT table_schema, table_name FROM information_schema.tables WHERE table_schema NOT IN ('pg_catalog','information_schema') ORDER BY table_schema, table_name"))
    tables = res.fetchall()
    for s,t in tables:
        print(s, t)
