# =============================================================================
# auth.py — Authentification, autorisations et traçabilité
#
# Décorateurs de contrôle d'accès (vérifiés côté serveur, jamais seulement en
# masquant des boutons côté interface) + fonctions d'aide pour journaliser
# automatiquement les connexions et les actions importantes.
# =============================================================================

from functools import wraps
from flask import session, redirect, url_for, flash, request

from extensions import db
from models.user import User
from models.audit import (
    HistoriqueConnexion, JournalActivite,
    EVT_CONNEXION_REUSSIE, EVT_DECONNEXION, EVT_ECHEC_CONNEXION,
)


def get_current_user():
    """Utilisateur actuellement connecté (objet User), ou None."""
    user_id = session.get('user_id')
    if not user_id:
        return None
    return db.session.get(User, user_id)


def login_required(view):
    """Exige une session authentifiée (administrateur ou agent)."""
    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get('user_id'):
            flash("Veuillez vous connecter pour accéder à cette page.", "warning")
            return redirect(url_for('main.login', next=request.path))
        return view(*args, **kwargs)
    return wrapped


def role_required(*roles):
    """Restreint une route aux utilisateurs ayant l'un des rôles indiqués.

    La vérification est faite ici, côté serveur, à chaque requête : un agent
    qui saisit directement une URL d'administration (ex. /admin/agents) est
    bloqué même si aucun lien ne pointe vers cette page dans son interface.
    """
    def decorator(view):
        @wraps(view)
        def wrapped(*args, **kwargs):
            if not session.get('user_id'):
                flash("Veuillez vous connecter pour accéder à cette page.", "warning")
                return redirect(url_for('main.login', next=request.path))
            if session.get('role') not in roles:
                flash("Vous n'avez pas les droits nécessaires pour accéder à cette page.", "danger")
                return redirect(url_for('admin.dashboard'))
            return view(*args, **kwargs)
        return wrapped
    return decorator


def log_connexion(type_evenement, user=None, nom_utilisateur_saisi=None):
    """Enregistre automatiquement un événement de connexion. Jamais saisi
    manuellement : appelé uniquement depuis la route de connexion/déconnexion."""
    entry = HistoriqueConnexion(
        id_utilisateur=user.id if user else None,
        nom_utilisateur_saisi=nom_utilisateur_saisi or (user.nom_utilisateur if user else None),
        type_evenement=type_evenement,
        adresse_ip=request.remote_addr,
    )
    db.session.add(entry)
    db.session.commit()


def log_activite(action, objet_type=None, objet_id=None, details=None):
    """Enregistre automatiquement une action importante dans le journal
    d'activité, attribuée à l'utilisateur actuellement connecté."""
    user = get_current_user()
    entry = JournalActivite(
        id_utilisateur=user.id if user else None,
        action=action,
        objet_type=objet_type,
        objet_id=str(objet_id) if objet_id is not None else None,
        details=details,
    )
    db.session.add(entry)
    db.session.commit()
