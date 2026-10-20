# =============================================================================
# scripts/init_auth_tables.py — Initialisation contrôlée du système de comptes
#
# Ce script :
#   1) crée les 3 tables nécessaires à l'authentification et à la traçabilité
#      (users, historique_connexion, journal_activite) SI elles n'existent
#      pas déjà — jamais db.create_all(), jamais de recréation de la base ;
#      les tables agricoles existantes (campagne, cooperative, variete,
#      suivi_campagne, parcelles, ...) ne sont ni lues ni modifiées ;
#   2) crée le premier compte administrateur et un compte agent, UNIQUEMENT
#      s'ils n'existent pas déjà (script idempotent, sûr à relancer).
#
# Usage :
#   venv\Scripts\python.exe scripts\init_auth_tables.py
#
# Il s'agit de la procédure contrôlée d'installation mentionnée dans le
# cahier des charges : il n'existe aucune page publique permettant de créer
# un compte administrateur.
# =============================================================================
import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from werkzeug.security import generate_password_hash

from app import create_app
from extensions import db
from models.user import User, ROLE_ADMIN, ROLE_AGENT
from models.audit import HistoriqueConnexion, JournalActivite

# Comptes initiaux (modifiables ici avant le premier lancement du script ;
# sans effet sur les lancements suivants puisque le script est idempotent).
ADMIN_ACCOUNT = {
    'nom_complet': 'Administrateur',
    'nom_utilisateur': 'REDAH',
    'password': 'ADMIN14',
}
AGENT_ACCOUNTS = [
    {
        'nom_complet': 'Jean Dupont',
        'nom_utilisateur': 'CTAA',
        'password': '1234',
    },
]


def create_tables_if_missing(engine):
    for model in (User, HistoriqueConnexion, JournalActivite):
        table = model.__table__
        table.create(bind=engine, checkfirst=True)
        print(f"Table '{table.name}' : OK (créée si absente).")


def create_account_if_missing(nom_complet, nom_utilisateur, password, role):
    existing = User.query.filter_by(nom_utilisateur=nom_utilisateur).first()
    if existing:
        print(f"Compte '{nom_utilisateur}' : déjà existant, inchangé.")
        return
    user = User(
        nom_complet=nom_complet,
        nom_utilisateur=nom_utilisateur,
        password_hash=generate_password_hash(password),
        role=role,
        actif=True,
    )
    db.session.add(user)
    db.session.commit()
    print(f"Compte '{nom_utilisateur}' ({role}) créé avec succès.")


if __name__ == '__main__':
    app = create_app()
    with app.app_context():
        create_tables_if_missing(db.engine)
        create_account_if_missing(**ADMIN_ACCOUNT, role=ROLE_ADMIN)
        for agent in AGENT_ACCOUNTS:
            create_account_if_missing(**agent, role=ROLE_AGENT)
        print("Initialisation terminée.")
