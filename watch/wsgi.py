"""WSGI entrypoint for production deployments.
Use with a WSGI server, e.g. waitress (Windows) or gunicorn (Linux).
NOTE: This file is kept for compatibility. Railway deployment uses the root wsgi.py file.
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
        
        print("✓ Starting database initialization...")
        
        # Create tables if they don't exist
        db.create_all()
        print("✓ Database tables created")
        
        # Clean up duplicate roles first
        print("✓ Cleaning up duplicate roles...")
        
        # Get existing roles
        admin_upper = Role.query.filter_by(name='Admin').first()
        user_upper = Role.query.filter_by(name='User').first()
        admin_lower = Role.query.filter_by(name='admin').first()
        user_lower = Role.query.filter_by(name='user').first()
        
        # Update users to use lowercase roles before deleting uppercase ones
        if admin_upper and admin_lower:
            users_with_admin_upper = User.query.filter_by(role_id=admin_upper.id).all()
            for user in users_with_admin_upper:
                user.role_id = admin_lower.id
            print(f"✓ Updated {len(users_with_admin_upper)} users from Admin to admin")
        
        if user_upper and user_lower:
            users_with_user_upper = User.query.filter_by(role_id=user_upper.id).all()
            for user in users_with_user_upper:
                user.role_id = user_lower.id
            print(f"✓ Updated {len(users_with_user_upper)} users from User to user")
        
        # Commit user updates first
        db.session.commit()
        
        # Now delete uppercase versions
        if admin_upper:
            db.session.delete(admin_upper)
            print("✓ Deleted Admin role")
        if user_upper:
            db.session.delete(user_upper)
            print("✓ Deleted User role")
        
        # Create default roles (lowercase only)
        admin_role = Role.query.filter_by(name='admin').first()
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            print("✓ Created admin role")
        else:
            print("✓ Admin role already exists")
        
        user_role = Role.query.filter_by(name='user').first()
        if not user_role:
            user_role = Role(name='user')
            db.session.add(user_role)
            print("✓ Created user role")
        else:
            print("✓ User role already exists")
        
        # Commit roles first
        db.session.commit()
        print("✓ Roles cleaned up and committed")
        
        # Check if this is a fresh database (no users exist)
        # Only initialize default admin if database is empty
        existing_users_count = User.query.count()
        
        if existing_users_count == 0:
            # Fresh database - create default admin account
            print("✓ Fresh database detected - creating default admin account...")
            admin_user = User(
                username='admin',
                password_hash=generate_password_hash('admin123'),
                role_id=admin_role.id,
                is_protected=True,
                full_name='Discipline Officer',
                email='admin@sti-watch.com',
                is_active=True
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✓ Created default admin account: admin / admin123 (Discipline Officer)")
            print("⚠️ IMPORTANT: Change this password immediately after first login!")
        else:
            # Database already has users - don't touch them
            print(f"✓ Database already has {existing_users_count} user(s) - skipping user initialization")
            print("✓ Existing users preserved - no changes made")
        
        db.session.commit()
        print("✓ Database initialization complete!")
        
except Exception as e:
    print(f"❌ Database initialization error: {e}")
    print("App will continue without database initialization")
    import traceback
    traceback.print_exc()

print("=== DATABASE INITIALIZATION END ===")

