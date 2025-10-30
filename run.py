#!/usr/bin/env python3
"""
Simple runner script for the Flask application
PRODUCTION READY - Debug mode disabled
"""
import sys
import os

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from watch.app import create_app

if __name__ == "__main__":
    app = create_app()
    # Debug mode from config (True for development, False for production)
    debug_mode = app.config.get('DEBUG', False)
    app.run(host="0.0.0.0", port=5000, debug=debug_mode)
    
# For production deployment with Gunicorn:
# gunicorn -w 4 -b 0.0.0.0:5000 --timeout 120 run:app
