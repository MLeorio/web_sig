from flask import Blueprint, jsonify, current_app, request
from services.geojson_service import fetch_layer_geojson
from services.dashboard_service import fetch_dashboard_for_campaign, list_campaigns

api_bp = Blueprint('api', __name__)


@api_bp.route('/api/<layer>', methods=['GET'])
def layer_geojson(layer):
    """Generic endpoint returning GeoJSON for a given layer name.

    Example: /api/parcelles
    """
    # map public-facing layer names to actual DB table names when needed
    layer_map = {
        'parcelles': 'parcelles',
        'pistes': 'pistes',
        'canaux_irrigation': 'cannaux_irrigation',  # note: DB table is 'cannaux_irrigation'
        'magasins': 'magasins',
        'aire_sechage': 'aires_sechage',  # DB table is 'aires_sechage'
        'limite_etat': 'limite_etat',
        'vannes': 'vannes',
        'zio': 'zio'
    }

    if layer not in layer_map:
        return jsonify({'error': 'Layer not allowed'}), 400

    table_name = layer_map[layer]
    limit = request.args.get('limit')
    try:
        geo = fetch_layer_geojson(table_name, limit=limit)
        return jsonify(geo)
    except Exception as exc:
        current_app.logger.exception('Error fetching geojson for %s: %s', layer, exc)
        return jsonify({'type': 'FeatureCollection', 'features': []})


@api_bp.route('/api/campaigns')
def api_campaigns():
    try:
        camps = list_campaigns()
        return jsonify({'campaigns': camps})
    except Exception as exc:
        current_app.logger.exception('Error listing campaigns: %s', exc)
        return jsonify({'campaigns': []})


@api_bp.route('/api/dashboard')
def api_dashboard():
    campagne_id = request.args.get('campagne_id', type=int)
    try:
        data = fetch_dashboard_for_campaign(campagne_id)
        return jsonify({'success': True, 'data': data})
    except Exception as exc:
        current_app.logger.exception('Error fetching dashboard for %s: %s', campagne_id, exc)
        return jsonify({'success': False, 'error': str(exc), 'data': {}})
