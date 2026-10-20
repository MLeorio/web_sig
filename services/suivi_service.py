# =============================================================================
# services/suivi_service.py — Accès aux données de suivi de campagne
#
# Centralise tout ce qui touche à la table `suivi_campagne` : introspection
# dynamique du schéma (pour le formulaire de saisie/modification), et
# opérations de liste/détail/création/modification/suppression utilisées par
# l'espace d'administration (routes/admin.py).
#
# Choix de conception conservé : pas de modèle ORM figé pour les données
# agricoles, mais une réflexion SQLAlchemy Core du schéma réel, de sorte que
# le formulaire s'adapte automatiquement si la table évolue en base.
# =============================================================================

import os
from sqlalchemy import MetaData, Table, select, text

from extensions import db


def get_schema():
    """Nom du schéma PostgreSQL à utiliser (défaut : 'public')."""
    return os.getenv("DB_SCHEMA", "public")


def humanize_column(name):
    """Transforme un nom de colonne SQL (ex: 'qte_npk') en libellé lisible
    pour l'affichage dans le formulaire de saisie (ex: 'Quantité npk')."""
    label = name.replace("id_", "")
    label = label.replace("_", " ")
    label = label.replace("qte_", "quantité ")
    label = label.replace("nom_", "nom ")
    label = label.replace("date_", "date ")
    return label.capitalize()


def get_table(name):
    """Reflète dynamiquement une table existante de la base (via SQLAlchemy
    Core) sans dépendre d'un modèle ORM déclaré à l'avance."""
    metadata = MetaData()
    return Table(name, metadata, autoload_with=db.engine, schema=get_schema())


def get_form_choices():
    """Récupère les listes déroulantes du formulaire de saisie (campagnes,
    coopératives, variétés) directement depuis leurs tables de référence."""
    choices = {}
    try:
        campagne = get_table('campagne')
        cooperative = get_table('cooperative')
        variete = get_table('variete')

        choices['id_campagne'] = [('', 'Sélectionner une campagne')] + [
            (row['id_campagne'], str(row['annee']))
            for row in db.session.execute(select(campagne)).mappings().all()
        ]
        choices['id_cooperative'] = [('', 'Sélectionner une coopérative')] + [
            (row['id_cooperative'], row['nom_cooperative'])
            for row in db.session.execute(select(cooperative)).mappings().all()
        ]
        choices['id_variete'] = [('', 'Sélectionner une variété')] + [
            (row['id_variete'], row['nom_variete'])
            for row in db.session.execute(select(variete)).mappings().all()
        ]
    except Exception:
        # Base indisponible ou tables absentes : le formulaire reste
        # affichable, simplement sans options dans les listes déroulantes.
        choices['id_campagne'] = []
        choices['id_cooperative'] = []
        choices['id_variete'] = []
    return choices


def get_form_fields(values=None):
    """Construit dynamiquement la liste des champs du formulaire à partir des
    colonnes réelles de `suivi_campagne`. Si `values` est fourni (dict nom de
    colonne -> valeur), les champs sont préremplis : utilisé aussi bien pour
    la création (values=None) que pour la modification d'un suivi existant."""
    from sqlalchemy import inspect
    inspector = inspect(db.engine)
    columns = inspector.get_columns('suivi_campagne', schema=get_schema())
    choices = get_form_choices()
    fields = []
    values = values or {}

    for col in columns:
        name = col['name']
        if name == 'id_suivi':
            continue  # clé primaire : jamais saisie manuellement

        dtype = str(col['type']).lower()
        field = {
            'name': name,
            'label': humanize_column(name),
            'required': not col['nullable'],
            'type': 'text',
            'step': None,
            'options': None,
            'value': values.get(name, ''),
        }

        if name in choices and choices[name]:
            field['type'] = 'select'
            field['options'] = choices[name]
        elif 'date' in dtype:
            field['type'] = 'date'
            if field['value']:
                # les valeurs issues de la base sont des objets date/datetime
                field['value'] = str(field['value'])[:10]
        elif 'integer' in dtype:
            field['type'] = 'number'
            field['step'] = '1'
        elif 'numeric' in dtype or 'decimal' in dtype or 'float' in dtype:
            field['type'] = 'number'
            field['step'] = '0.01'
        elif 'bool' in dtype:
            field['type'] = 'checkbox'
        elif name in ('production_ecoulee', 'production_restante', 'notes'):
            field['type'] = 'textarea'
        else:
            field['type'] = 'text'

        fields.append(field)

    return fields


# Regroupement thématique des champs pour l'affichage en sections (saisie,
# modification, consultation). Purement présentation.
FORM_SECTIONS = [
    ('Identification', ('id_campagne', 'id_cooperative', 'id_variete')),
    ('Effectifs', ('effectif_hommes', 'effectif_femmes')),
    ('Superficies', ('superficie_attribuee', 'superficie_cultivee')),
    ('Travaux agricoles', (
        'date_debut_labour', 'date_fin_labour',
        'date_debut_mise_boue', 'date_fin_mise_boue',
        'date_pepiniere', 'date_repiquage',
        'date_1_desherbage', 'date_2_desherbage',
        'date_debut_epandage_npk', 'date_fin_epandage_npk', 'date_epandage_uree',
    )),
    ('Intrants', ('qte_npk', 'qte_uree', 'qte_herbicide', 'qte_insecticide')),
    ('Récolte et production', (
        'date_recolte', 'production_kg', 'rendement_ha',
        'disponibilite_agregateur', 'production_ecoulee', 'production_restante',
    )),
]


def group_fields_by_section(fields):
    """Répartit les champs du formulaire dans les sections ci-dessus. Toute
    colonne présente en base mais absente de FORM_SECTIONS (schéma futur)
    atterrit automatiquement dans une section "Autres informations"."""
    remaining = {f['name']: f for f in fields}
    sections = []
    for title, names in FORM_SECTIONS:
        section_fields = [remaining.pop(name) for name in names if name in remaining]
        if section_fields:
            sections.append({'title': title, 'fields': section_fields})
    if remaining:
        sections.append({'title': 'Autres informations', 'fields': list(remaining.values())})
    return sections


def parse_value(raw_value, field):
    """Convertit la valeur brute (string) reçue du formulaire HTML vers le
    type Python attendu par la colonne SQL correspondante."""
    if raw_value is None or raw_value == '':
        return None
    if field['type'] == 'number':
        if field['step'] == '1':
            try:
                return int(raw_value)
            except ValueError:
                return None
        try:
            return float(raw_value)
        except ValueError:
            return None
    if field['type'] == 'checkbox':
        return raw_value.lower() in ('1', 'true', 'on', 'yes')
    return raw_value


# -----------------------------------------------------------------------------
# Liste, détail, création, modification, suppression (espace d'administration)
# -----------------------------------------------------------------------------

def _base_joins():
    schema = get_schema()
    return (
        f"FROM {schema}.suivi_campagne s "
        f"JOIN {schema}.cooperative c ON s.id_cooperative = c.id_cooperative "
        f"JOIN {schema}.campagne ca ON s.id_campagne = ca.id_campagne "
        f"JOIN {schema}.variete v ON s.id_variete = v.id_variete"
    )


def list_suivis(campagne_id=None, cooperative_id=None, variete_id=None, q=None, page=1, per_page=20):
    """Liste paginée des suivis, avec filtres optionnels. Toutes les valeurs
    proviennent de requêtes SQL (jointures), aucune n'est calculée en Python."""
    where = []
    params = {}
    if campagne_id:
        where.append("s.id_campagne = :campagne_id")
        params['campagne_id'] = campagne_id
    if cooperative_id:
        where.append("s.id_cooperative = :cooperative_id")
        params['cooperative_id'] = cooperative_id
    if variete_id:
        where.append("s.id_variete = :variete_id")
        params['variete_id'] = variete_id
    if q:
        where.append("c.nom_cooperative ILIKE :q")
        params['q'] = f"%{q}%"
    where_sql = ("WHERE " + " AND ".join(where)) if where else ""

    total = db.session.execute(
        text(f"SELECT COUNT(*) {_base_joins()} {where_sql}"), params
    ).scalar() or 0

    page = max(1, page)
    per_page = max(1, per_page)
    offset = (page - 1) * per_page
    rows = db.session.execute(
        text(
            f"SELECT s.id_suivi, ca.id_campagne, ca.annee, c.id_cooperative, c.nom_cooperative, "
            f"v.nom_variete, s.superficie_attribuee, s.superficie_cultivee, "
            f"s.production_kg, s.rendement_ha, s.date_recolte "
            f"{_base_joins()} {where_sql} "
            f"ORDER BY ca.annee DESC, c.nom_cooperative "
            f"LIMIT :limit OFFSET :offset"
        ),
        dict(params, limit=per_page, offset=offset),
    ).mappings().all()

    return rows, total


def get_suivi_detail(id_suivi):
    """Détail complet d'un suivi (toutes les colonnes) + libellés des
    référentiels (campagne, coopérative, variété). None si introuvable."""
    row = db.session.execute(
        text(f"SELECT s.*, ca.annee, c.nom_cooperative, v.nom_variete "
             f"{_base_joins()} WHERE s.id_suivi = :id"),
        {'id': id_suivi},
    ).mappings().first()
    return dict(row) if row else None


def create_suivi(payload):
    suivi = get_table('suivi_campagne')
    stmt = suivi.insert().values(**payload)
    result = db.session.execute(stmt)
    db.session.commit()
    return result.inserted_primary_key[0] if result.inserted_primary_key else None


def update_suivi(id_suivi, payload):
    suivi = get_table('suivi_campagne')
    stmt = suivi.update().where(suivi.c.id_suivi == id_suivi).values(**payload)
    db.session.execute(stmt)
    db.session.commit()


def delete_suivi(id_suivi):
    suivi = get_table('suivi_campagne')
    stmt = suivi.delete().where(suivi.c.id_suivi == id_suivi)
    db.session.execute(stmt)
    db.session.commit()


def count_suivis():
    return db.session.execute(text("SELECT COUNT(*) FROM public.suivi_campagne")).scalar() or 0


def count_cooperatives():
    return db.session.execute(text("SELECT COUNT(*) FROM public.cooperative")).scalar() or 0


def latest_campagne_annee():
    return db.session.execute(text("SELECT MAX(annee) FROM public.campagne")).scalar()
