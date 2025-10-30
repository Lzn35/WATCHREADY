#!/usr/bin/env python3
"""
Database Initialization Script for WATCH System
Creates database tables and populates with default data for fresh deployments.
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from watch.app import create_app
from watch.app.extensions import db
from watch.app.models import Role, User, SystemSettings, EmailSettings

def init_database():
    """Initialize the database with tables and default data."""
    
    print("=" * 70)
    print("  WATCH System - Database Initialization")
    print("=" * 70)
    print()
    
    # Create Flask app
    print("Creating Flask application...")
    app = create_app()
    
    with app.app_context():
        print("✓ Application context created")
        print()
        
        # Create all tables
        print("Creating database tables...")
        try:
            db.create_all()
            print("✓ Database tables created successfully")
            print()
        except Exception as e:
            print(f"✗ Error creating tables: {e}")
            return False
        
        # Check if roles already exist
        existing_roles = Role.query.count()
        if existing_roles > 0:
            print(f"⚠ Roles already exist ({existing_roles} found). Skipping role creation.")
        else:
            # Create default roles
            print("Creating default roles...")
            try:
                admin_role = Role(name='Admin')
                user_role = Role(name='User')
                
                db.session.add(admin_role)
                db.session.add(user_role)
                db.session.commit()
                print("✓ Created roles: Admin, User")
            except Exception as e:
                print(f"✗ Error creating roles: {e}")
                db.session.rollback()
                return False
        
        print()
        
        # Check if admin user already exists
        existing_admin = User.query.join(Role).filter(Role.name == 'Admin').first()
        if existing_admin:
            print(f"⚠ Admin user already exists: {existing_admin.username}")
            print("  Skipping admin user creation.")
        else:
            # Create default admin user
            print("Creating default admin user...")
            try:
                admin_role = Role.query.filter_by(name='Admin').first()
                if not admin_role:
                    print("✗ Error: Admin role not found!")
                    return False
                
                admin_user = User(
                    username='discipline_officer',
                    role_id=admin_role.id,
                    is_protected=True,  # Protect admin account from deletion
                    is_active=True,
                    full_name='Discipline Officer',
                    title='Administrator'
                )
                admin_user.set_password('admin123')
                
                db.session.add(admin_user)
                db.session.commit()
                print("✓ Created admin user:")
                print("    Username: discipline_officer")
                print("    Password: admin123")
                print("    ⚠ IMPORTANT: Change this password immediately after first login!")
            except Exception as e:
                print(f"✗ Error creating admin user: {e}")
                db.session.rollback()
                return False
        
        print()
        
        # Initialize system settings
        existing_settings = SystemSettings.query.first()
        if existing_settings:
            print("⚠ System settings already exist. Skipping.")
        else:
            print("Initializing system settings...")
            try:
                settings = SystemSettings(
                    system_name='WATCH System',
                    school_name='Your School Name',
                    school_website='',
                    academic_year='2024-2025'
                )
                db.session.add(settings)
                db.session.commit()
                print("✓ System settings initialized")
            except Exception as e:
                print(f"✗ Error initializing settings: {e}")
                db.session.rollback()
        
        print()
        
        # Initialize email settings
        existing_email_settings = EmailSettings.query.first()
        if existing_email_settings:
            print("⚠ Email settings already exist. Skipping.")
        else:
            print("Initializing email settings...")
            try:
                email_settings = EmailSettings(
                    enabled=False,
                    provider='gmail',
                    sender_email='',
                    sender_password='',
                    sender_name='Discipline Office'
                )
                db.session.add(email_settings)
                db.session.commit()
                print("✓ Email settings initialized")
            except Exception as e:
                print(f"✗ Error initializing email settings: {e}")
                db.session.rollback()
        
        print()
        print("=" * 70)
        print("  Database Initialization Complete!")
        print("=" * 70)
        print()
        print("Next Steps:")
        print("  1. Start the application: python run.py")
        print("  2. Login with:")
        print("     Username: discipline_officer")
        print("     Password: admin123")
        print("  3. Change the admin password immediately!")
        print("  4. Configure system settings in Settings > System Settings")
        print("  5. Create additional users in Settings > User Management")
        print()
        print("Database Location:")
        print(f"  {app.config['SQLALCHEMY_DATABASE_URI']}")
        print()
        
        return True

def main():
    """Main entry point."""
    try:
        success = init_database()
        if success:
            print("✓ Database initialization successful!")
            return 0
        else:
            print("✗ Database initialization failed!")
            return 1
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == "__main__":
    sys.exit(main())

