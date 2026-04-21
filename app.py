import os
import io
import secrets
import mimetypes
from datetime import timezone
from zoneinfo import ZoneInfo
from flask import Flask, abort, redirect, request, send_from_directory, send_file
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager, current_user
from models import db, ApprovalStep, Proposal, ProposalMessage
from sqlalchemy import inspect, text
from sqlalchemy.orm import joinedload
from sqlalchemy.exc import IntegrityError
from werkzeug.security import generate_password_hash
from storage import storage
from utils import normalize_proposal_data, build_proposal_pdf_bytes

# Import Blueprints
from routes.auth import auth_bp
from routes.admin import admin_bp
from routes.proposal import proposal_bp
from routes.office import office_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or secrets.token_hex(32)
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
app.config['DISPLAY_TIMEZONE'] = 'Asia/Manila'
app.config['STORAGE_BACKEND'] = os.environ.get('STORAGE_BACKEND', 'local')
app.config['S3_BUCKET'] = os.environ.get('S3_BUCKET')
app.config['S3_REGION'] = os.environ.get('S3_REGION')
app.config['S3_ENDPOINT_URL'] = os.environ.get('S3_ENDPOINT_URL')
app.config['S3_KEY_PREFIX'] = os.environ.get('S3_KEY_PREFIX', 'uploads')
app.config['S3_URL_EXPIRATION'] = int(os.environ.get('S3_URL_EXPIRATION', '3600'))
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'propas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- DYNAMIC DATABASE CONFIGURATION ---
database_url = os.environ.get('DATABASE_URL')

if database_url:
    if database_url.startswith("mysql://"):
        database_url = database_url.replace("mysql://", "mysql+pymysql://", 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local fallback
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'propas.db')
# ---------------------------------------

db.init_app(app)
storage.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.signin'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))


@app.template_filter('datetime_ph')
def datetime_ph(value, fmt='%b %d, %Y %I:%M %p'):
    if value is None:
        return 'N/A'

    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)

    return value.astimezone(ZoneInfo(app.config['DISPLAY_TIMEZONE'])).strftime(fmt)


def _proposal_signed_roles(proposal):
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


@app.route('/files/<path:filename>')
def serve_file(filename):
    if not filename:
        abort(404)

    download = request.args.get('download') == '1'
    if storage.is_remote:
        try:
            download_name = os.path.basename(filename) if download else None
            return redirect(storage.generate_download_url(filename, download_name=download_name))
        except Exception:
            abort(404)

    local_path = storage.local_full_path(filename)
    if not local_path or not os.path.exists(local_path):
        abort(404)

    mimetype, _ = mimetypes.guess_type(local_path)
    return send_from_directory(
        os.path.dirname(local_path),
        os.path.basename(local_path),
        as_attachment=download,
        mimetype=mimetype or 'application/octet-stream',
    )


@app.route('/proposal-download/<int:proposal_id>')
def download_proposal_pdf(proposal_id):
    proposal = db.session.get(Proposal, proposal_id)
    if not proposal:
        abort(404)

    if not current_user.is_authenticated:
        abort(403)
    if current_user.account_type == 'Org' and proposal.creator_id != current_user.id:
        abort(403)
    if current_user.account_type not in {'Org', 'Office', 'Admin'}:
        abort(403)

    download_name = f"{(proposal.title or 'proposal').strip() or 'proposal'}.pdf"
    proposal_data = normalize_proposal_data(proposal.proposal_data)
    proposal_data = dict(proposal_data)
    proposal_data['title'] = proposal.title
    generated_pdf = build_proposal_pdf_bytes(
        proposal_data,
        signed_roles=_proposal_signed_roles(proposal),
        title=proposal.title,
    )
    return send_file(
        io.BytesIO(generated_pdf),
        as_attachment=True,
        download_name=download_name,
        mimetype='application/pdf',
    )

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(admin_bp)
app.register_blueprint(proposal_bp)
app.register_blueprint(office_bp)

def init_approval_steps():
    if not ApprovalStep.query.first():
        steps = [("CAS", 1), ("OSA", 2), ("FINANCE", 3), ("VPAA", 4), ("VicePresident", 5), ("President", 6)]
        for name, order in steps:
            db.session.add(ApprovalStep(name=name, step_order=order))
        db.session.commit()


def init_admin_account():
    from models import User

    admin_password = os.environ.get('ADMIN_PASSWORD')
    admin = User.query.filter(User.username.ilike('Admin')).first()
    if not admin and admin_password:
        admin = User(
            username='Admin',
            password_hash=generate_password_hash(admin_password),
            account_type='Admin',
            profile_data={}
        )
        db.session.add(admin)
        try:
            db.session.commit()
        except IntegrityError:
            db.session.rollback()
    elif not admin:
        print("Admin account was not created because ADMIN_PASSWORD is not set.")


def _message_step_for_timestamp(proposal, steps, timestamp):
    if not steps:
        return None

    approvals_by_step = {approval.step_id: approval for approval in proposal.approvals}
    active_step = steps[0]
    last_acted_step = None

    for index, step in enumerate(steps):
        approval = approvals_by_step.get(step.id)
        if not approval:
            break

        if approval.status == 'approved' and approval.approved_at and approval.approved_at <= timestamp:
            last_acted_step = step
            if index + 1 < len(steps):
                active_step = steps[index + 1]
            continue

        if approval.status == 'rejected':
            event_time = approval.approved_at or proposal.created_at
            if event_time and event_time <= timestamp:
                return step

        break

    return active_step or last_acted_step


def ensure_message_thread_schema():
    inspector = inspect(db.engine)
    message_columns = {column['name'] for column in inspector.get_columns('proposal_messages')}
    if 'office_step_id' not in message_columns:
        db.session.execute(text('ALTER TABLE proposal_messages ADD COLUMN office_step_id INTEGER'))
        db.session.commit()

    messages_without_step = ProposalMessage.query.filter(ProposalMessage.office_step_id.is_(None)).all()
    if not messages_without_step:
        return

    proposals = Proposal.query.options(
        joinedload(Proposal.approvals)
    ).filter(
        Proposal.id.in_({message.proposal_id for message in messages_without_step})
    ).all()
    proposal_map = {proposal.id: proposal for proposal in proposals}
    steps = ApprovalStep.query.order_by(ApprovalStep.step_order.asc()).all()

    updated = False
    for message in messages_without_step:
        proposal = proposal_map.get(message.proposal_id)
        if not proposal:
            continue

        step = _message_step_for_timestamp(proposal, steps, message.created_at or proposal.created_at)
        if not step:
            continue

        message.office_step_id = step.id
        updated = True

    if updated:
        db.session.commit()


def drop_obsolete_tables():
    inspector = inspect(db.engine)
    table_names = set(inspector.get_table_names())
    if 'notifications' in table_names:
        db.session.execute(text('DROP TABLE notifications'))
        db.session.commit()


with app.app_context():
    db.create_all()
    init_approval_steps()
    ensure_message_thread_schema()
    drop_obsolete_tables()
    init_admin_account()

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
