"""Modèles SQLAlchemy de l'application.

Les données agricoles (campagne, cooperative, variete, suivi_campagne,
parcelles, ...) restent lues par réflexion dynamique du schéma (voir
services/suivi_service.py) plutôt que par des modèles déclarés ici : elles
existaient déjà en base avant l'application et leur structure est pilotée
depuis PostgreSQL/QGIS.

Les modèles de ce paquet ne concernent que ce que l'application possède
réellement en propre : les comptes utilisateurs et la traçabilité.
"""

from .user import User
from .audit import HistoriqueConnexion, JournalActivite

__all__ = ["User", "HistoriqueConnexion", "JournalActivite"]
