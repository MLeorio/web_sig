# Web SIG Djagblé (AgriSIG)

Application Flask connectée à PostgreSQL/PostGIS pour le suivi agricole du
périmètre irrigué de Djagblé : saisie des suivis de campagne, carte
dynamique, tableau de bord analytique, et espace d'administration avec
gestion des comptes (administrateur/agents) et traçabilité complète.

## Description

- Page d'accueil publique, tableau de bord public (carte + graphiques).
- Connexion unique (`/login`) pour les agents et l'administrateur.
- Espace d'administration (`/admin`) : gestion des suivis (créer, consulter,
  rechercher, filtrer, modifier ; supprimer pour l'administrateur), gestion
  des agents, historique des connexions et journal des activités
  (administrateur uniquement).
- Toutes les données agricoles proviennent exclusivement de PostgreSQL/PostGIS.

## Installation

1. Créez un environnement virtuel Python :

   ```powershell
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

2. Installez les dépendances :

   ```powershell
   pip install -r requirements.txt
   ```

3. Copiez le fichier d'exemple et configurez votre connexion PostgreSQL :

   ```powershell
   copy .env.example .env
   ```

4. Modifiez `.env` pour pointer vers votre base PostgreSQL/PostGIS existante
   (`DATABASE_URL`, `FLASK_SECRET`).

5. Initialisez le système de comptes (une seule fois) : crée les tables
   `users`, `historique_connexion`, `journal_activite` si elles n'existent
   pas encore, et le premier compte administrateur. Sans effet si déjà fait
   (script idempotent) :

   ```powershell
   venv\Scripts\python.exe scripts\init_auth_tables.py
   ```

6. Lancez l'application (développement) :

   ```powershell
   python app.py
   ```

7. Ouvrez le navigateur sur :

   ```text
   http://127.0.0.1:5000
   ```

## Déploiement (production)

Le serveur intégré de Flask (`python app.py`) est réservé au développement.
Un point d'entrée WSGI (`wsgi.py`) est prévu pour Gunicorn :

```powershell
venv\Scripts\gunicorn.exe wsgi:app
```

(sous Linux/macOS : `gunicorn wsgi:app`). Ceci prépare l'application pour la
production ; elle n'y est pas déployée automatiquement.

## Accès et rôles

Trois profils :

| Profil | Accès |
|---|---|
| Visiteur (pas de compte) | Accueil, Dashboard, carte, graphiques |
| Agent | + Connexion, saisie/consultation/modification des suivis |
| Administrateur | + suppression des suivis, gestion des agents, historique des connexions, journal des activités |

La connexion se fait sur `/login`. Le premier administrateur est créé par
`scripts/init_auth_tables.py` (jamais par une page publique). Un
administrateur crée ensuite les comptes agents depuis
`/admin/agents/nouveau`.

## Extensibilité

- Ajoutez une nouvelle couche cartographique en l'inscrivant dans
  `routes/api.py` (`layer_map`) et `static/js/dashboard.js` (`layerNames`).
- Les graphiques et commentaires du dashboard sont alimentés automatiquement
  à partir des données enregistrées (voir `services/dashboard_service.py`).

## Tests et vérifications

- Vérifier la connexion à la base de données :

```powershell
venv\Scripts\python.exe scripts\check_db_connection.py
```

- Test rapide (smoke test) :

```powershell
venv\Scripts\python.exe scripts\smoke_test.py
```

- Tests unitaires : certaines suites peuvent créer/supprimer des tables en local. Pour autoriser la création de tables pendant les tests, définissez :

```powershell
$env:ALLOW_TEST_DB_CREATE=1
python -m unittest discover -v
```

## Sécurité

- Protection CSRF activée (Flask-WTF) sur tous les formulaires.
- Mots de passe stockés uniquement sous forme de hash (Werkzeug), jamais en clair.
- Chaque route d'administration est protégée côté serveur (décorateurs
  `login_required` / `role_required` dans `auth.py`) : une URL admin tapée
  directement par un agent est refusée, pas seulement masquée dans l'interface.
- Toute connexion, déconnexion, échec de connexion et action importante
  (création/modification/suppression d'un suivi, gestion des comptes) est
  journalisée automatiquement (tables `historique_connexion` et
  `journal_activite`), jamais saisie manuellement.
- Le projet n'exécute jamais `db.create_all()` : les tables agricoles
  existent déjà en base, et les 3 tables propres à l'application sont créées
  individuellement par `scripts/init_auth_tables.py` (`checkfirst=True`).
- Identifiants et informations sensibles exclusivement dans `.env` (non versionné).
