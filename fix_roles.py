#!/usr/bin/env python3
"""Fix duplicate roles in database"""

import sys
from pathlib import Path

# Add the watch directory to Python path
watch_dir = Path(__file__).resolve().parent / 'watch'
sys.path.insert(0, str(watch_dir))

from app import create_app
from app.config import DevelopmentConfig
from app.extensions import db
from app.models import Role, User

def fix_roles():
    app = create_app(DevelopmentConfig)
    with app.app_context():
        print('Current roles in database:')
        roles = Role.query.all()
        for role in roles:
            print(f'ID: {role.id}, Name: "{role.name}"')
        
        print('\nCleaning up duplicate roles...')
        
        # Keep only lowercase versions
        admin_role = Role.query.filter_by(name='admin').first()
        user_role = Role.query.filter_by(name='user').first()
        
        # Create lowercase roles if they don't exist
        if not admin_role:
            admin_role = Role(name='admin')
            db.session.add(admin_role)
            print('Created admin role')
        
        if not user_role:
            user_role = Role(name='user')
            db.session.add(user_role)
            print('Created user role')
        
        db.session.commit()
        
        # Get uppercase roles
        admin_upper = Role.query.filter_by(name='Admin').first()
        user_upper = Role.query.filter_by(name='User').first()
        
        # Update users to use lowercase roles
        if admin_upper:
            users_with_admin_upper = User.query.filter_by(role_id=admin_upper.id).all()
            for user in users_with_admin_upper:
                user.role_id = admin_role.id
            print(f'Updated {len(users_with_admin_upper)} users from Admin to admin')
        
        if user_upper:
            users_with_user_upper = User.query.filter_by(role_id=user_upper.id).all()
            for user in users_with_user_upper:
                user.role_id = user_role.id
            print(f'Updated {len(users_with_user_upper)} users from User to user')
        
        # Delete uppercase versions
        if admin_upper:
            db.session.delete(admin_upper)
            print('Deleted Admin role')
        
        if user_upper:
            db.session.delete(user_upper)
            print('Deleted User role')
        
        db.session.commit()
        
        print('\nAfter cleanup:')
        roles = Role.query.all()
        for role in roles:
            print(f'ID: {role.id}, Name: "{role.name}"')
        
        print('\nUsers and their roles:')
        users = User.query.all()
        for user in users:
            print(f'User: {user.username}, Role: {user.role.name if user.role else "None"}')

if __name__ == "__main__":
    fix_roles()
