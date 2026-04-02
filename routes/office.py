from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_required, current_user
from models import db, Proposal

# Define the blueprint
office_bp = Blueprint('office', __name__)

# 1: Cas -> 2: Osa -> 3: Vpaa -> 4: Finance -> 5: President
STAGE_MAP = {
    'Cas': 1,
    'Osa': 2,
    'Vpaa': 3,
    'Finance': 4,
    'President': 5
}

@office_bp.route('/office-home', methods=['GET', 'POST'])
@office_bp.route('/office-home/<int:review_id>', methods=['GET', 'POST'])
@login_required
def office_home(review_id=None):
    # Identity Check
    office_username = current_user.username 
    my_stage = STAGE_MAP.get(office_username)

    # Security: Only 'Office' accounts can access this blueprint
    if current_user.account_type != 'Office' or not my_stage:
        flash("Unauthorized access to Office Dashboard.", "danger")
        return redirect(url_for('signin'))

    # --- HANDLE FORM SUBMISSION (Approve/Reject) ---
    if request.method == 'POST' and review_id:
        proposal = Proposal.query.get_or_404(review_id)
        action = request.form.get('action')
        feedback = request.form.get('feedback')

        # Security: Prevent an office from acting on a document not at their stage
        if proposal.current_stage != my_stage:
            flash("Action denied: This proposal is no longer at your stage.", "danger")
            return redirect(url_for('office.office_home'))

        if action == 'approve':
            # Move to next office in the sequence
            proposal.current_stage += 1
            
            # If it passes the President (Stage 5), it's officially APPROVED
            if proposal.current_stage > 5:
                proposal.status = 'APPROVED'
            else:
                proposal.status = 'PENDING' # Keep pending as it moves to next office
            
            flash(f"Proposal '{proposal.title}' approved and forwarded to the next office.", "success")
        
        elif action == 'reject':
            # Memory Logic: Remember this office rejected it
            proposal.last_rejected_by = my_stage
            # Send back to Org (Stage 0)
            proposal.current_stage = 0 
            proposal.status = 'REJECTED'
            # Save feedback so the Org knows why it was returned
            proposal.description = f"REJECTION FEEDBACK from {office_username.upper()}: {feedback}"
            
            flash(f"Proposal '{proposal.title}' returned to Organization for corrections.", "warning")

        db.session.commit()
        return redirect(url_for('office.office_home'))

    # --- HANDLE DISPLAY LOGIC ---
    # Fetch only proposals waiting at THIS specific desk
    proposals = Proposal.query.filter_by(current_stage=my_stage).all()
    
    # Calculate Dynamic Stats
    pending_count = len(proposals)
    total_budget = sum(p.budget for p in proposals)

    # If a specific proposal is being reviewed, fetch its details
    selected_proposal = None
    if review_id:
        selected_proposal = Proposal.query.get(review_id)

    return render_template(
        'office_home.html', 
        proposals=proposals, 
        selected_proposal=selected_proposal,
        username=office_username,
        pending_count=pending_count,
        total_budget="{:,.2f}".format(total_budget),
        university_name="NWU",
        city="Laoag"
    )