# =============================================================================
# routes/admin.py — Espace d'administration (suivis, agents, traçabilité)
#
# Toutes les routes de ce blueprint vivent sous /admin. Chacune est protégée
# individuellement par @login_required (administrateur OU agent) ou
# @role_required('administrateur') (administrateur uniquement) — la
# vérification est faite côté serveur à chaque requête, pas seulement en
# masquant des liens dans l'interface (voir auth.py).
# =============================================================================

from flask import Blueprint, render_template, request, redirect, url_for, flash, session, Response
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash

from extensions import db
from auth import login_required, role_required, get_current_user, log_activite
from models.user import User, ROLE_ADMIN
from models.audit import HistoriqueConnexion, JournalActivite
from services import suivi_service as svc
from services.pdf_service import generate_suivi_pdf

admin_bp = Blueprint('admin', __name__, url_prefix='/admin')


def _friendly_suivi_error(exc):
    """Message d'erreur compréhensible pour l'utilisateur, sans exposer les
    détails techniques de la base de données."""
    if isinstance(exc, IntegrityError) and 'uq_suivi' in str(exc.orig):
        return ("Un suivi existe déjà pour cette combinaison campagne + coopérative. "
                "Modifiez le suivi existant plutôt que d'en créer un nouveau.")
    return "Erreur lors de l'enregistrement du suivi. Vérifiez les valeurs saisies."


# -----------------------------------------------------------------------------
# Vue d'ensemble
# -----------------------------------------------------------------------------

@admin_bp.route('/')
@login_required
def dashboard():
    user = get_current_user()
    kpis = {
        'suivis': svc.count_suivis(),
        'cooperatives': svc.count_cooperatives(),
        'agents_actifs': User.query.filter_by(role='agent', actif=True).count(),
        'derniere_campagne': svc.latest_campagne_annee(),
    }
    return render_template('admin_dashboard.html', kpis=kpis, user=user)


# -----------------------------------------------------------------------------
# Gestion des suivis de campagne (administrateur ET agent)
# -----------------------------------------------------------------------------

@admin_bp.route('/suivis')
@login_required
def suivis_list():
    page = request.args.get('page', 1, type=int)
    campagne_id = request.args.get('campagne_id', type=int)
    cooperative_id = request.args.get('cooperative_id', type=int)
    variete_id = request.args.get('variete_id', type=int)
    q = (request.args.get('q') or '').strip() or None

    rows, total = svc.list_suivis(campagne_id, cooperative_id, variete_id, q, page=page, per_page=20)
    choices = svc.get_form_choices()
    total_pages = max(1, (total + 19) // 20)

    return render_template(
        'suivi_list.html',
        rows=rows, total=total, page=page, total_pages=total_pages,
        campagnes=choices['id_campagne'][1:],
        cooperatives=choices['id_cooperative'][1:],
        varietes=choices['id_variete'][1:],
        filters={'campagne_id': campagne_id, 'cooperative_id': cooperative_id, 'variete_id': variete_id, 'q': q or ''},
    )


@admin_bp.route('/suivis/nouveau', methods=['GET', 'POST'])
@login_required
def suivis_create():
    fields = svc.get_form_fields()

    if request.method == 'POST':
        payload = {field['name']: svc.parse_value(request.form.get(field['name']), field) for field in fields}
        try:
            new_id = svc.create_suivi(payload)
            log_activite('creation_suivi', objet_type='suivi_campagne', objet_id=new_id,
                         details="Ajout d'un suivi de campagne")
            flash('Le suivi a été enregistré avec succès.', 'success')
            return redirect(url_for('admin.suivis_list'))
        except Exception as exc:
            db.session.rollback()
            flash(_friendly_suivi_error(exc), 'danger')
            submitted = {k: request.form.get(k) for k in request.form}
            fields = svc.get_form_fields(submitted)

    sections = svc.group_fields_by_section(fields)
    return render_template('suivi_form.html', sections=sections, mode='create', suivi_id=None)


@admin_bp.route('/suivis/<int:id_suivi>')
@login_required
def suivis_detail(id_suivi):
    detail = svc.get_suivi_detail(id_suivi)
    if not detail:
        flash('Suivi introuvable.', 'danger')
        return redirect(url_for('admin.suivis_list'))
    return render_template('suivi_detail.html', s=detail)


@admin_bp.route('/suivis/<int:id_suivi>/telecharger')
@login_required
def suivis_download(id_suivi):
    detail = svc.get_suivi_detail(id_suivi)
    if not detail:
        flash('Suivi introuvable.', 'danger')
        return redirect(url_for('admin.suivis_list'))

    pdf_bytes = generate_suivi_pdf(detail)
    filename = f"suivi_{detail['nom_cooperative']}_{detail['annee']}_{id_suivi}.pdf".replace(' ', '_')
    return Response(
        pdf_bytes,
        mimetype='application/pdf',
        headers={'Content-Disposition': f'attachment; filename="{filename}"'},
    )


@admin_bp.route('/suivis/<int:id_suivi>/modifier', methods=['GET', 'POST'])
@login_required
def suivis_edit(id_suivi):
    existing = svc.get_suivi_detail(id_suivi)
    if not existing:
        flash('Suivi introuvable.', 'danger')
        return redirect(url_for('admin.suivis_list'))

    if request.method == 'POST':
        fields = svc.get_form_fields()
        payload = {field['name']: svc.parse_value(request.form.get(field['name']), field) for field in fields}
        try:
            svc.update_suivi(id_suivi, payload)
            log_activite('modification_suivi', objet_type='suivi_campagne', objet_id=id_suivi,
                         details=f"Modification du suivi #{id_suivi}")
            flash('Le suivi a été modifié avec succès.', 'success')
            return redirect(url_for('admin.suivis_detail', id_suivi=id_suivi))
        except Exception as exc:
            db.session.rollback()
            flash(_friendly_suivi_error(exc), 'danger')

    fields = svc.get_form_fields(existing)
    sections = svc.group_fields_by_section(fields)
    return render_template('suivi_form.html', sections=sections, mode='edit', suivi_id=id_suivi)


@admin_bp.route('/suivis/<int:id_suivi>/supprimer', methods=['POST'])
@role_required(ROLE_ADMIN)
def suivis_delete(id_suivi):
    existing = svc.get_suivi_detail(id_suivi)
    if not existing:
        flash('Suivi introuvable.', 'danger')
    else:
        svc.delete_suivi(id_suivi)
        log_activite('suppression_suivi', objet_type='suivi_campagne', objet_id=id_suivi,
                     details=f"Suppression du suivi #{id_suivi}")
        flash('Le suivi a été supprimé avec succès.', 'success')
    return redirect(url_for('admin.suivis_list'))


# -----------------------------------------------------------------------------
# Gestion des agents (administrateur uniquement)
# -----------------------------------------------------------------------------

@admin_bp.route('/agents')
@role_required(ROLE_ADMIN)
def agents_list():
    agents = User.query.order_by(User.nom_complet).all()
    return render_template('agents_list.html', agents=agents)


@admin_bp.route('/agents/nouveau', methods=['GET', 'POST'])
@role_required(ROLE_ADMIN)
def agents_create():
    from forms import AgentForm
    form = AgentForm()
    if form.validate_on_submit():
        if User.query.filter_by(nom_utilisateur=form.nom_utilisateur.data).first():
            flash("Ce nom d'utilisateur est déjà utilisé.", 'danger')
        elif not form.password.data:
            flash('Un mot de passe initial est requis.', 'danger')
        else:
            agent = User(
                nom_complet=form.nom_complet.data,
                nom_utilisateur=form.nom_utilisateur.data,
                email=form.email.data or None,
                password_hash=generate_password_hash(form.password.data),
                role=form.role.data,
                actif=form.actif.data,
            )
            db.session.add(agent)
            db.session.commit()
            log_activite('creation_agent', objet_type='users', objet_id=agent.id,
                         details=f"Création du compte {agent.nom_utilisateur}")
            flash('Le compte agent a été créé avec succès.', 'success')
            return redirect(url_for('admin.agents_list'))
    return render_template('agent_form.html', form=form, mode='create', agent=None)


@admin_bp.route('/agents/<int:user_id>')
@role_required(ROLE_ADMIN)
def agents_detail(user_id):
    agent = db.get_or_404(User, user_id)
    connexions = (HistoriqueConnexion.query.filter_by(id_utilisateur=agent.id)
                  .order_by(HistoriqueConnexion.date_heure.desc()).limit(10).all())
    activites = (JournalActivite.query.filter_by(id_utilisateur=agent.id)
                 .order_by(JournalActivite.date_heure.desc()).limit(10).all())
    return render_template('agent_detail.html', agent=agent, connexions=connexions, activites=activites)


@admin_bp.route('/agents/<int:user_id>/modifier', methods=['GET', 'POST'])
@role_required(ROLE_ADMIN)
def agents_edit(user_id):
    from forms import AgentForm
    agent = db.get_or_404(User, user_id)
    form = AgentForm(obj=agent)
    if request.method == 'GET':
        form.password.data = ''
        form.confirm_password.data = ''

    if form.validate_on_submit():
        existing = User.query.filter_by(nom_utilisateur=form.nom_utilisateur.data).first()
        if existing and existing.id != agent.id:
            flash("Ce nom d'utilisateur est déjà utilisé.", 'danger')
        else:
            agent.nom_complet = form.nom_complet.data
            agent.nom_utilisateur = form.nom_utilisateur.data
            agent.email = form.email.data or None
            agent.role = form.role.data
            agent.actif = form.actif.data
            if form.password.data:
                agent.password_hash = generate_password_hash(form.password.data)
            db.session.commit()
            log_activite('modification_compte', objet_type='users', objet_id=agent.id,
                         details=f"Modification du compte {agent.nom_utilisateur}")
            flash('Le compte a été modifié avec succès.', 'success')
            return redirect(url_for('admin.agents_detail', user_id=agent.id))
    return render_template('agent_form.html', form=form, mode='edit', agent=agent)


@admin_bp.route('/agents/<int:user_id>/activer', methods=['POST'])
@role_required(ROLE_ADMIN)
def agents_activate(user_id):
    agent = db.get_or_404(User, user_id)
    agent.actif = True
    db.session.commit()
    log_activite('activation_compte', objet_type='users', objet_id=agent.id,
                 details=f"Activation du compte {agent.nom_utilisateur}")
    flash(f"Le compte de {agent.nom_complet} a été activé.", 'success')
    return redirect(request.referrer or url_for('admin.agents_list'))


@admin_bp.route('/agents/<int:user_id>/desactiver', methods=['POST'])
@role_required(ROLE_ADMIN)
def agents_deactivate(user_id):
    agent = db.get_or_404(User, user_id)
    if agent.id == session.get('user_id'):
        flash('Vous ne pouvez pas désactiver votre propre compte.', 'danger')
        return redirect(request.referrer or url_for('admin.agents_list'))
    agent.actif = False
    db.session.commit()
    log_activite('desactivation_compte', objet_type='users', objet_id=agent.id,
                 details=f"Désactivation du compte {agent.nom_utilisateur}")
    flash(f"Le compte de {agent.nom_complet} a été désactivé.", 'success')
    return redirect(request.referrer or url_for('admin.agents_list'))


@admin_bp.route('/agents/<int:user_id>/reinitialiser-mdp', methods=['POST'])
@role_required(ROLE_ADMIN)
def agents_reset_password(user_id):
    agent = db.get_or_404(User, user_id)
    new_password = (request.form.get('new_password') or '').strip()
    if len(new_password) < 4:
        flash('Le nouveau mot de passe doit contenir au moins 4 caractères.', 'danger')
    else:
        agent.password_hash = generate_password_hash(new_password)
        db.session.commit()
        log_activite('reinitialisation_mdp', objet_type='users', objet_id=agent.id,
                     details=f"Réinitialisation du mot de passe de {agent.nom_utilisateur}")
        flash(f"Le mot de passe de {agent.nom_complet} a été réinitialisé.", 'success')
    return redirect(url_for('admin.agents_detail', user_id=agent.id))


# -----------------------------------------------------------------------------
# Historique des connexions & journal des activités (administrateur uniquement)
# -----------------------------------------------------------------------------

@admin_bp.route('/historique-connexions')
@role_required(ROLE_ADMIN)
def historique():
    page = request.args.get('page', 1, type=int)
    user_id = request.args.get('user_id', type=int)
    type_evenement = request.args.get('type_evenement') or None

    query = HistoriqueConnexion.query
    if user_id:
        query = query.filter_by(id_utilisateur=user_id)
    if type_evenement:
        query = query.filter_by(type_evenement=type_evenement)
    query = query.order_by(HistoriqueConnexion.date_heure.desc())

    per_page = 25
    total = query.count()
    entries = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)

    agents = User.query.order_by(User.nom_complet).all()
    return render_template(
        'historique.html', entries=entries, agents=agents, page=page, total_pages=total_pages,
        filters={'user_id': user_id, 'type_evenement': type_evenement or ''},
    )


@admin_bp.route('/journal-activite')
@role_required(ROLE_ADMIN)
def journal():
    page = request.args.get('page', 1, type=int)
    user_id = request.args.get('user_id', type=int)
    action = request.args.get('action') or None

    query = JournalActivite.query
    if user_id:
        query = query.filter_by(id_utilisateur=user_id)
    if action:
        query = query.filter_by(action=action)
    query = query.order_by(JournalActivite.date_heure.desc())

    per_page = 25
    total = query.count()
    entries = query.offset((page - 1) * per_page).limit(per_page).all()
    total_pages = max(1, (total + per_page - 1) // per_page)

    agents = User.query.order_by(User.nom_complet).all()
    actions = [row[0] for row in db.session.query(JournalActivite.action).distinct().all()]
    return render_template(
        'journal.html', entries=entries, agents=agents, actions=actions, page=page, total_pages=total_pages,
        filters={'user_id': user_id, 'action': action or ''},
    )
