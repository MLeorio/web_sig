# =============================================================================
# dashboard_service.py — Agrégats et commentaires du tableau de bord
#
# Ce module calcule, pour chaque graphique de la page /dashboard, les valeurs
# par coopérative (via `_agg_by_coop` / `_sum_two_cols`) ainsi qu'un court
# commentaire textuel en français mettant en avant la coopérative la plus
# performante et la moins performante sur l'indicateur concerné.
#
# Chaque graphique du dashboard a son propre style de phrase (verbe, unité,
# présence ou non d'une "différence") : les fonctions `_comment_*` ci-dessous
# correspondent chacune à un numéro de graphique affiché dans dashboard.html.
# =============================================================================

from flask import current_app
from sqlalchemy import text


def list_campaigns():
    """Return list of campaigns as dicts {id, annee} ordered by annee desc."""
    engine = current_app.extensions['sqlalchemy'].db.engine
    q = text("SELECT id_campagne, annee FROM public.campagne ORDER BY annee DESC")
    with engine.connect() as conn:
        rows = conn.execute(q).all()
        return [{'id': r[0], 'annee': r[1]} for r in rows]


def _agg_by_coop(campagne_id, column):
    engine = current_app.extensions['sqlalchemy'].db.engine
    with engine.connect() as conn:
        if campagne_id is None:
            q = text(f"SELECT c.id_cooperative, c.nom_cooperative, COALESCE(SUM(s.{column}),0) as val "
                     "FROM public.cooperative c "
                     "LEFT JOIN public.suivi_campagne s ON s.id_cooperative = c.id_cooperative "
                     "GROUP BY c.id_cooperative, c.nom_cooperative ORDER BY c.nom_cooperative")
            rows = conn.execute(q).all()
        else:
            q = text(f"SELECT c.id_cooperative, c.nom_cooperative, COALESCE(SUM(s.{column}),0) as val "
                     "FROM public.cooperative c "
                     "LEFT JOIN public.suivi_campagne s ON s.id_cooperative = c.id_cooperative "
                     "AND s.id_campagne = :campagne_id "
                     "GROUP BY c.id_cooperative, c.nom_cooperative ORDER BY c.nom_cooperative")
            rows = conn.execute(q, {'campagne_id': campagne_id}).all()
        return [{'id': r[0], 'coop': r[1], 'value': float(r[2]) if r[2] is not None else 0.0} for r in rows]


def _sum_two_cols(campagne_id, col1, col2):
    engine = current_app.extensions['sqlalchemy'].db.engine
    with engine.connect() as conn:
        if campagne_id is None:
            q = text(f"SELECT c.id_cooperative, c.nom_cooperative, COALESCE(SUM(s.{col1}),0) as v1, COALESCE(SUM(s.{col2}),0) as v2 "
                     "FROM public.cooperative c "
                     "LEFT JOIN public.suivi_campagne s ON s.id_cooperative = c.id_cooperative "
                     "GROUP BY c.id_cooperative, c.nom_cooperative ORDER BY c.nom_cooperative")
            rows = conn.execute(q).all()
        else:
            q = text(f"SELECT c.id_cooperative, c.nom_cooperative, COALESCE(SUM(s.{col1}),0) as v1, COALESCE(SUM(s.{col2}),0) as v2 "
                     "FROM public.cooperative c "
                     "LEFT JOIN public.suivi_campagne s ON s.id_cooperative = c.id_cooperative "
                     "AND s.id_campagne = :campagne_id "
                     "GROUP BY c.id_cooperative, c.nom_cooperative ORDER BY c.nom_cooperative")
            rows = conn.execute(q, {'campagne_id': campagne_id}).all()
        return [{'id': r[0], 'coop': r[1], 'v1': float(r[2]) if r[2] is not None else 0.0, 'v2': float(r[3]) if r[3] is not None else 0.0} for r in rows]


def _varieties_by_coop(campagne_id):
    """Nombre de suivis par variété cultivée, groupés par coopérative.

    La valeur 'Aucune' n'est pas une variété : elle signifie qu'aucune culture
    n'a été renseignée pour ce suivi. On l'exclut donc pour ne pas fausser le
    diagramme en camembert des variétés (graphique 12)."""
    engine = current_app.extensions['sqlalchemy'].db.engine
    with engine.connect() as conn:
        if campagne_id is None:
            q = text("SELECT c.nom_cooperative, v.nom_variete, COUNT(*) as cnt "
                     "FROM public.suivi_campagne s "
                     "JOIN public.cooperative c ON s.id_cooperative = c.id_cooperative "
                     "JOIN public.variete v ON s.id_variete = v.id_variete "
                     "WHERE lower(trim(v.nom_variete)) <> 'aucune' "
                     "GROUP BY c.nom_cooperative, v.nom_variete ORDER BY c.nom_cooperative, v.nom_variete")
            rows = conn.execute(q).all()
        else:
            q = text("SELECT c.nom_cooperative, v.nom_variete, COUNT(*) as cnt "
                     "FROM public.suivi_campagne s "
                     "JOIN public.cooperative c ON s.id_cooperative = c.id_cooperative "
                     "JOIN public.variete v ON s.id_variete = v.id_variete "
                     "WHERE s.id_campagne = :campagne_id AND lower(trim(v.nom_variete)) <> 'aucune' "
                     "GROUP BY c.nom_cooperative, v.nom_variete ORDER BY c.nom_cooperative, v.nom_variete")
            rows = conn.execute(q, {'campagne_id': campagne_id}).all()
        out = {}
        for coop, variete, cnt in rows:
            out.setdefault(coop, []).append({'variete': variete, 'count': int(cnt)})
        return out


# -----------------------------------------------------------------------------
# Mise en forme des nombres et sélection des valeurs extrêmes
# -----------------------------------------------------------------------------

def _fmt_number(value, decimals=2):
    """Formate un nombre à la française : virgule décimale, espace comme
    séparateur de milliers, et pas de décimales inutiles.

    Exemples : 100 -> "100" ; 54.36 -> "54,36" ; 1250 -> "1 250" ; -0.02 -> "-0,02"
    """
    value = float(value)
    rounded = round(value, decimals)
    negative = rounded < 0
    abs_rounded = abs(rounded)

    if abs_rounded == int(abs_rounded):
        text_value = f"{int(abs_rounded):,}".replace(",", " ")
    else:
        raw = f"{abs_rounded:,.{decimals}f}"
        int_part, dec_part = raw.split(".")
        dec_part = dec_part.rstrip("0") or "0"
        text_value = f"{int_part.replace(',', ' ')},{dec_part}"

    return f"-{text_value}" if negative else text_value


def _rank_extremes(items):
    """Parmi une liste de {'coop', 'value'}, retourne (coop_max, valeur_max)
    et (coop_min, valeur_min), en ignorant les valeurs manquantes ou nulles
    (une valeur à 0 signifie généralement qu'aucun suivi n'existe pour cette
    coopérative sur la campagne, pas une vraie mesure à 0).
    Retourne (None, None) si aucune valeur exploitable n'est disponible."""
    vals = [
        (it['coop'], float(it['value']))
        for it in items
        if it.get('value') not in (None, 0)
    ]
    if not vals:
        return None, None
    return max(vals, key=lambda x: x[1]), min(vals, key=lambda x: x[1])


def _comment_for_series(campagne_annee_label, metric_label, items, unit=''):
    """Commentaire générique utilisé pour les graphiques 1, 2 et 4 (superficie
    attribuée, superficie cultivée, production) : indicateurs simples pour
    lesquels une phrase neutre "plus élevé / plus faible" suffit."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {campagne_annee_label}."

    unit_text = f" {unit}" if unit else ""
    comment = (
        f"Pour la campagne {campagne_annee_label}, la coopérative {highest[0]} présente la {metric_label} la plus élevée,"
        f" avec {_fmt_number(highest[1])}{unit_text}."
    )
    if lowest[0] != highest[0]:
        diff = highest[1] - lowest[1]
        comment += f" La coopérative {lowest[0]} affiche la valeur la plus faible, avec {_fmt_number(lowest[1])}{unit_text} (différence de {_fmt_number(diff)})."
    return comment


# -----------------------------------------------------------------------------
# Commentaires spécifiques par graphique (2 -> voir _comment_for_series ci-dessus)
# -----------------------------------------------------------------------------

def _comment_utilisation(annee, items):
    """Graphique 3 : taux d'utilisation de la superficie attribuée (%)."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    comment = (
        f"Pour la campagne {annee}, la coopérative {highest[0]} utilise {_fmt_number(highest[1])} % "
        "de la superficie attribuée, ce qui représente la valeur la plus élevée."
    )
    if lowest[0] != highest[0]:
        comment += f" À l'inverse, la coopérative {lowest[0]} n'exploite que {_fmt_number(lowest[1])} %."
    return comment


def _comment_effectifs(annee, eff_items):
    """Graphique 5 : effectifs totaux (hommes + femmes) par coopérative."""
    totals = [{'coop': e['coop'], 'value': e['v1'] + e['v2'], 'femmes': e['v2']} for e in eff_items]
    highest, lowest = _rank_extremes(totals)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    femmes_high = next(t['femmes'] for t in totals if t['coop'] == highest[0])
    comment = (
        f"En {annee}, la coopérative {highest[0]} compte l'effectif le plus important avec "
        f"{_fmt_number(highest[1], 0)} personnes dont {_fmt_number(femmes_high, 0)} femmes."
    )
    if lowest[0] != highest[0]:
        femmes_low = next(t['femmes'] for t in totals if t['coop'] == lowest[0])
        comment += (
            f" La coopérative {lowest[0]} enregistre le plus faible effectif avec seulement "
            f"{_fmt_number(lowest[1], 0)} personnes dont {_fmt_number(femmes_low, 0)} femmes."
        )
    return comment


def _comment_npk(annee, items):
    """Graphique 6 : quantité de NPK (kg)."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    comment = (
        f"Durant la campagne {annee}, la coopérative {highest[0]} utilise la plus grande quantité de NPK, "
        f"soit {_fmt_number(highest[1])} kg."
    )
    if lowest[0] != highest[0]:
        diff = highest[1] - lowest[1]
        comment += (
            f" La coopérative {lowest[0]} en consomme seulement {_fmt_number(lowest[1])} kg, "
            f"ce qui représente une différence de {_fmt_number(diff)} kg."
        )
    return comment


def _comment_uree(annee, items):
    """Graphique 7 : quantité d'urée (kg)."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    comment = (
        f"Pour la campagne {annee}, la coopérative {highest[0]} applique la quantité d'urée la plus élevée "
        f"avec {_fmt_number(highest[1])} kg."
    )
    if lowest[0] != highest[0]:
        diff = highest[1] - lowest[1]
        comment += (
            f" La coopérative {lowest[0]} n'en utilise que {_fmt_number(lowest[1])} kg, "
            f"soit une différence de {_fmt_number(diff)} kg."
        )
    return comment


def _comment_herbicide(annee, items):
    """Graphique 8 : quantité d'herbicide (L)."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    comment = (
        f"En {annee}, la coopérative {highest[0]} enregistre la consommation d'herbicide la plus élevée "
        f"avec {_fmt_number(highest[1])} L."
    )
    if lowest[0] != highest[0]:
        diff = highest[1] - lowest[1]
        comment += (
            f" La coopérative {lowest[0]} n'en utilise que {_fmt_number(lowest[1])} L, "
            f"soit une différence de {_fmt_number(diff)} L."
        )
    return comment


def _comment_insecticide(annee, items):
    """Graphique 9 : quantité d'insecticide (L)."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    comment = (
        f"Pour la campagne {annee}, la coopérative {highest[0]} consomme la plus grande quantité d'insecticide "
        f"avec {_fmt_number(highest[1])} L."
    )
    if lowest[0] != highest[0]:
        diff = highest[1] - lowest[1]
        comment += (
            f" La coopérative {lowest[0]} affiche la valeur la plus faible avec {_fmt_number(lowest[1])} L, "
            f"soit une différence de {_fmt_number(diff)} L."
        )
    return comment


def _comment_production_ecoulee(annee, items):
    """Graphique 10 : production écoulée (kg)."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    comment = (
        f"Durant la campagne {annee}, la coopérative {highest[0]} a écoulé la plus grande quantité de "
        f"production, avec {_fmt_number(highest[1])} kg."
    )
    if lowest[0] != highest[0]:
        comment += f" La coopérative {lowest[0]} n'en a écoulé que {_fmt_number(lowest[1])} kg."
    return comment


def _comment_production_restante(annee, items):
    """Graphique 11 : production restante, non encore écoulée (kg)."""
    highest, lowest = _rank_extremes(items)
    if not highest:
        return f"Données insuffisantes pour établir un commentaire sur la campagne {annee}."

    comment = (
        f"En {annee}, la coopérative {highest[0]} conserve la plus grande quantité de production non écoulée "
        f"avec {_fmt_number(highest[1])} kg."
    )
    if lowest[0] != highest[0]:
        diff = highest[1] - lowest[1]
        comment += (
            f" La coopérative {lowest[0]} affiche la valeur la plus faible avec {_fmt_number(lowest[1])} kg, "
            f"soit une différence de {_fmt_number(diff)} kg."
        )
    return comment


# -----------------------------------------------------------------------------
# Point d'entrée : agrège tous les graphiques du dashboard pour une campagne
# -----------------------------------------------------------------------------

def fetch_dashboard_for_campaign(campagne_id):
    """Return aggregated metrics for the dashboard filtered by campagne_id (or None for all)."""
    engine = current_app.extensions['sqlalchemy'].db.engine

    # get campaign label for comments
    camp_label = None
    if campagne_id:
        with engine.connect() as conn:
            r = conn.execute(text("SELECT annee FROM public.campagne WHERE id_campagne = :id"), {'id': campagne_id}).fetchone()
            camp_label = r[0] if r else str(campagne_id)
    else:
        camp_label = 'toutes'

    result = {}

    # 1. superficie_attribuee (bar)
    sup_attr = _agg_by_coop(campagne_id, 'superficie_attribuee')
    result['superficie_attribuee'] = {'items': sup_attr, 'unit': 'ha', 'comment': _comment_for_series(camp_label, 'superficie attribuée', sup_attr, 'ha')}

    # 2. superficie_cultivee (bar)
    sup_cult = _agg_by_coop(campagne_id, 'superficie_cultivee')
    result['superficie_cultivee'] = {'items': sup_cult, 'unit': 'ha', 'comment': _comment_for_series(camp_label, 'superficie cultivée', sup_cult, 'ha')}

    # 3. taux d'utilisation de la superficie attribuée
    use_items = []
    for s_attr in sup_attr:
        s_cult = next((item for item in sup_cult if item['id'] == s_attr['id']), {'value': 0.0})
        value = 0.0
        if float(s_attr['value'] or 0) != 0:
            value = (float(s_cult.get('value', 0.0)) / float(s_attr['value'])) * 100
        use_items.append({'id': s_attr['id'], 'coop': s_attr['coop'], 'value': value})
    result['superficie_utilisation'] = {
        'items': use_items,
        'unit': '%',
        'comment': _comment_utilisation(camp_label, use_items)
    }

    # 4. production_kg
    prod = _agg_by_coop(campagne_id, 'production_kg')
    result['production_kg'] = {'items': prod, 'unit': 'kg', 'comment': _comment_for_series(camp_label, 'production', prod, 'kg')}

    # 5. effectif hommes/femmes
    eff = _sum_two_cols(campagne_id, 'effectif_hommes', 'effectif_femmes')
    result['effectifs'] = {'items': eff, 'comment': _comment_effectifs(camp_label, eff)}

    # 6. qte_npk
    qte_npk = _agg_by_coop(campagne_id, 'qte_npk')
    result['qte_npk'] = {'items': qte_npk, 'unit': 'kg', 'comment': _comment_npk(camp_label, qte_npk)}

    # 7. qte_uree
    qte_uree = _agg_by_coop(campagne_id, 'qte_uree')
    result['qte_uree'] = {'items': qte_uree, 'unit': 'kg', 'comment': _comment_uree(camp_label, qte_uree)}

    # 8. qte_herbicide
    qte_herb = _agg_by_coop(campagne_id, 'qte_herbicide')
    result['qte_herbicide'] = {'items': qte_herb, 'unit': 'L', 'comment': _comment_herbicide(camp_label, qte_herb)}

    # 9. qte_insecticide
    qte_insec = _agg_by_coop(campagne_id, 'qte_insecticide')
    result['qte_insecticide'] = {'items': qte_insec, 'unit': 'L', 'comment': _comment_insecticide(camp_label, qte_insec)}

    # 10. production_ecoulee
    prod_ec = _agg_by_coop(campagne_id, 'production_ecoulee')
    result['production_ecoulee'] = {'items': prod_ec, 'unit': 'kg', 'comment': _comment_production_ecoulee(camp_label, prod_ec)}

    # 11. production_restante
    prod_rest = _agg_by_coop(campagne_id, 'production_restante')
    result['production_restante'] = {'items': prod_rest, 'unit': 'kg', 'comment': _comment_production_restante(camp_label, prod_rest)}

    # 12. variétés par coopérative (camembert) — la valeur "Aucune" est déjà
    # exclue par _varieties_by_coop() car ce n'est pas une variété cultivée.
    var_by_coop = _varieties_by_coop(campagne_id)
    result['varietes'] = {'by_coop': var_by_coop}

    return result
