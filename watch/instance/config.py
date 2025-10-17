# PRODUCTION CONFIGURATION
# This file is kept for compatibility but actual configuration should be in environment variables
# Set environment variables or create a .env file in the watch/ directory

import os

# Load from environment variables (set via .env file or system environment)
SECRET_KEY = os.getenv("SECRET_KEY", "dev-instance-secret-change-in-production")

# Database Configuration
# The application will use DATABASE_URL from environment variables if set
# For development: SQLite (default fallback)
# For production: Set DATABASE_URL environment variable to your MySQL connection string
basedir = os.path.abspath(os.path.dirname(__file__))
DATABASE_URL = os.getenv("DATABASE_URL", f"sqlite:///{os.path.join(basedir, 'watch_db.sqlite')}")


