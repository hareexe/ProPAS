from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from models import db, User, Proposal, ApprovalStep, DocumentApproval, Notification, ProposalMessage
from utils import add_signature_page
from utils import build_month_matrix, get_proposal_venue, parse_event_date
from datetime import datetime, date
import calendar
from sqlalchemy.orm.attributes import flag_modified

office_bp = Blueprint('office', __name__)

ORG_DEPARTMENTS = {
    'icons': 'Computer Science Dept',
    'hibe': 'Biology Dept',
    'psych': 'Psychology Dept',
    'kwago': 'Political Science Dept',
    'aces': 'Communication and English Studies',
    'casso': 'CAS',
}

def _get_printed_name(user):
    profile = user.profile_data or {}
    return (profile.get('printed_name') or '').strip()


def _create_notification(recipient_id, proposal_id, title, message, notification_type='info'):
    db.session.add(Notification(
        recipient_id=recipient_id,
        proposal_id=proposal_id,
        title=title,
        message=message,
        notification_type=notification_type,
    ))


def _conversation_messages(proposal_id):
    return ProposalMessage.query.filter_by(proposal_id=proposal_id).order_by(ProposalMessage.created_at.asc()).all()


def _approved_calendar_events():
    events = []
    proposals = Proposal.query.filter_by(status='APPROVED').order_by(Proposal.created_at.desc()).all()
    for proposal in proposals:
        proposal_data = proposal.proposal_data or {}
        event_date = parse_event_date(proposal_data.get('event_date'))
        if not event_date:
            continue

        events.append({
            'proposal_id': proposal.id,
            'title': proposal.title,
            'org_name': proposal.creator.username if proposal.creator else 'Unknown organization',
            'event_date': event_date,
            'date_label': event_date.strftime('%B %d, %Y'),
            'venue': get_proposal_venue(proposal_data),
        })

    return sorted(events, key=lambda item: (item['event_date'], item['title'].lower()))


def _calendar_month_context(events, year, month):
    month_matrix = build_month_matrix(year, month)
    month_name = calendar.month_name[month]
    today = date.today()
    events_by_day = {}
    monthly_events = []

    for event in events:
        if event['event_date'].year == year and event['event_date'].month == month:
            events_by_day.setdefault(event['event_date'].day, []).append(event)
            monthly_events.append(event)

    for day_events in events_by_day.values():
        day_events.sort(key=lambda item: (item['event_date'], item['title'].lower()))

    prev_year, prev_month = (year - 1, 12) if month == 1 else (year, month - 1)
    next_year, next_month = (year + 1, 1) if month == 12 else (year, month + 1)

    return {
        'month_matrix': month_matrix,
        'events_by_day': events_by_day,
        'monthly_events': sorted(monthly_events, key=lambda item: (item['event_date'], item['title'].lower())),
        'month_name': month_name,
        'today': today,
        'prev_year': prev_year,
        'prev_month': prev_month,
        'next_year': next_year,
        'next_month': next_month,
    }


def _notify_next_office_and_org(proposal, approving_step, next_step):
    org_title = 'Proposal Approved'
    if next_step:
        org_message = (
            f"Your proposal '{proposal.title}' was approved by {approving_step.name} "
            f"and is now forwarded to {next_step.name}."
        )
    else:
        org_message = f"Your proposal '{proposal.title}' was approved by {approving_step.name} and is now fully approved."

    _create_notification(
        recipient_id=proposal.creator_id,
        proposal_id=proposal.id,
        title=org_title,
        message=org_message,
        notification_type='success',
    )

    if not next_step:
        return

    office_accounts = User.query.filter(
        User.account_type == 'Office',
        User.username.ilike(next_step.name)
    ).all()

    for office_account in office_accounts:
        _create_notification(
            recipient_id=office_account.id,
            proposal_id=proposal.id,
            title='New Proposal Received',
            message=(
                f"Proposal '{proposal.title}' from {proposal.creator.username} was approved by "
                f"{approving_step.name} and is now in your review queue."
            ),
            notification_type='info',
        )

@office_bp.route('/office-home', methods=['GET', 'POST'])
@office_bp.route('/office-home/<int:review_id>', methods=['GET', 'POST'])
@login_required
def review(review_id=None):
    my_step = ApprovalStep.query.filter(ApprovalStep.name.ilike(current_user.username)).first()
    
    if not my_step:
        flash("Account not linked to a valid approval step.", "danger")
        return redirect(url_for('auth.signin'))

    if request.method == 'POST' and review_id:
        prop = db.session.get(Proposal, review_id)
        if not prop:
            abort(404)

        action = request.form.get('action')
        remarks = request.form.get('remarks')
        printed_name = (request.form.get('printed_name') or _get_printed_name(current_user)).strip()
  
        current_approval = DocumentApproval.query.filter_by(
            document_id=prop.id, 
            step_id=my_step.id
        ).first()

        if action == 'approve':
            if not printed_name:
                flash("Set your printed name first so it can be used as your digital signature.", "warning")
                return redirect(url_for('office.review', review_id=review_id))

            profile = dict(current_user.profile_data or {})
            profile['printed_name'] = printed_name
            current_user.profile_data = profile
         
            success = add_signature_page(
                current_app.config['UPLOAD_FOLDER'], 
                prop.file_path, 
                my_step.name.upper(), 
                printed_name
            )
            
            if success:
                current_approval.signed_name = printed_name
                current_approval.status = 'approved'
                current_approval.remarks = remarks
                current_approval.approved_at = datetime.utcnow()
                current_approval.approved_by = current_user.id

                next_s = ApprovalStep.query.filter(
                    ApprovalStep.step_order > my_step.step_order
                ).order_by(ApprovalStep.step_order.asc()).first()

                if next_s:
                    prop.current_step_id = next_s.id
                else:
                    prop.status = 'APPROVED'
                    prop.current_step_id = None

                _notify_next_office_and_org(prop, my_step, next_s)
                
                flash(f"Proposal '{prop.title}' signed and forwarded.", "success")
            else:
                flash("Failed to generate PDF signature. Please check file permissions.", "danger")

        elif action == 'reject':

            current_approval.status = 'rejected'
            current_approval.remarks = remarks
            prop.status = 'REJECTED'
   
            prop.current_step_id = None 
            flash(f"Proposal '{prop.title}' has been rejected and returned to the organization.", "warning")

        db.session.commit()
        return redirect(url_for('office.review'))
 
    proposals = Proposal.query.filter_by(current_step_id=my_step.id).all()
    notifications = Notification.query.filter_by(recipient_id=current_user.id).order_by(Notification.created_at.desc()).limit(5).all()
    unread_notifications = Notification.query.filter_by(recipient_id=current_user.id, is_read=False).count()
    selected = db.session.get(Proposal, review_id) if review_id else None
    selected_messages = _conversation_messages(selected.id) if selected else []
    active_tab = request.args.get('tab', 'overview')
    if active_tab not in {'overview', 'chat'}:
        active_tab = 'overview'

    return render_template(
        'office_home.html', 
        proposals=proposals, 
        selected_proposal=selected,
        selected_messages=selected_messages,
        active_tab=active_tab,
        username=current_user.username,
        pending_count=len(proposals),
        printed_name=_get_printed_name(current_user),
        notifications=notifications,
        unread_notifications=unread_notifications,
    )

@office_bp.route('/office-profile', methods=['POST'])
@login_required
def update_profile():
    if current_user.account_type != 'Office':
        abort(403)

    printed_name = (request.form.get('printed_name') or '').strip()
    profile = dict(current_user.profile_data or {})
    profile['printed_name'] = printed_name
    current_user.profile_data = profile
    flag_modified(current_user, 'profile_data')
    db.session.add(current_user)
    db.session.commit()

    if printed_name:
        flash("Printed name saved. It will now be used as your digital signature.", "success")
    else:
        flash("Printed name cleared.", "warning")

    return redirect(url_for('office.review'))


@office_bp.route('/proposal-messages/<int:proposal_id>', methods=['POST'])
@login_required
def send_message(proposal_id):
    if current_user.account_type != 'Office':
        abort(403)

    proposal = db.session.get(Proposal, proposal_id)
    if not proposal:
        abort(404)

    body = (request.form.get('message') or '').strip()
    if not body:
        flash('Message cannot be empty.', 'warning')
    else:
        db.session.add(ProposalMessage(
            proposal_id=proposal.id,
            sender_id=current_user.id,
            sender_role=current_user.account_type,
            body=body,
        ))
        _create_notification(
            recipient_id=proposal.creator_id,
            proposal_id=proposal.id,
            title='New Office Message',
            message=f"{current_user.username} sent a message about proposal '{proposal.title}'.",
            notification_type='info',
        )
        db.session.commit()
        flash('Your message was added to the conversation.', 'success')

    return_to = request.form.get('return_to')
    if return_to == 'details':
        return redirect(url_for('office.proposal_details', proposal_id=proposal.id, tab='chat'))
    return redirect(url_for('office.review', review_id=proposal.id, tab='chat'))

# ... existing review function ...

@office_bp.route('/master-history')
@login_required
def master_history():
    """Global history for Office accounts to review all organizations."""
    if current_user.account_type != 'Office':
        abort(403)

    query = Proposal.query.join(User, Proposal.creator_id == User.id).filter(User.account_type == 'Org')

    # Global Search
    search = request.args.get('search')
    if search:
        query = query.filter(Proposal.title.ilike(f'%{search}%'))

    # Filter by specific Organization (Username)
    username_filter = (request.args.get('username_filter') or '').strip()
    if username_filter:
        query = query.filter(User.username.ilike(username_filter))

    # Apply Date Filter
    date_from = request.args.get('date_from')
    if date_from:
        try:
            date_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Proposal.created_at >= date_obj)
        except ValueError:
            pass 

    proposals = query.order_by(Proposal.created_at.desc()).all()
    
    department_options = [
        {'username': 'Icons', 'label': 'Icons - Computer Science Dept'},
        {'username': 'Hibe', 'label': 'Hibe - Biology Dept'},
        {'username': 'Psych', 'label': 'Psych - Psychology Dept'},
        {'username': 'Kwago', 'label': 'Kwago - Political Science Dept'},
        {'username': 'Aces', 'label': 'Aces - Communication and English Studies'},
        {'username': 'Casso', 'label': 'Casso - CAS'},
    ]

    return render_template(
        'submission_history.html',
        proposals=proposals,
        is_history=True,
        is_office=True,
        department_options=department_options,
        department_map=ORG_DEPARTMENTS
    )


@office_bp.route('/calendar')
@login_required
def calendar_view():
    if current_user.account_type != 'Office':
        abort(403)

    today = date.today()
    year = request.args.get('year', type=int) or today.year
    month = request.args.get('month', type=int) or today.month

    if month < 1 or month > 12:
        month = today.month
    if year < 2000 or year > 2100:
        year = today.year

    events = _approved_calendar_events()
    calendar_context = _calendar_month_context(events, year, month)

    return render_template(
        'calendar.html',
        page_title='Calendar of Activities',
        page_subtitle='Browse approved activities across organizations and reviewing offices.',
        account_sub='Office',
        dashboard_endpoint='office.review',
        history_endpoint='office.master_history',
        calendar_endpoint='office.calendar_view',
        review_endpoint='office.review',
        **calendar_context,
    )

@office_bp.route('/proposal-details/<int:proposal_id>')
@login_required
def proposal_details(proposal_id):
    """Detailed PDF viewer for office accounts."""
    if current_user.account_type != 'Office':
        abort(403)

    proposal = db.session.get(Proposal, proposal_id)
    if not proposal:
        abort(404)

    current_step_name = None
    if proposal.current_step_id:
        current_step = db.session.get(ApprovalStep, proposal.current_step_id)
        current_step_name = current_step.name if current_step else None
    messages = _conversation_messages(proposal.id)
    active_tab = request.args.get('tab', 'overview')
    if active_tab not in {'overview', 'chat'}:
        active_tab = 'overview'

    return render_template(
        'office_proposal_detail.html',
        proposal=proposal,
        department_name=ORG_DEPARTMENTS.get(proposal.creator.username.lower(), proposal.creator.username),
        current_step_name=current_step_name,
        messages=messages,
        active_tab=active_tab
    )
