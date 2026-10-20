# =============================================================================
# services/pdf_service.py — Génération de la fiche PDF d'un suivi
#
# Utilise xhtml2pdf pour convertir le gabarit templates/suivi_pdf.html (une
# page HTML/CSS autonome) en fichier PDF téléchargeable. Le contenu vient
# uniquement des données réelles du suivi (services/suivi_service.py) —
# aucune valeur n'est ajoutée ou inventée ici.
# =============================================================================

import io

from flask import render_template
from xhtml2pdf import pisa


def generate_suivi_pdf(suivi):
    """Construit le PDF de la fiche d'un suivi et renvoie son contenu binaire."""
    html = render_template('suivi_pdf.html', s=suivi)
    buffer = io.BytesIO()
    result = pisa.CreatePDF(src=html, dest=buffer, encoding='utf-8')
    if result.err:
        raise RuntimeError("Échec de la génération du PDF de la fiche de suivi.")
    return buffer.getvalue()
