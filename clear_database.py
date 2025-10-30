#!/usr/bin/env python3
"""
Clear PostgreSQL Database Script for WATCH System
Clears all data except essential roles (Admin and User)
"""

import sys
import os
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent))

from watch.app import create_app
from watch.app.extensions import db
from watch.app.models import (
    Role, User, SystemSettings, EmailSettings, Schedule, Person, 
    Case, MinorCase, MajorCase, Appointment, Notification, 
    AuditLog, ActivityLog, AttendanceChecklist, AttendanceHistory
)

def clear_database():
    """Clear all data except essential roles and admin user."""
    
    print("=" * 70)
    print("  WATCH System - Database Clear")
    print("=" * 70)
    print()
    
    # Set PostgreSQL database URL
    os.environ['DATABASE_URL'] = 'postgresql://watch_user:chen@localhost:5432/watch_db'
    print("✓ Set DATABASE_URL to PostgreSQL")
    
    # Create Flask app
    print("Creating Flask application...")
    app = create_app()
    
    with app.app_context():
        print("✓ Application context created")
        print()
        
        try:
            # Clear all data tables (in reverse order to respect foreign keys)
            print("Clearing all data...")
            
            # Clear data tables
            tables_to_clear = [
                AttendanceHistory,
                AttendanceChecklist,
                ActivityLog,
                AuditLog,
                Notification,
                Appointment,
                MajorCase,
                MinorCase,
                Case,
                Person,
                Schedule,
                EmailSettings,
                SystemSettings
            ]
            
            for model in tables_to_clear:
                try:
                    count = model.query.count()
                    if count > 0:
                        model.query.delete()
                        print(f"✓ Cleared {count} records from {model.__tablename__}")
                    else:
                        print(f"✓ {model.__tablename__} was already empty")
                except Exception as e:
                    print(f"⚠ Warning: Could not clear {model.__tablename__}: {e}")
            
            # Clear all users except the protected admin
            print("\nClearing users...")
            try:
                # Keep only the discipline_officer user
                protected_users = User.query.filter_by(is_protected=True).all()
                all_users = User.query.all()
                
                for user in all_users:
                    if not user.is_protected:
                        db.session.delete(user)
                        print(f"✓ Deleted user: {user.username}")
                    else:
                        print(f"✓ Kept protected user: {user.username}")
                
                print(f"✓ Kept {len(protected_users)} protected user(s)")
            except Exception as e:
                print(f"⚠ Warning: Could not clear users: {e}")
            
            # Keep only essential roles (Admin and User)
            print("\nManaging roles...")
            try:
                # Get existing roles
                admin_role = Role.query.filter_by(name='admin').first()
                user_role = Role.query.filter_by(name='user').first()
                
                if not admin_role:
                    admin_role = Role(name='admin')
                    db.session.add(admin_role)
                    print("✓ Created admin role")
                else:
                    print("✓ Admin role already exists")
                
                if not user_role:
                    user_role = Role(name='user')
                    db.session.add(user_role)
                    print("✓ Created user role")
                else:
                    print("✓ User role already exists")
                
                # Delete any other roles
                other_roles = Role.query.filter(~Role.name.in_(['admin', 'user'])).all()
                for role in other_roles:
                    db.session.delete(role)
                    print(f"✓ Deleted role: {role.name}")
                
            except Exception as e:
                print(f"⚠ Warning: Could not manage roles: {e}")
            
            # Ensure admin user exists
            print("\nEnsuring admin user...")
            try:
                admin_role = Role.query.filter_by(name='admin').first()
                if admin_role and not User.query.filter_by(username='discipline_officer').first():
                    from werkzeug.security import generate_password_hash
                    admin_user = User(
                        username='discipline_officer',
                        password_hash=generate_password_hash('admin123'),
                        role=admin_role,
                        is_protected=True,
                        full_name='Discipline Officer',
                        email='admin@example.com'
                    )
                    db.session.add(admin_user)
                    print("✓ Created admin user: discipline_officer / admin123")
                else:
                    print("✓ Admin user already exists")
            except Exception as e:
                print(f"⚠ Warning: Could not ensure admin user: {e}")
            
            # Commit all changes
            db.session.commit()
            print("\n✓ Database cleared successfully!")
            print()
            
            # Show final status
            print("Final database status:")
            print(f"- Roles: {Role.query.count()}")
            print(f"- Users: {User.query.count()}")
            print(f"- Cases: {Case.query.count()}")
            print(f"- Appointments: {Appointment.query.count()}")
            print(f"- Notifications: {Notification.query.count()}")
            print()
            
            return True
            
        except Exception as e:
            print(f"❌ Error clearing database: {e}")
            db.session.rollback()
            return False

def main():
    """Main clear process"""
    print("⚠️  WARNING: This will clear ALL data except essential roles!")
    print("This action cannot be undone!")
    print()
    
    confirm = input("Are you sure you want to proceed? (yes/no): ").lower().strip()
    if confirm != 'yes':
        print("Operation cancelled.")
        return False
    
    success = clear_database()
    
    if success:
        print("=" * 70)
        print("  Database Clear Completed Successfully!")
        print("=" * 70)
        print()
        print("Database now contains only:")
        print("- Admin role (Discipline Officer)")
        print("- User role (Discipline Committee)")
        print("- discipline_officer user (admin123)")
        print()
        print("Ready for deployment! 🚀")
    else:
        print("❌ Database clear failed!")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
