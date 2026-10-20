# =============================================================================
# models/user.py — Comptes utilisateurs (administrateur ou agent)
#
# Nouvelle table `users`, indépendante des tables agricoles existantes
# (campagne, cooperative, variete, suivi_campagne, parcelles, ...) : rien
# n'est modifié ni supprimé côté données agricoles.
# =============================================================================

from datetime import datetime

from extensions import db

ROLE_ADMIN = 'administrateur'
ROLE_AGENT = 'agent'
ROLES = (ROLE_ADMIN, ROLE_AGENT)


class User(db.Model):
    __tablename__ = 'users'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    nom_complet = db.Column(db.String(150), nullable=False)
    nom_utilisateur = db.Column(db.String(80), nullable=False, unique=True)
    email = db.Column(db.String(150), nullable=True)
    password_hash = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(20), nullable=False, default=ROLE_AGENT)
    actif = db.Column(db.Boolean, nullable=False, default=True)
    date_creation = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    derniere_connexion = db.Column(db.DateTime, nullable=True)

    def is_admin(self):
        return self.role == ROLE_ADMIN

    def to_dict(self):
        return {
            'id': self.id,
            'nom_complet': self.nom_complet,
            'nom_utilisateur': self.nom_utilisateur,
            'email': self.email,
            'role': self.role,
            'actif': self.actif,
            'date_creation': self.date_creation,
            'derniere_connexion': self.derniere_connexion,
        }
