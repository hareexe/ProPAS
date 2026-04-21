from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, current_user, login_required 
from werkzeug.security import check_password_hash
from models import db, User, Proposal, ApprovalStep, DocumentApproval, ProposalMessage
from utils import normalize_proposal_data, proposal_needs_budget
from storage import storage
auth_bp = Blueprint('auth', __name__)

OFFICE_DISPLAY_NAMES = {
    'VicePresident': 'VP Executive',
}


def _display_step_name(name):
    return OFFICE_DISPLAY_NAMES.get(name, name)


def _home_endpoint_for_user(user):
    if user.account_type == 'Admin':
        return 'admin.dashboard'
    if user.account_type == 'Office':
        return 'office.review'
    return 'proposal.org_home'


def _home_calendar_endpoint_for_user(user):
    if user.account_type == 'Office':
        return 'office.calendar_view'
    return 'proposal.calendar_view'


def _office_step_for_conversation(proposal):
    if proposal.current_step_id:
        current_step = db.session.get(ApprovalStep, proposal.current_step_id)
        if current_step:
            return current_step

    acted_approvals = [approval for approval in proposal.approvals if approval.status in {'approved', 'rejected'}]
    if not acted_approvals:
        return None

    latest_approval = max(
        acted_approvals,
        key=lambda approval: (approval.approved_at or proposal.created_at, approval.id)
    )
    return latest_approval.step


def _office_accounts_for_conversation(proposal):
    office_step = _office_step_for_conversation(proposal)
    if not office_step:
        return [], None

    office_accounts = User.query.filter(
        User.account_type == 'Office',
        User.username.ilike(office_step.name)
    ).all()
    return office_accounts, office_step


def _signed_roles_for_preview(proposal):
    signed_roles = {}
    for approval in proposal.approvals:
        if not approval.step or approval.status != 'approved' or not approval.signed_name:
            continue
        signed_roles[approval.step.name.upper()] = approval.signed_name
    return signed_roles


def _should_use_generated_preview(file_path):
    if not file_path:
        return True

    try:
        pdf_bytes = storage.read_bytes(file_path)
    except Exception:
        return True

    return len(pdf_bytes) < 20_000


def _conversation_messages(proposal_id, office_step_id):
    return ProposalMessage.query.filter_by(
        proposal_id=proposal_id,
        office_step_id=office_step_id,
    ).order_by(ProposalMessage.created_at.asc()).all()

@auth_bp.route('/', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        return redirect(url_for(_home_endpoint_for_user(current_user)))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            return redirect(url_for(_home_endpoint_for_user(user)))
        else:
            flash("Invalid Username or Password", "auth-danger")

    return render_template('signin.html')

@auth_bp.route('/forgot-password')
def forgot_password():
    return render_template('forgot_password.html')


@auth_bp.route('/calendar')
@login_required
def calendar_redirect():
    return redirect(url_for(_home_calendar_endpoint_for_user(current_user)))


@auth_bp.route('/view-status/<int:proposal_id>/messages', methods=['POST'])
@login_required
def send_message(proposal_id):
    if current_user.account_type != 'Org':
        abort(403)

    proposal = Proposal.query.filter_by(id=proposal_id, creator_id=current_user.id).first_or_404()
    body = (request.form.get('message') or '').strip()

    if not body:
        flash('Message cannot be empty.', 'auth-danger')
        return redirect(url_for('auth.view_status', proposal_id=proposal.id, tab='chat'))

    _, office_step = _office_accounts_for_conversation(proposal)

    db.session.add(ProposalMessage(
        proposal_id=proposal.id,
        office_step_id=office_step.id if office_step else None,
        sender_id=current_user.id,
        sender_role=current_user.account_type,
        body=body,
    ))

    db.session.commit()
    flash('Your message was sent to the office thread.', 'auth-success')
    return redirect(url_for('auth.view_status', proposal_id=proposal.id, tab='chat'))

@auth_bp.route('/view-status/<int:proposal_id>')
@login_required
def view_status(proposal_id):
    if current_user.account_type != 'Org':
        abort(403)

    selected_proposal = Proposal.query.filter_by(
        id=proposal_id,
        creator_id=current_user.id
    ).first_or_404()
    active_tab = request.args.get('tab', 'overview')
    if active_tab not in {'overview', 'chat'}:
        active_tab = 'overview'

    proposals = Proposal.query.filter_by(creator_id=current_user.id).order_by(Proposal.created_at.desc()).all()
    pending = Proposal.query.filter_by(creator_id=current_user.id, status='PENDING').count()
    approved = Proposal.query.filter_by(creator_id=current_user.id, status='APPROVED').count()
    rejected = Proposal.query.filter_by(creator_id=current_user.id, status='REJECTED').count()
    office_step = _office_step_for_conversation(selected_proposal)
    messages = _conversation_messages(selected_proposal.id, office_step.id) if office_step else []

    steps = ApprovalStep.query.order_by(ApprovalStep.step_order).all()
    approvals_by_step = {approval.step_id: approval for approval in selected_proposal.approvals}
    needs_budget = proposal_needs_budget(selected_proposal.proposal_data)

    tracker_steps = []
    approved_step_count = 0
    current_office = None
    rejected_office = None
    rejection_remarks = None

    for step in steps:
        step_name = step.name.strip().upper()
        if step_name == 'FINANCE' and not needs_budget:
            tracker_steps.append({
                'name': _display_step_name(step.name),
                'state': 'complete',
                'remarks': 'Skipped because this proposal does not require a budget.',
                'signed_name': None,
                'approved_at': None,
                'status_label': 'Skipped',
            })
            approved_step_count += 1
            continue

        approval = approvals_by_step.get(step.id)
        approval_status = approval.status if approval else 'pending'
        step_label = _display_step_name(step.name)

        if approval_status == 'approved':
            state = 'complete'
            approved_step_count += 1
        elif approval_status == 'rejected':
            state = 'rejected'
            rejected_office = step_label
            rejection_remarks = approval.remarks
        elif selected_proposal.status == 'APPROVED':
            state = 'complete'
        elif selected_proposal.current_step_id == step.id:
            state = 'current'
            current_office = step_label
        else:
            state = 'upcoming'

        tracker_steps.append({
            'name': step_label,
            'state': state,
            'remarks': approval.remarks if approval and approval.remarks else None,
            'signed_name': approval.signed_name if approval and approval.signed_name else None,
            'approved_at': approval.approved_at if approval else None,
            'status_label': 'Approved' if state == 'complete' else ('In Review' if state == 'current' else ('Returned' if state == 'rejected' else 'Waiting')),
        })

    total_steps = len(steps) or 1
    progress_percent = round((approved_step_count / total_steps) * 100)

    if selected_proposal.status == 'APPROVED':
        progress_percent = 100
        status_summary = 'Fully approved by all reviewing offices.'
    elif selected_proposal.status == 'REJECTED':
        status_summary = f"Returned by {rejected_office or 'the reviewing office'}."
    else:
        status_summary = f"Currently under review by {current_office or 'the next office'}."

    proposal_preview_data = normalize_proposal_data(selected_proposal.proposal_data) if selected_proposal else None
    if proposal_preview_data is not None:
        proposal_preview_data = dict(proposal_preview_data)
        proposal_preview_data['signed_roles'] = _signed_roles_for_preview(selected_proposal)
        proposal_preview_data['title'] = selected_proposal.title

    return render_template(
        'org_home.html',
        proposals=proposals,
        selected_proposal=selected_proposal,
        proposal_preview_data=proposal_preview_data,
        tracker_steps=tracker_steps,
        progress_percent=progress_percent,
        status_summary=status_summary,
        current_office=current_office,
        rejected_office=rejected_office,
        rejection_remarks=rejection_remarks,
        pending_count=pending,
        approved_count=approved,
        rejected_count=rejected,
        messages=messages,
        conversation_office=office_step.name if office_step else None,
        active_tab=active_tab,
        use_generated_preview=_should_use_generated_preview(selected_proposal.file_path),
    )

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.signin'))
