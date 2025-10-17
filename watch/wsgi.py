"""WSGI entrypoint for production deployments.
Use with a WSGI server, e.g. waitress (Windows) or gunicorn (Linux).
"""

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app import create_app
from app.config import ProductionConfig, DevelopmentConfig, NetworkConfig, Config


def _select_config():
    name = os.getenv('APP_CONFIG', 'Config')
    if name == 'ProductionConfig':
        return ProductionConfig
    if name == 'DevelopmentConfig':
        return DevelopmentConfig
    if name == 'NetworkConfig':
        return NetworkConfig
    return Config


app = create_app(_select_config())

# Initialize database on first run
print("=== DATABASE INITIALIZATION START ===")
try:
    with app.app_context():
        print("✓ App context created")
        from app.extensions import db
        from app.models import Role, User
        from werkzeug.security import generate_password_hash
        
        print("✓ Imports successful")
        print("Starting database initialization...")
        
        # Create tables if they don't exist
        db.create_all()
        print("✓ Database tables created")
        
        # Create default roles
        if not Role.query.filter_by(name='admin').first():
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            print("✓ Created admin role")
        else:
            print("✓ Admin role already exists")
        
        if not Role.query.filter_by(name='user').first():
            user_role = Role(name='user')
            db.session.add(user_role)
            print("✓ Created user role")
        else:
            print("✓ User role already exists")
        
        # Create admin user
        admin_role_obj = Role.query.filter_by(name='admin').first()
        if admin_role_obj and not User.query.filter_by(username='discipline_officer').first():
            admin_user = User(
                username='discipline_officer',
                password_hash=generate_password_hash('admin123'),
                role=admin_role_obj,
                is_protected=True,
                full_name='Discipline Officer',
                email='admin@example.com'
            )
            db.session.add(admin_user)
            print("✓ Created admin user: discipline_officer / admin123")
        else:
            print("✓ Admin user already exists")
        
        db.session.commit()
        print("✓ Database initialized successfully!")
        
except Exception as e:
    print(f"❌ Database initialization error: {e}")
    print("App will continue without database initialization")
    import traceback
    traceback.print_exc()

print("=== DATABASE INITIALIZATION END ===")


