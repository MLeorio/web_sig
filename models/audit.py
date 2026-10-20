# =============================================================================
# models/audit.py — Traçabilité : connexions et journal des activités
#
# Deux tables nouvelles, remplies automatiquement par auth.py (jamais saisies
# manuellement). Elles ne touchent à aucune table agricole existante.
# =============================================================================

from datetime import datetime

from extensions import db

# Types d'événements de connexion (historique_connexion.type_evenement)
EVT_CONNEXION_REUSSIE = 'connexion_reussie'
EVT_DECONNEXION = 'deconnexion'
EVT_ECHEC_CONNEXION = 'echec_connexion'


class HistoriqueConnexion(db.Model):
    __tablename__ = 'historique_connexion'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('public.users.id'), nullable=True)
    nom_utilisateur_saisi = db.Column(db.String(80), nullable=True)
    date_heure = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    type_evenement = db.Column(db.String(30), nullable=False)
    adresse_ip = db.Column(db.String(45), nullable=True)

    utilisateur = db.relationship('User', foreign_keys=[id_utilisateur])


class JournalActivite(db.Model):
    __tablename__ = 'journal_activite'
    __table_args__ = {'schema': 'public'}

    id = db.Column(db.Integer, primary_key=True)
    id_utilisateur = db.Column(db.Integer, db.ForeignKey('public.users.id'), nullable=True)
    date_heure = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    action = db.Column(db.String(50), nullable=False)
    objet_type = db.Column(db.String(50), nullable=True)
    objet_id = db.Column(db.String(50), nullable=True)
    details = db.Column(db.Text, nullable=True)

    utilisateur = db.relationship('User', foreign_keys=[id_utilisateur])
