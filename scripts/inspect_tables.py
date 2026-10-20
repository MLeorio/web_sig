import os
from sqlalchemy import create_engine, text
from dotenv import load_dotenv

load_dotenv()
url = os.getenv('DATABASE_URL')
if not url:
    print('No DATABASE_URL environment variable set')
    raise SystemExit(1)

engine = create_engine(url)

tables = ['canaux_irrigation', 'aire_sechage']
for tbl in tables:
    print('\nTABLE:', tbl)
    try:
        with engine.connect() as conn:
            q = text("SELECT column_name, udt_name FROM information_schema.columns WHERE table_schema='public' AND table_name = :tbl")
            res = conn.execute(q, {'tbl': tbl}).all()
            if not res:
                print('  (no columns found)')
            else:
                for r in res:
                    print('  ', r[0], r[1])
            try:
                cnt = conn.execute(text(f"SELECT count(*) FROM public.{tbl}")).scalar()
                print('  rows:', cnt)
            except Exception as e:
                print('  count error:', e)
            # try a sample geojson
            try:
                geomq = text(f"SELECT column_name FROM information_schema.columns WHERE table_schema='public' AND table_name = :tbl AND udt_name ilike '%geometry%'")
                gres = conn.execute(geomq, {'tbl': tbl}).all()
                geom_cols = [r[0] for r in gres]
                print('  geometry columns detected:', geom_cols)
                if geom_cols:
                    g = geom_cols[0]
                    sj = conn.execute(text(f"SELECT ST_AsGeoJSON({g}) FROM public.{tbl} WHERE {g} IS NOT NULL LIMIT 3")).all()
                    print('  sample geojson rows:', len(sj))
                else:
                    print('  no geometry cols to sample')
            except Exception as e:
                print('  sample geojson error:', e)
    except Exception as e:
        print('  error inspecting table:', e)
print('\nDone')
