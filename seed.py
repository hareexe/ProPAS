from app import app, db, User
from werkzeug.security import generate_password_hash

# Define your list
orgs = ["Icons", "Hibe", "Kwago", "Casso", "Psych", "Aces"]
offices = ["Osa", "Finance", "Vpaa", "Cas", "VicePresident", "President"]

with app.app_context():
    db.create_all() 
    
    for name in orgs:
        if not User.query.filter_by(username=name).first():
            new_user = User(
                username=name,
                password_hash=generate_password_hash(f"@{name}2026."),
                account_type="Org"
            )
            db.session.add(new_user)
    
    for name in offices:
        if not User.query.filter_by(username=name).first():
            new_user = User(
                username=name,
                password_hash=generate_password_hash(f"@{name}2026."),
                account_type="Office"
            )
            db.session.add(new_user)
            print(f"Added Office: {name}")
            
    db.session.commit()
    print("Database seeded!")