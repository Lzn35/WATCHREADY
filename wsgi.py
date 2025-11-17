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

# Add request teardown to rollback failed transactions
@app.teardown_appcontext
def shutdown_session(exception=None):
    from app.extensions import db
    if exception:
        # Rollback on any exception to prevent InFailedSqlTransaction
        try:
            db.session.rollback()
        except:
            pass
    try:
        db.session.remove()
    except:
        pass

# Add error handler with proper transaction rollback (prevents logging loops)
@app.errorhandler(500)
def handle_500_error(e):
    from app.extensions import db
    # CRITICAL: Rollback any failed transactions to prevent InFailedSqlTransaction loops
    try:
        db.session.rollback()
    except:
        pass
    # Simple error response without database access (prevents logging loops)
    return "Internal Server Error - Check Railway logs for details", 500

# Initialize database on first run (for Railway deployment)
# Use lazy initialization to avoid worker timeouts
# Only run basic table creation, skip heavy migrations on startup
import threading
_init_lock = threading.Lock()
_init_done = False

def init_database_lazy():
    """Lazy database initialization - only runs once, fast startup"""
    global _init_done
    
    if _init_done:
        return
    
    with _init_lock:
        if _init_done:
            return
        
        try:
            with app.app_context():
                from app.extensions import db
                
                # Quick check: just create tables if they don't exist
                # Skip heavy migrations - they'll run on first request if needed
                print("✓ Quick database check...")
                db.create_all()
                
                # Quick role check - only create if missing
                from app.models import Role
                admin_role = Role.query.filter_by(name='admin').first()
                if not admin_role:
                    admin_role = Role(name='admin')
                    db.session.add(admin_role)
                
                user_role = Role.query.filter_by(name='user').first()
                if not user_role:
                    user_role = Role(name='user')
                    db.session.add(user_role)
                
                db.session.commit()
                print("✓ Database ready")
                _init_done = True
                
        except Exception as e:
            print(f"⚠ Database init warning: {e}")
            # Don't fail startup - app will work, migrations can run later
            _init_done = True  # Mark as done to prevent retry loops

# Run initialization in background thread to not block worker startup
init_thread = threading.Thread(target=init_database_lazy, daemon=True)
init_thread.start()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 5000))
    app.run(host="0.0.0.0", port=port)

