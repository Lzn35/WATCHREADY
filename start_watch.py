#!/usr/bin/env python3
"""
WATCH System Startup Script
Automatically sets the correct database path and starts the Flask app
"""

import os
import sys
from pathlib import Path

def start_watch():
    """Start the WATCH Flask application with correct database configuration"""
    
    print("=" * 60)
    print("  WATCH - Discipline Office Management System")
    print("  Starting Flask Application...")
    print("=" * 60)
    
    # Get the correct paths
    project_root = Path(__file__).resolve().parent
    watch_dir = project_root / 'watch'
    
    # Check if .env file exists and load it
    env_file = project_root / '.env'
    if env_file.exists():
        from dotenv import load_dotenv
        load_dotenv(env_file)
        print(f"✓ Loaded environment from .env file")
    
    # Get database URL from environment or use default
    database_url = os.getenv('DATABASE_URL', 'sqlite:///./instance/watch_db.sqlite')
    
    print(f"Project root: {project_root}")
    print(f"DATABASE_URL: {database_url}")
    print()
    
    try:
        # Import and create the Flask app
        sys.path.insert(0, str(watch_dir.parent))
        from watch.app import create_app
        
        app = create_app()
        
        # Test database connection
        with app.app_context():
            from watch.app.extensions import db
            from watch.app.models import User
            
            db.engine.connect()
            user_count = User.query.count()
            print(f"✓ Database connection successful!")
            print(f"✓ Users in database: {user_count}")
            print()
        
        # Start the Flask app
        print("Starting Flask development server...")
        print("Access the application at: http://localhost:5000")
        print("Press Ctrl+C to stop the server")
        print("=" * 60)
        
        app.run(host="0.0.0.0", port=5000, debug=True)
        
    except Exception as e:
        print(f"ERROR: Failed to start WATCH application")
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    start_watch()
