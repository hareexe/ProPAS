from flask import Blueprint, render_template, request, redirect, url_for, flash, current_app, abort
from flask_login import login_required, current_user
from models import db, User, Proposal, ApprovalStep, DocumentApproval
from utils import add_signature_page
from datetime import datetime

office_bp = Blueprint('office', __name__)

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
        officer_name = request.form.get('officer_name')
        remarks = request.form.get('remarks')
  
        current_approval = DocumentApproval.query.filter_by(
            document_id=prop.id, 
            step_id=my_step.id
        ).first()

        if action == 'approve':
            if not officer_name:
                flash("Officer name is required for the signature.", "warning")
                return redirect(url_for('office.review', review_id=review_id))
         
            success = add_signature_page(
                current_app.config['UPLOAD_FOLDER'], 
                prop.file_path, 
                my_step.name.upper(), 
                officer_name
            )
            
            if success:
                current_approval.signed_name = officer_name
                current_approval.status = 'approved'
                current_approval.remarks = remarks
                current_approval.approved_at = datetime.utcnow()

                next_s = ApprovalStep.query.filter(
                    ApprovalStep.step_order > my_step.step_order
                ).order_by(ApprovalStep.step_order.asc()).first()

                if next_s:
                    prop.current_step_id = next_s.id
                else:
                    prop.status = 'APPROVED'
                    prop.current_step_id = None
                
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
    selected = db.session.get(Proposal, review_id) if review_id else None

    return render_template(
        'office_home.html', 
        proposals=proposals, 
        selected_proposal=selected,
        username=current_user.username,
        pending_count=len(proposals)
    )

# ... existing review function ...

@office_bp.route('/master-history')
@login_required
def master_history():
    """Global history for Office accounts to review all organizations."""
    if current_user.account_type != 'Office':
        abort(403)

    query = Proposal.query.join(User)

    # Global Search
    search = request.args.get('search')
    if search:
        query = query.filter(Proposal.title.ilike(f'%{search}%'))

    # Filter by specific Organization (Username)
    username_filter = request.args.get('username_filter')
    if username_filter:
        query = query.filter(User.username.ilike(f'%{username_filter}%'))

    # Apply Date Filter
    date_from = request.args.get('date_from')
    if date_from:
        try:
            date_obj = datetime.strptime(date_from, '%Y-%m-%d')
            query = query.filter(Proposal.created_at >= date_obj)
        except ValueError:
            pass 

    proposals = query.order_by(Proposal.created_at.desc()).all()
    
    return render_template('submission_history.html', proposals=proposals, is_history=True, is_office=True)
