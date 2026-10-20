# =============================================================================
# app.py — Application principale Flask (Web SIG Agricole)
#
# Ce fichier contient :
#   1) L'initialisation des extensions (SQLAlchemy, CSRF)
#   2) Les routes publiques (accueil, dashboard) et d'authentification
#      (connexion unique administrateur/agent, déconnexion)
#   3) La fabrique `create_app()` qui assemble l'application Flask
#
# L'espace d'administration (suivis, agents, historique, journal) vit dans
# routes/admin.py. Les routes de l'API cartographique/dashboard (/api/...)
# vivent dans routes/api.py. La logique métier sur `suivi_campagne` vit dans
# services/suivi_service.py.
# =============================================================================

from datetime import datetime

from flask import Flask, render_template, jsonify, redirect, url_for, flash, Blueprint, session
from flask_wtf import CSRFProtect
from sqlalchemy import select
from werkzeug.security import check_password_hash
from dotenv import load_dotenv

from extensions import db
from config import Config
from forms import LoginForm
from auth import log_connexion, get_current_user
from models.user import User
from models.audit import EVT_CONNEXION_REUSSIE, EVT_ECHEC_CONNEXION, EVT_DECONNEXION
from services.suivi_service import get_table
from routes.api import api_bp
from routes.admin import admin_bp

load_dotenv()

# Blueprint regroupant les routes publiques et d'authentification.
main_bp = Blueprint('main', __name__)


# =============================================================================
# Route publique : page d'accueil
# =============================================================================

@main_bp.route("/")
def index():
    return render_template("index.html")


# =============================================================================
# Authentification (connexion unique administrateur / agent)
# =============================================================================

@main_bp.route("/login", methods=["GET", "POST"])
def login():
    if session.get('user_id'):
        return redirect(url_for('admin.dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        username = form.username.data.strip()
        user = User.query.filter_by(nom_utilisateur=username).first()

        if user and check_password_hash(user.password_hash, form.password.data):
            if not user.actif:
                flash("Votre compte est actuellement désactivé. Veuillez contacter l'administrateur.", 'danger')
                log_connexion(EVT_ECHEC_CONNEXION, nom_utilisateur_saisi=username)
            else:
                session['user_id'] = user.id
                session['role'] = user.role
                session['nom_complet'] = user.nom_complet
                user.derniere_connexion = datetime.utcnow()
                db.session.commit()
                log_connexion(EVT_CONNEXION_REUSSIE, user=user)
                return redirect(url_for('admin.dashboard'))
        else:
            # Message générique : ne révèle jamais si c'est l'identifiant ou
            # le mot de passe qui est incorrect.
            flash("Nom d'utilisateur ou mot de passe incorrect.", 'danger')
            log_connexion(EVT_ECHEC_CONNEXION, nom_utilisateur_saisi=username)

    return render_template('login.html', form=form)


@main_bp.route('/logout')
def logout():
    user = get_current_user()
    if user:
        log_connexion(EVT_DECONNEXION, user=user)
    session.clear()
    flash('Déconnecté.', 'success')
    return redirect(url_for('main.login'))


# Compatibilité avec les anciennes URLs (ancien système mono-administrateur).
@main_bp.route('/admin-access', methods=['GET', 'POST'])
def admin_access_redirect():
    return redirect(url_for('main.login'), code=301)


@main_bp.route('/admin/logout')
def admin_logout_redirect():
    return redirect(url_for('main.logout'), code=301)


# =============================================================================
# Tableau de bord (carte dynamique + graphiques) — accès public (visiteur)
# =============================================================================
# La page ne fait que du rendu statique : la carte (via /api/<layer>) et les
# graphiques (via /api/dashboard, /api/campaigns) sont chargés en Ajax par
# static/js/dashboard.js. Voir routes/api.py et services/dashboard_service.py
# pour le calcul des agrégats affichés.

@main_bp.route("/dashboard")
def dashboard():
    return render_template('dashboard.html')


# =============================================================================
# API brute : export JSON de toutes les lignes de suivi_campagne
# =============================================================================
# Endpoint indépendant du dashboard, utile pour inspecter/exporter les
# données brutes (ex. vérifications manuelles, script scripts/smoke_test.py).

@main_bp.route('/api/data')
def api_data():
    try:
        suivi = get_table('suivi_campagne')
        records = [dict(row) for row in db.session.execute(select(suivi).order_by(suivi.c.id_suivi.desc())).mappings().all()]
    except Exception:
        return jsonify({'data': []})
    return jsonify({'data': records})


# =============================================================================
# Fabrique de l'application (application factory)
# =============================================================================

def create_app(test_config=None):
    app = Flask(__name__)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    # Rattache les extensions à cette instance d'application
    db.init_app(app)
    CSRFProtect(app)

    @app.template_filter('fmt_date')
    def fmt_date_filter(value):
        """Affiche '—' pour une date absente ou une date sentinelle
        (0001-01-01, présente pour quelques suivis anciens de la base) sans
        jamais modifier la valeur réellement stockée en PostgreSQL."""
        if not value or getattr(value, 'year', None) == 1:
            return '—'
        return value

    # Enregistre les blueprints : pages publiques (main_bp), administration
    # (admin_bp) et API SIG/dashboard (api_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(main_bp)
    app.register_blueprint(admin_bp)

    # Alias des endpoints sans le préfixe 'main.' pour compatibilité avec
    # d'anciens usages de url_for('index'), etc.
    for name in ('index', 'login', 'logout', 'dashboard', 'api_data'):
        pref = f'main.{name}'
        if pref in app.view_functions:
            app.view_functions[name] = app.view_functions[pref]

    return app


if __name__ == "__main__":
    _app = create_app()
    _app.run(debug=True, host="0.0.0.0", port=5000)
