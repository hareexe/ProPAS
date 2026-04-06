import os
from flask import Flask
from flask_wtf.csrf import CSRFProtect
from flask_login import LoginManager
from models import db, ApprovalStep

# Import Blueprints
from routes.auth import auth_bp
from routes.proposal import proposal_bp
from routes.office import office_bp

app = Flask(__name__)
app.config['SECRET_KEY'] = 'propas-nwu-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join('static', 'uploads')
basedir = os.path.abspath(os.path.dirname(__file__))
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'propas.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db.init_app(app)
csrf = CSRFProtect(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.signin'

@login_manager.user_loader
def load_user(user_id):
    from models import User
    return db.session.get(User, int(user_id))

# Register Blueprints
app.register_blueprint(auth_bp)
app.register_blueprint(proposal_bp)
app.register_blueprint(office_bp)

def init_approval_steps():
    if not ApprovalStep.query.first():
        steps = [("CAS", 1), ("OSA", 2), ("FINANCE", 3), ("VPAA", 4), ("VICEPRESIDENT", 5), ("PRESIDENT", 6)]
        for name, order in steps:
            db.session.add(ApprovalStep(name=name, step_order=order))
        db.session.commit()

if __name__ == '__main__':
    with app.app_context():
        db.create_all()
        init_approval_steps()
    app.run(debug=True)