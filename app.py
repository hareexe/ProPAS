import os, json
from flask import Flask, render_template, flash, request, redirect, url_for, send_from_directory, jsonify
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, login_required, login_user, logout_user, current_user
from datetime import datetime
from werkzeug.security import check_password_hash
from werkzeug.utils import secure_filename
from models import db, User, Proposal, ApprovalStep, DocumentApproval, DocumentLog

# ------------------ APP CONFIG ------------------
app = Flask(__name__)
app.config['SECRET_KEY'] = 'propas-nwu-secret-key'
# This is where the physical PDFs will live
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')

basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'propas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
csrf = CSRFProtect(app)

login_manager = LoginManager(app)
login_manager.login_view = 'signin'
login_manager.login_message_category = "warning"

# ------------------ HELPERS ------------------
@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))

def init_approval_steps():
    if not ApprovalStep.query.first():
        steps = [("CAS", 1), ("OSA", 2), ("FINANCE", 3), ("VPAA", 4), ("PRESIDENT", 5)]
        for name, order in steps:
            db.session.add(ApprovalStep(name=name, step_order=order))
        db.session.commit()

# ------------------ ROUTES ------------------

@app.route('/', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        dest = 'office_home' if current_user.account_type == 'Office' else 'org_home'
        return redirect(url_for(dest))
    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            dest = 'office_home' if user.account_type == 'Office' else 'org_home'
            return redirect(url_for(dest))
        flash("Invalid Username or Password", "danger")
    return render_template('signin.html')

@app.route('/org-home')
@login_required
def org_home():
    proposals = Proposal.query.filter_by(creator_id=current_user.id).all()
    pending = Proposal.query.filter_by(creator_id=current_user.id, status='PENDING').count()
    rejected = Proposal.query.filter_by(creator_id=current_user.id, status='REJECTED').count()
    approved = Proposal.query.filter_by(creator_id=current_user.id, status='APPROVED').count()
    return render_template('org_home.html', proposals=proposals, 
                           pending_count=pending, rejected_count=rejected, approved_count=approved)

@app.route('/create-proposal', methods=['GET', 'POST'])
@login_required
def create_proposal():
    # Check if we are fixing a rejected proposal
    edit_id = request.args.get('edit_id')
    proposal_to_edit = None
    if edit_id:
        proposal_to_edit = Proposal.query.get(edit_id)

    if request.method == 'POST':
        try:
            file = request.files.get('proposal_file')
            title = request.form.get('title')
            
            if not title:
                return jsonify({"error": "Missing title"}), 400

            # 1. HANDLE FILE UPLOAD
            filename = None
            if file:
                upload_path = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
                if not os.path.exists(upload_path):
                    os.makedirs(upload_path)
                
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                filename = secure_filename(f"{timestamp}_{title}.pdf")
                file.save(os.path.join(upload_path, filename))

            # 2. SAVE OR UPDATE DB
            if proposal_to_edit:
                # UPDATE EXISTING (FIXING REJECTION)
                proposal_to_edit.title = title
                if filename: # Only update file path if a new PDF was generated
                    proposal_to_edit.file_path = filename
                
                proposal_to_edit.proposal_data = request.form.to_dict()
                proposal_to_edit.status = 'PENDING' # Reset status to Pending
                
                # Reset the specific approval record that rejected it
                # so the office sees it as a fresh submission
                rej_approval = DocumentApproval.query.filter_by(
                    document_id=proposal_to_edit.id, 
                    status='rejected'
                ).first()
                if rej_approval:
                    rej_approval.status = 'pending'
                    rej_approval.remarks = "Resubmitted/Fixed by Org"

            else:
                # CREATE NEW SUBMISSION
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

                # SETUP LEDGER (Only for new ones)
                for step in steps:
                    db.session.add(DocumentApproval(document_id=new_prop.id, step_id=step.id))

            db.session.commit()
            return jsonify({"status": "success"}), 200

        except Exception as e:
            db.session.rollback()
            return jsonify({"error": str(e)}), 500

    # GET: Load the form (optionally with old data if editing)
    return render_template('create_proposal.html', edit_data=proposal_to_edit)

@app.route('/office-home', methods=['GET', 'POST'])
@app.route('/office-home/<int:review_id>', methods=['GET', 'POST'])
@login_required
def office_home(review_id=None):
    # 1. Identify which step this user belongs to
    # (Matches username 'CAS' to step name 'CAS')
    my_step = ApprovalStep.query.filter(ApprovalStep.name.ilike(current_user.username)).first()
    
    if not my_step:
        flash("Account not linked to an approval step.", "warning")
        return redirect(url_for('org_home'))

    # 2. Handle POST (Approve/Reject)
    if request.method == 'POST' and review_id:
        prop = Proposal.query.get_or_404(review_id)
        action = request.form.get('action')
        remarks = request.form.get('remarks')
        
        # Get the specific approval record for this step
        approval = DocumentApproval.query.filter_by(document_id=prop.id, step_id=my_step.id).first()

        if action == 'approve':
            approval.status = 'approved'
            approval.remarks = remarks
            approval.approved_at = datetime.utcnow()
            
            # Find next step
            next_s = ApprovalStep.query.filter(ApprovalStep.step_order > my_step.step_order).order_by(ApprovalStep.step_order).first()
            if next_s:
                prop.current_step_id = next_s.id
            else:
                prop.status = 'APPROVED'
                prop.current_step_id = None
            flash("Proposal approved!", "success")

        elif action == 'reject':
            approval.status = 'rejected'
            approval.remarks = remarks
            prop.status = 'REJECTED'
            flash("Proposal rejected.", "warning")

        db.session.commit()
        return redirect(url_for('office_home'))

    # 3. Handle GET
    proposals = Proposal.query.filter_by(current_step_id=my_step.id).all()
    selected_proposal = Proposal.query.get(review_id) if review_id else None

    return render_template('office_home.html', 
                           proposals=proposals, 
                           selected_proposal=selected_proposal)

@app.route('/resubmit/<int:review_id>')
@login_required
def resubmit_proposal(review_id):
    prop = Proposal.query.get_or_404(review_id)
  
    if prop.creator_id != current_user.id:
        flash("Unauthorized action.", "danger")
        return redirect(url_for('org_home'))

    prop.status = 'PENDING'
 
    approval = DocumentApproval.query.filter_by(
        document_id=prop.id, 
        step_id=prop.current_step_id
    ).first()
    if approval:
        approval.status = 'pending'
        approval.remarks = "Resubmitted by Organization"

    db.session.commit()
    flash("Proposal resubmitted for review.", "success")
    return redirect(url_for('org_home'))

@app.route('/submission-history')
@login_required
def submission_history():
    proposals = Proposal.query.filter_by(creator_id=current_user.id).order_by(Proposal.created_at.desc()).all()
    return render_template('submission_history.html', proposals=proposals)

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('signin'))

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_approval_steps()
    app.run(debug=True)