# routes/org.py
from flask import Blueprint, render_template

# Define the blueprint
org_bp = Blueprint('org', __name__)

@org_bp.route('/org-home')
def org_home():
    return render_template('org_home.html', university_name="NWU", city="Laoag")