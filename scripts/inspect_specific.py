from dotenv import load_dotenv
load_dotenv()
import os
from sqlalchemy import create_engine, text

url = os.getenv('DATABASE_URL')
engine = create_engine(url)

tables = ['cannaux_irrigation','aires_sechage']
for tbl in tables:
    print('\nTABLE:', tbl)
    with engine.connect() as conn:
        cols = conn.execute(text("SELECT column_name, udt_name FROM information_schema.columns WHERE table_schema='public' AND table_name=:tbl"), {'tbl':tbl}).all()
        for c in cols:
            print('  ', c[0], c[1])
        cnt = conn.execute(text(f"SELECT count(*) FROM public.{tbl}")).scalar()
        print('  rows', cnt)
        # try to get a sample ST_AsGeoJSON
        geom_cols = [c[0] for c in cols if 'geometry' in (c[1] or '').lower()]
        print('  geom_cols', geom_cols)
        if geom_cols:
            g = geom_cols[0]
            samples = conn.execute(text(f"SELECT ST_AsGeoJSON({g}) FROM public.{tbl} WHERE {g} IS NOT NULL LIMIT 3")).all()
            print('  samples', len(samples))
print('\nDone')
