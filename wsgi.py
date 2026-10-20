# =============================================================================
# wsgi.py — Point d'entrée pour un serveur WSGI de production (Gunicorn)
#
# Le serveur de développement intégré à Flask (utilisé via `python app.py`)
# n'est pas conçu pour la production. Ce fichier expose l'objet `app` attendu
# par un serveur WSGI comme Gunicorn.
#
# Lancement en production :
#   gunicorn wsgi:app
#
# Lancement en développement (inchangé) :
#   python app.py
# =============================================================================

from app import create_app

app = create_app()

if __name__ == "__main__":
    app.run()
