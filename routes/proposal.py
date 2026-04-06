import os
from flask import Blueprint, render_template, request, jsonify, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from datetime import datetime
from werkzeug.utils import secure_filename
from models import db, Proposal, ApprovalStep, DocumentApproval, DocumentLog

# Define the Blueprint - Only for Organization/Student tasks
proposal_bp = Blueprint('proposal', __name__)

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
    edit_id = request.args.get('edit_id')
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
            if file and file.filename != '':
                upload_path = os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'])
                os.makedirs(upload_path, exist_ok=True)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = secure_filename(f"{timestamp}_{title}.pdf")
                file.save(os.path.join(upload_path, filename))

            # 2. SAVE OR UPDATE
            if proposal_to_edit:
                proposal_to_edit.title = title
                if filename: 
                    proposal_to_edit.file_path = filename
                
                proposal_to_edit.proposal_data = request.form.to_dict()
                proposal_to_edit.status = 'PENDING'
                
                # Reset any rejected steps to pending
                DocumentApproval.query.filter_by(document_id=proposal_to_edit.id, status='rejected').update({"status": "pending"})
                
                first_step = ApprovalStep.query.order_by(ApprovalStep.step_order).first()
                proposal_to_edit.current_step_id = first_step.id if first_step else None
            else:
                steps = ApprovalStep.query.order_by(ApprovalStep.step_order).all()
                new_prop = Proposal(
                    title=title,
                    file_path=filename,
                    proposal_data=request.form.to_dict(),
                    creator_id=current_user.id,
                    current_step_id=steps[0].id if steps else None,
                    status='PENDING'
                )
                db.session.add(new_prop)
                db.session.flush() 
                
                for step in steps:
                    db.session.add(DocumentApproval(document_id=new_prop.id, step_id=step.id, status='pending'))

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
        new_filename = f"Proposal_{proposal.id}_v{proposal.version_number}.pdf"
        file.save(os.path.join(current_app.root_path, current_app.config['UPLOAD_FOLDER'], new_filename))
        
        proposal.file_path = new_filename
        proposal.status = 'PENDING'
        
        db.session.add(DocumentLog(document_id=proposal.id, action="Version Resubmitted", performed_by=current_user.id))
        db.session.commit()
        flash("Version updated successfully.", "success")

    return redirect(url_for('proposal.org_home'))