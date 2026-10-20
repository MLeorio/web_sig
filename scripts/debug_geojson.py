from dotenv import load_dotenv
load_dotenv()
import os
from flask import Flask
from app import create_app
from services.geojson_service import fetch_layer_geojson

app = create_app({'TESTING': True})
with app.app_context():
    for layer in ['cannaux_irrigation', 'aires_sechage']:
        try:
            geo = fetch_layer_geojson(layer)
            print('LAYER', layer)
            print('FEATURES', len(geo.get('features', [])))
            if geo.get('features'):
                print('FIRST', geo['features'][0])
        except Exception as exc:
            print('ERROR', layer, exc)
