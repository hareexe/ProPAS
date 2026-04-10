from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_user, logout_user, current_user, login_required 
from werkzeug.security import check_password_hash
from models import User, Proposal, ApprovalStep
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

@auth_bp.route('/view-status/<int:proposal_id>')
@login_required
def view_status(proposal_id):
    if current_user.account_type != 'Org':
        abort(403)

    selected_proposal = Proposal.query.filter_by(
        id=proposal_id,
        creator_id=current_user.id
    ).first_or_404()

    proposals = Proposal.query.filter_by(creator_id=current_user.id).order_by(Proposal.created_at.desc()).all()
    pending = Proposal.query.filter_by(creator_id=current_user.id, status='PENDING').count()
    approved = Proposal.query.filter_by(creator_id=current_user.id, status='APPROVED').count()
    rejected = Proposal.query.filter_by(creator_id=current_user.id, status='REJECTED').count()

    steps = ApprovalStep.query.order_by(ApprovalStep.step_order).all()
    approvals_by_step = {approval.step_id: approval for approval in selected_proposal.approvals}

    tracker_steps = []
    approved_step_count = 0
    current_office = None
    rejected_office = None
    rejection_remarks = None

    for step in steps:
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

    return render_template(
        'org_home.html',
        proposals=proposals,
        selected_proposal=selected_proposal,
        tracker_steps=tracker_steps,
        progress_percent=progress_percent,
        status_summary=status_summary,
        current_office=current_office,
        rejected_office=rejected_office,
        rejection_remarks=rejection_remarks,
        pending_count=pending,
        approved_count=approved,
        rejected_count=rejected
    )

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.signin'))
