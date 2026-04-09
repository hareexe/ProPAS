import os
import re
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
from models import db, Proposal, ApprovalStep, DocumentApproval, DocumentLog

# Define the Blueprint - Only for Organization/Student tasks
proposal_bp = Blueprint('proposal', __name__)

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

@proposal_bp.route('/org-home')
@login_required
def org_home():
    """Main dashboard for Organizations to see a summary of their work."""
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
        approved_count=approved
    )

@proposal_bp.route('/create-proposal', methods=['GET', 'POST'])
@login_required
def create():
    """Handles creating new proposals and editing rejected ones."""
    edit_id = request.values.get('edit_id')
    proposal_to_edit = None
    
    if edit_id:
        proposal_to_edit = Proposal.query.filter_by(id=edit_id, creator_id=current_user.id).first()

    if request.method == 'POST':
        try:
            file = request.files.get('proposal_file')
            title = request.form.get('title')
            
            if not title:
                return jsonify({"error": "Missing title"}), 400

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
                
                proposal_to_edit.proposal_data = request.form.to_dict()
                proposal_to_edit.status = 'PENDING'
                
                # Reset any rejected steps to pending
                DocumentApproval.query.filter_by(document_id=proposal_to_edit.id).update({
                    "status": "pending",
                    "remarks": None,
                    "approved_at": None,
                    "signed_name": None,
                    "approved_by": None,
                })
                
                first_step = ApprovalStep.query.order_by(ApprovalStep.step_order).first()
                proposal_to_edit.current_step_id = first_step.id if first_step else None
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
                    proposal_data=request.form.to_dict(),
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

    return render_template('create_proposal.html', edit_data=proposal_to_edit)

@proposal_bp.route('/submission-history')
@login_required
def history():
    """Private history for the logged-in Organization."""
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
        proposal.status = 'PENDING'
        
        db.session.add(DocumentLog(document_id=proposal.id, action="Version Resubmitted", performed_by=current_user.id))
        db.session.commit()
        flash("Version updated successfully.", "success")

    return redirect(url_for('proposal.org_home'))
