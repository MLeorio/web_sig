# =============================================================================
# extensions.py — Instances partagées des extensions Flask
#
# Isolé dans son propre module (plutôt que défini dans app.py) pour que les
# modèles (models/) et les blueprints (routes/) puissent importer `db` sans
# jamais avoir à importer app.py — ce qui créerait une dépendance circulaire
# (app.py importe les blueprints, qui auraient sinon besoin d'importer app.py).
# =============================================================================

from flask_sqlalchemy import SQLAlchemy

db = SQLAlchemy()
