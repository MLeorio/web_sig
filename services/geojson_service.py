from flask import current_app
from sqlalchemy import text
import os


def fetch_layer_geojson(table_name, geom_column=None, srid=4326, limit=None, schema=None):
    """Return a GeoJSON FeatureCollection produced by PostGIS for the given table.

    This function runs a SQL query using ST_AsGeoJSON on the geometry column and
    returns a Python dict representing a GeoJSON FeatureCollection. It purposely
    avoids loading ORM models to keep the query efficient.
    """
    engine = current_app.extensions['sqlalchemy'].db.engine
    if schema is None:
        schema = os.getenv('DB_SCHEMA', 'public')

    cols_query = text("SELECT column_name, udt_name FROM information_schema.columns WHERE table_schema = :schema AND table_name = :tbl")
    with engine.connect() as conn:
        res = conn.execute(cols_query, {'tbl': table_name, 'schema': schema})
        cols = [dict(row._mapping) for row in res]

        # detect geometry column if not provided
        if geom_column is None:
            geom_candidates = [c['column_name'] for c in cols if 'geometry' in (c['udt_name'] or '').lower()]
            if not geom_candidates:
                # fallback to common names
                for name in ('geom', 'the_geom', 'wkb_geometry', 'shape'):
                    if any(c['column_name'] == name for c in cols):
                        geom_candidates = [name]
                        break
            geom_column = geom_candidates[0] if geom_candidates else None

        # try to detect primary key column
        pk_query = text("SELECT a.attname as column_name FROM pg_index i JOIN pg_attribute a ON a.attrelid = i.indrelid AND a.attnum = ANY(i.indkey) WHERE i.indrelid = (:schema || '.' || :tbl)::regclass AND i.indisprimary")
        pk_col = None
        try:
            pk_res = conn.execute(pk_query, {'tbl': table_name, 'schema': schema}).all()
            if pk_res:
                pk_col = pk_res[0][0]
        except Exception:
            pk_col = None

        col_names = [c['column_name'] for c in cols]
        if not pk_col:
            if 'id' in col_names:
                pk_col = 'id'
            else:
                # pick first non-geom column as id fallback
                non_geom = [c for c in col_names if c != geom_column]
                pk_col = non_geom[0] if non_geom else None

        # exclude geometry column from properties
        prop_cols = [c for c in col_names if c != geom_column and c != pk_col]

        select_props = ', '.join([f"{c}" for c in prop_cols]) if prop_cols else 'NULL'
        if limit:
            limit_clause = f"LIMIT {int(limit)}"
        else:
            limit_clause = ''

        id_select = pk_col or 'NULL'
        geom_select = geom_column or 'NULL'
        sql = text(f"SELECT {id_select} as id, ST_AsGeoJSON({geom_select}) AS geojson, {select_props} FROM {schema}.{table_name} {limit_clause}")
        rows = conn.execute(sql).mappings().all()

        features = []
        for row in rows:
            geom = row.get('geojson')
            props = {k: row[k] for k in row.keys() if k not in ('geojson', 'id')}
            try:
                geometry = None if geom is None else __import__('json').loads(geom)
            except Exception:
                geometry = None
            features.append({
                'type': 'Feature',
                'id': row.get('id'),
                'geometry': geometry,
                'properties': props,
            })

        return {
            'type': 'FeatureCollection',
            'features': features,
        }
