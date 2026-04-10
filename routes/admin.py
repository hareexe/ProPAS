from flask import Blueprint, abort, flash, redirect, render_template, request, session, url_for
from flask_login import current_user, login_required
from werkzeug.security import generate_password_hash

from models import ApprovalStep, DocumentApproval, DocumentLog, Proposal, User, db

admin_bp = Blueprint('admin', __name__)


def _require_admin():
    if not current_user.is_authenticated or current_user.account_type != 'Admin':
        abort(403)


def _restart_proposal_workflow(proposal):
    steps = ApprovalStep.query.order_by(ApprovalStep.step_order).all()
    if not steps:
        raise ValueError('No approval steps configured.')

    approvals_by_step = {approval.step_id: approval for approval in proposal.approvals}
    for step in steps:
        approval = approvals_by_step.get(step.id)
        if approval is None:
            approval = DocumentApproval(document_id=proposal.id, step_id=step.id)
            db.session.add(approval)

        approval.status = 'pending'
        approval.remarks = None
        approval.approved_at = None
        approval.signed_name = None
        approval.approved_by = None

    proposal.status = 'PENDING'
    proposal.current_step_id = steps[0].id


@admin_bp.route('/admin')
@login_required
def dashboard():
    _require_admin()

    flashes = session.get('_flashes', [])
    if flashes:
        session['_flashes'] = [
            (category, message)
            for category, message in flashes
            if category.startswith('admin-')
        ]
        if not session['_flashes']:
            session.pop('_flashes', None)

    active_tab = request.args.get('tab', 'accounts')
    if active_tab not in {'accounts', 'proposals'}:
        active_tab = 'accounts'

    accounts = User.query.order_by(User.account_type.asc(), User.username.asc()).all()
    proposals = Proposal.query.order_by(Proposal.created_at.desc()).all()
    approval_steps = ApprovalStep.query.order_by(ApprovalStep.step_order).all()
    step_name_map = {step.id: step.name for step in approval_steps}

    return render_template(
        'admin_panel.html',
        accounts=accounts,
        proposals=proposals,
        approval_steps=approval_steps,
        step_name_map=step_name_map,
        active_tab=active_tab,
    )


@admin_bp.route('/admin/accounts/create', methods=['POST'])
@login_required
def create_account():
    _require_admin()

    username = (request.form.get('username') or '').strip()
    password = request.form.get('password') or ''
    account_type = (request.form.get('account_type') or '').strip()

    if not username or not password or account_type not in {'Org', 'Office', 'Admin'}:
        flash('Provide a username, password, and valid account type.', 'admin-danger')
        return redirect(url_for('admin.dashboard', tab='accounts'))

    if User.query.filter_by(username=username).first():
        flash(f"Account '{username}' already exists.", 'admin-warning')
        return redirect(url_for('admin.dashboard', tab='accounts'))

    if account_type == 'Office':
        step = ApprovalStep.query.filter(ApprovalStep.name.ilike(username)).first()
        if not step:
            flash('Office usernames must match an existing approval step exactly.', 'admin-danger')
            return redirect(url_for('admin.dashboard', tab='accounts'))

    new_user = User(
        username=username,
        password_hash=generate_password_hash(password),
        account_type=account_type,
        profile_data={}
    )
    db.session.add(new_user)
    db.session.commit()

    flash(f"Created {account_type} account '{username}'.", 'admin-success')
    return redirect(url_for('admin.dashboard', tab='accounts'))


@admin_bp.route('/admin/accounts/<int:user_id>/reset-password', methods=['POST'])
@login_required
def reset_password(user_id):
    _require_admin()

    user = db.session.get(User, user_id)
    if not user:
        abort(404)

    new_password = request.form.get('new_password') or ''
    if not new_password:
        flash('New password cannot be empty.', 'admin-danger')
        return redirect(url_for('admin.dashboard', tab='accounts'))

    user.password_hash = generate_password_hash(new_password)
    db.session.commit()

    flash(f"Password reset for '{user.username}'.", 'admin-success')
    return redirect(url_for('admin.dashboard', tab='accounts'))


@admin_bp.route('/admin/proposals/<int:proposal_id>/restart', methods=['POST'])
@login_required
def restart_proposal(proposal_id):
    _require_admin()

    proposal = db.session.get(Proposal, proposal_id)
    if not proposal:
        abort(404)

    _restart_proposal_workflow(proposal)
    db.session.add(DocumentLog(
        document_id=proposal.id,
        action='Approval Restarted by Admin',
        performed_by=current_user.id,
        notes=request.form.get('admin_notes') or 'Restarted from admin panel.'
    ))
    db.session.commit()

    flash(f"Approval workflow restarted for proposal '{proposal.title}'.", 'admin-success')
    return redirect(url_for('admin.dashboard', tab='proposals'))
