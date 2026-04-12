import os
import re
import json
import calendar
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime, date
from werkzeug.utils import secure_filename
from models import db, Proposal, ApprovalStep, DocumentApproval, DocumentLog
from utils import build_month_matrix, get_proposal_venue, normalize_proposal_data, parse_event_date

# Define the Blueprint - Only for Organization/Student tasks
proposal_bp = Blueprint('proposal', __name__)

VENUE_OPTIONS = [
    'Student Center',
    'New Media Hall',
    'Old Media Hall',
    'Worship Center',
    'Freedom Park',
    'International House',
    'Oval',
    'Others',
]

SDG_OPTIONS = [
    {'value': 'SDG 1: No Poverty', 'label': 'SDG 1: No Poverty'},
    {'value': 'SDG 2: Zero Hunger', 'label': 'SDG 2: Zero Hunger'},
    {'value': 'SDG 3: Good Health and Well-Being', 'label': 'SDG 3: Good Health and Well-Being'},
    {'value': 'SDG 4: Quality Education', 'label': 'SDG 4: Quality Education'},
    {'value': 'SDG 5: Gender Equality', 'label': 'SDG 5: Gender Equality'},
    {'value': 'SDG 6: Clean Water and Sanitation', 'label': 'SDG 6: Clean Water and Sanitation'},
    {'value': 'SDG 8: Decent Work and Economic Growth', 'label': 'SDG 8: Decent Work and Economic Growth'},
    {'value': 'SDG 9: Industry, Innovation and Infrastructure', 'label': 'SDG 9: Industry, Innovation and Infrastructure'},
    {'value': 'SDG 10: Reduced Inequalities', 'label': 'SDG 10: Reduced Inequalities'},
    {'value': 'SDG 11: Sustainable Cities and Communities', 'label': 'SDG 11: Sustainable Cities and Communities'},
    {'value': 'SDG 13: Climate Action', 'label': 'SDG 13: Climate Action'},
    {'value': 'SDG 16: Peace, Justice and Strong Institutions', 'label': 'SDG 16: Peace, Justice and Strong Institutions'},
    {'value': 'SDG 17: Partnerships for the Goals', 'label': 'SDG 17: Partnerships for the Goals'},
]

REQUIRED_PROPOSAL_FIELDS = {
    'title': 'Project title',
    'sponsor': 'Sponsor / organization',
    'event_date': 'Event date',
    'venue': 'Venue',
    'participation': 'Target participants',
    'rationale': 'Background / rationale',
    'approach_list': 'Approach / process',
    'objectives_list': 'Objectives',
    'expected_outcome': 'Expected outcomes',
    'funding_source': 'Source of funding',
    'signatory_ProjPresident': 'Org president / project coordinator',
    'signatory_adviser': 'Person in-charge / adviser',
    'signatory_dept_head': 'Department / program head',
}


def _require_org_account():
    if current_user.account_type == 'Admin':
        return redirect(url_for('admin.dashboard'))
    if current_user.account_type == 'Office':
        return redirect(url_for('office.review'))
    if current_user.account_type != 'Org':
        abort(403)
    return None

def _proposal_prefix(username):
    safe_username = secure_filename(username or "Org").replace("_", "")
    return f"{safe_username}Proposal"

def _extract_proposal_sequence(filename, username):
    if not filename:
        return None

    prefix = re.escape(_proposal_prefix(username))
    match = re.match(rf"^{prefix}(\d+)(?:_v\d+)?\.pdf$", filename, re.IGNORECASE)
    return int(match.group(1)) if match else None

def _fallback_proposal_sequence(proposal):
    return Proposal.query.filter(
        Proposal.creator_id == proposal.creator_id,
        Proposal.id <= proposal.id
    ).count()

def _next_proposal_sequence(user_id, username):
    highest_sequence = 0
    proposals = Proposal.query.filter_by(creator_id=user_id).all()

    for proposal in proposals:
        sequence = _extract_proposal_sequence(proposal.file_path, username)
        if sequence:
            highest_sequence = max(highest_sequence, sequence)

    return highest_sequence + 1

def _build_proposal_filename(username, sequence, version=None):
    base_name = f"{_proposal_prefix(username)}{sequence}"
    if version and version > 1:
        base_name = f"{base_name}_v{version}"
    return f"{base_name}.pdf"


def _resume_step_for_resubmission(proposal, steps):
    approvals_by_step = {approval.step_id: approval for approval in proposal.approvals}

    for step in steps:
        approval = approvals_by_step.get(step.id)
        if not approval or approval.status != 'approved':
            return step

    return None


def _reset_proposal_for_resubmission(proposal):
    steps = ApprovalStep.query.order_by(ApprovalStep.step_order.asc()).all()
    approvals_by_step = {approval.step_id: approval for approval in proposal.approvals}

    for step in steps:
        if step.id in approvals_by_step:
            continue
        approval = DocumentApproval(document_id=proposal.id, step_id=step.id, status='pending')
        db.session.add(approval)
        proposal.approvals.append(approval)
        approvals_by_step[step.id] = approval

    resume_step = _resume_step_for_resubmission(proposal, steps)
    resume_order = resume_step.step_order if resume_step else None

    for approval in proposal.approvals:
        step_order = approval.step.step_order if approval.step else None
        if (
            resume_order is not None
            and step_order is not None
            and step_order < resume_order
            and approval.status == 'approved'
        ):
            continue

        approval.status = 'pending'
        approval.remarks = None
        approval.approved_at = None
        approval.signed_name = None
        approval.approved_by = None

    proposal.status = 'PENDING'
    proposal.current_step_id = resume_step.id if resume_step else None


def _split_legacy_date_venue(value):
    if not value:
        return '', '', ''

    for separator in ('|', ' / ', '/', ' — ', ' – '):
        if separator in value:
            event_date, venue = [part.strip() for part in value.split(separator, 1)]
            break
    else:
        return value.strip(), '', ''

    if venue in VENUE_OPTIONS[:-1]:
        return event_date, venue, ''

    return event_date, 'Others', venue


def _normalize_proposal_form_data(form_data):
    if hasattr(form_data, 'to_dict'):
        normalized = form_data.to_dict()
        unsdg_goals = [value.strip() for value in form_data.getlist('unsdg_goals') if value.strip()]
    else:
        normalized = normalize_proposal_data(form_data)
        raw_unsdg_goals = normalized.get('unsdg_goals', [])
        if isinstance(raw_unsdg_goals, list):
            unsdg_goals = [value.strip() for value in raw_unsdg_goals if isinstance(value, str) and value.strip()]
        elif isinstance(raw_unsdg_goals, str) and raw_unsdg_goals.strip():
            unsdg_goals = [raw_unsdg_goals.strip()]
        else:
            unsdg_goals = []

    event_date = (normalized.get('event_date') or '').strip()
    venue = (normalized.get('venue') or '').strip()
    venue_other = (normalized.get('venue_other') or '').strip()

    if not (event_date or venue or venue_other):
        legacy_date_venue = (normalized.get('date_venue') or '').strip()
        split_date, split_venue, split_other = _split_legacy_date_venue(legacy_date_venue)
        normalized['event_date'] = split_date
        normalized['venue'] = split_venue
        normalized['venue_other'] = split_other
    else:
        normalized['event_date'] = event_date
        normalized['venue'] = venue
        normalized['venue_other'] = venue_other if venue == 'Others' else ''

    legacy_unsdg = normalized.get('unsdg')
    if not unsdg_goals and isinstance(legacy_unsdg, str) and legacy_unsdg.strip():
        unsdg_goals = [value.strip() for value in legacy_unsdg.splitlines() if value.strip()]

    normalized['unsdg_goals'] = unsdg_goals
    normalized['unsdg'] = ', '.join(unsdg_goals)

    return normalized


def _extract_budget_items(form_data):
    raw_budget_items = ''
    if hasattr(form_data, 'get'):
        raw_budget_items = form_data.get('budget_items', '')
    elif isinstance(form_data, dict):
        raw_budget_items = form_data.get('budget_items', '')

    if not raw_budget_items:
        return []

    try:
        items = json.loads(raw_budget_items)
    except (TypeError, json.JSONDecodeError):
        return []

    if not isinstance(items, list):
        return []

    normalized_items = []
    for item in items:
        if not isinstance(item, dict):
            continue
        description = str(item.get('description') or '').strip()
        quantity = float(item.get('quantity') or 0)
        unit_cost = float(item.get('unit_cost') or 0)
        normalized_items.append({
            'description': description,
            'quantity': quantity,
            'unit_cost': unit_cost,
            'amount': quantity * unit_cost,
        })
    return normalized_items


def _validate_proposal_payload(form_data, file_storage=None):
    normalized_data = _normalize_proposal_form_data(form_data)
    budget_items = _extract_budget_items(form_data)

    for field_name, label in REQUIRED_PROPOSAL_FIELDS.items():
        value = (form_data.get(field_name) or '').strip()
        if not value:
            return None, f'{label} is required.'

    if normalized_data.get('venue') == 'Others' and not normalized_data.get('venue_other'):
        return None, 'Please specify the other venue.'

    if not normalized_data.get('unsdg_goals'):
        return None, 'Select at least one UNSDG target.'

    budget_value = (form_data.get('budget') or '').strip()
    try:
        budget_amount = float(budget_value)
    except ValueError:
        return None, 'Proposed budget must be a valid amount.'

    if budget_amount <= 0:
        return None, 'Proposed budget must be greater than zero.'

    if not budget_items:
        return None, 'Add at least one budget item.'

    for item in budget_items:
        if not item['description']:
            return None, 'Every budget item needs a description.'
        if item['quantity'] <= 0:
            return None, 'Every budget item quantity must be greater than zero.'
        if item['unit_cost'] < 0:
            return None, 'Budget item unit cost cannot be negative.'

    if file_storage is not None and (not file_storage or file_storage.filename == ''):
        return None, 'Proposal PDF generation failed. Please try again.'

    normalized_data['budget'] = budget_amount
    normalized_data['budget_items'] = budget_items
    return normalized_data, None


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


def _approved_calendar_events():
    events = []
    proposals = Proposal.query.filter_by(status='APPROVED').order_by(Proposal.created_at.desc()).all()

    for proposal in proposals:
        proposal_data = _normalize_proposal_form_data(proposal.proposal_data or {})
        event_date = parse_event_date(proposal_data.get('event_date'))
        if not event_date:
            continue

        venue = get_proposal_venue(proposal_data)
        events.append({
            'proposal_id': proposal.id,
            'title': proposal.title,
            'org_name': proposal.creator.username if proposal.creator else 'Unknown organization',
            'event_date': event_date,
            'date_label': event_date.strftime('%B %d, %Y'),
            'venue': venue,
        })

    return sorted(events, key=lambda item: (item['event_date'], item['title'].lower()))

@proposal_bp.route('/org-home')
@login_required
def org_home():
    """Main dashboard for Organizations to see a summary of their work."""
    redirect_response = _require_org_account()
    if redirect_response:
        return redirect_response

    proposals = Proposal.query.filter_by(creator_id=current_user.id).all()
    
    # Statistics for dashboard cards
    pending = Proposal.query.filter_by(creator_id=current_user.id, status='PENDING').count()
    rejected = Proposal.query.filter_by(creator_id=current_user.id, status='REJECTED').count()
    approved = Proposal.query.filter_by(creator_id=current_user.id, status='APPROVED').count()
    
    return render_template(
        'org_home.html', 
        proposals=proposals, 
        pending_count=pending, 
        rejected_count=rejected, 
        approved_count=approved,
    )


@proposal_bp.route('/org-calendar')
@login_required
def calendar_view():
    redirect_response = _require_org_account()
    if redirect_response:
        return redirect_response

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
        page_subtitle='Track approved activities by date, venue, and organization.',
        account_sub='Org',
        dashboard_endpoint='proposal.org_home',
        history_endpoint='proposal.history',
        calendar_endpoint='proposal.calendar_view',
        review_endpoint=None,
        **calendar_context,
    )

@proposal_bp.route('/create-proposal', methods=['GET', 'POST'])
@login_required
def create():
    """Handles creating new proposals and editing rejected ones."""
    redirect_response = _require_org_account()
    if redirect_response:
        return redirect_response

    edit_id = request.values.get('edit_id')
    proposal_to_edit = None
    
    if edit_id:
        proposal_to_edit = Proposal.query.filter_by(id=edit_id, creator_id=current_user.id).first()
        if proposal_to_edit and proposal_to_edit.proposal_data:
            proposal_to_edit.proposal_data = _normalize_proposal_form_data(proposal_to_edit.proposal_data)

    if request.method == 'POST':
        try:
            file = request.files.get('proposal_file')
            normalized_payload, validation_error = _validate_proposal_payload(request.form, file)
            if validation_error:
                return jsonify({"error": validation_error}), 400

            title = (request.form.get('title') or '').strip()

            # 1. HANDLE FILE UPLOAD
            filename = proposal_to_edit.file_path if proposal_to_edit else None
            upload_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
            os.makedirs(upload_path, exist_ok=True)

            # 2. SAVE OR UPDATE
            if proposal_to_edit:
                proposal_to_edit.title = title
                proposal_to_edit.version_number += 1
                if file and file.filename != '':
                    existing_sequence = _extract_proposal_sequence(proposal_to_edit.file_path, current_user.username)
                    if not existing_sequence:
                        existing_sequence = _fallback_proposal_sequence(proposal_to_edit)

                    filename = _build_proposal_filename(
                        current_user.username,
                        existing_sequence,
                        proposal_to_edit.version_number
                    )
                    file.save(os.path.join(upload_path, filename))

                if filename:
                    proposal_to_edit.file_path = filename
                
                proposal_to_edit.proposal_data = normalized_payload
                _reset_proposal_for_resubmission(proposal_to_edit)
                db.session.add(DocumentLog(
                    document_id=proposal_to_edit.id,
                    action="Proposal Revised and Resubmitted",
                    performed_by=current_user.id
                ))
            else:
                steps = ApprovalStep.query.order_by(ApprovalStep.step_order).all()
                new_prop = Proposal(
                    title=title,
                    file_path=None,
                    proposal_data=normalized_payload,
                    creator_id=current_user.id,
                    current_step_id=steps[0].id if steps else None,
                    status='PENDING'
                )
                db.session.add(new_prop)
                db.session.flush()

                if file and file.filename != '':
                    next_sequence = _next_proposal_sequence(current_user.id, current_user.username)
                    filename = _build_proposal_filename(current_user.username, next_sequence)
                    file.save(os.path.join(upload_path, filename))
                    new_prop.file_path = filename
                
                for step in steps:
                    db.session.add(DocumentApproval(document_id=new_prop.id, step_id=step.id, status='pending'))
                db.session.add(DocumentLog(
                    document_id=new_prop.id,
                    action="Proposal Created",
                    performed_by=current_user.id
                ))

            db.session.commit()
            return jsonify({"status": "success"}), 200
        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    return render_template(
        'create_proposal.html',
        edit_data=proposal_to_edit,
        venue_options=VENUE_OPTIONS,
        sdg_options=SDG_OPTIONS
    )

@proposal_bp.route('/submission-history')
@login_required
def history():
    """Private history for the logged-in Organization."""
    redirect_response = _require_org_account()
    if redirect_response:
        return redirect_response

    query = Proposal.query.filter_by(creator_id=current_user.id)

    search = request.args.get('search')
    if search:
        query = query.filter(Proposal.title.ilike(f'%{search}%'))

    date_from = request.args.get('date_from')
    if date_from:
        try:
            date_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Proposal.created_at >= date_obj)
        except ValueError:
            pass 

    proposals = query.order_by(Proposal.created_at.desc()).all()
    return render_template('submission_history.html', proposals=proposals, is_office=False)

@proposal_bp.route('/resubmit/<int:proposal_id>', methods=['POST'])
@login_required
def resubmit(proposal_id):
    """Specific endpoint for physical PDF uploads if needed separately."""
    redirect_response = _require_org_account()
    if redirect_response:
        return redirect_response

    proposal = db.session.get(Proposal, proposal_id)
    if not proposal or proposal.creator_id != current_user.id:
        abort(403)
        
    file = request.files.get('file')
    if file and file.filename != '':
        proposal.version_number += 1
        upload_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
        os.makedirs(upload_path, exist_ok=True)

        sequence = _extract_proposal_sequence(proposal.file_path, current_user.username)
        if not sequence:
            sequence = _fallback_proposal_sequence(proposal)

        new_filename = _build_proposal_filename(current_user.username, sequence, proposal.version_number)
        file.save(os.path.join(upload_path, new_filename))
        
        proposal.file_path = new_filename
        _reset_proposal_for_resubmission(proposal)
        
        db.session.add(DocumentLog(document_id=proposal.id, action="Version Resubmitted", performed_by=current_user.id))
        db.session.commit()
        flash("Version updated successfully.", "success")

    return redirect(url_for('proposal.org_home'))
