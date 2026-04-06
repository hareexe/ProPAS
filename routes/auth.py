from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user, logout_user, current_user
from werkzeug.security import check_password_hash
from models import User

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/', methods=['GET', 'POST'])
def signin():
    if current_user.is_authenticated:
        # Update these two strings with blueprint prefixes
        dest = 'office.review' if current_user.account_type == 'Office' else 'proposal.org_home'
        return redirect(url_for(dest))

    if request.method == 'POST':
        user = User.query.filter_by(username=request.form.get('username')).first()
        
        if user and check_password_hash(user.password_hash, request.form.get('password')):
            login_user(user)
            # Update these two strings here as well
            dest = 'office.review' if user.account_type == 'Office' else 'proposal.org_home'
            return redirect(url_for(dest))
        else:
            flash("Invalid Username or Password", "danger")

    return render_template('signin.html')

@auth_bp.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('auth.signin'))