# wsgi.py - Railway entry point
import os
import sys
from pathlib import Path

# Add the watch directory to Python path
watch_dir = Path(__file__).resolve().parent / 'watch'
sys.path.insert(0, str(watch_dir))

# Debug: Print DATABASE_URL info (without exposing password)
database_url = os.getenv('DATABASE_URL', 'Not set')
if database_url != 'Not set':
    # Mask password in URL for security
    if '@' in database_url:
        protocol = database_url.split('://')[0] if '://' in database_url else 'unknown'
        print(f"🔍 DATABASE_URL detected with protocol: {protocol}://")
    else:
        print(f"🔍 DATABASE_URL: {database_url[:20]}...")
else:
    print("🔍 No DATABASE_URL set, will use SQLite")

# Import the app creation function from watch package
from app import create_app
from app.config import DevelopmentConfig, ProductionConfig

# Select config based on environment
def _select_config():
    env = os.getenv('FLASK_ENV', 'production')
    if env == 'development':
        return DevelopmentConfig
    return ProductionConfig

# Create the application instance
app = create_app(_select_config())

# Initialize database on first run (for Railway deployment)
print("=== DATABASE INITIALIZATION START ===")
try:
    with app.app_context():
        print("✓ App context created")
        from app.extensions import db
        
        print("✓ Starting database initialization...")
        
        # Create tables if they don't exist
        db.create_all()
        print("✓ Database tables created")
        
        # Import models after db is ready
        from app.models import Role, User
        from werkzeug.security import generate_password_hash
        
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
        
        # Clean up existing users - keep only one default admin
        print("✓ Cleaning up existing users...")
        
        # Clean up audit logs first to avoid foreign key constraints
        from app.models import AuditLog, ActivityLog
        AuditLog.query.delete()
        ActivityLog.query.delete()
        print("✓ Cleaned up audit logs and activity logs")
        
        # Delete all existing users to start fresh
        User.query.delete()
        print("✓ Deleted all existing users")
        
        # Create ONLY ONE default admin account for Discipline Officer
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
        print("✓ Created default admin account: admin / admin123 (Discipline Officer)")
        
        # Note: No default user account - Discipline Officer can create users via User Management
        
        db.session.commit()
        print("✓ Database initialized successfully!")
        
except Exception as e:
    print(f"❌ Database initialization error: {e}")
    print("App will continue without database initialization")

print("=== DATABASE INITIALIZATION END ===")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

