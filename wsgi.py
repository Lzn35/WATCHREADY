# wsgi.py - Railway entry point
import os
import sys
from pathlib import Path

# Add the watch directory to Python path
watch_dir = Path(__file__).resolve().parent / 'watch'
sys.path.insert(0, str(watch_dir))

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
        from app.models import Role, User
        from werkzeug.security import generate_password_hash
        
        print("✓ Imports successful")
        print("Starting database initialization...")
        
        # Create tables if they don't exist
        db.create_all()
        print("✓ Database tables created")
        
        # Create default roles
        if not Role.query.filter_by(name='Admin').first():
            admin_role = Role(name='Admin')
            db.session.add(admin_role)
            print("✓ Created Admin role")
        else:
            print("✓ Admin role already exists")
        
        if not Role.query.filter_by(name='User').first():
            user_role = Role(name='User')
            db.session.add(user_role)
            print("✓ Created User role")
        else:
            print("✓ User role already exists")
        
        # Create admin user
        admin_role_obj = Role.query.filter_by(name='Admin').first()
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

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

