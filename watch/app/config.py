# watch/app/config.py
# Configuration for WATCH Flask application
import os
from pathlib import Path
from dotenv import load_dotenv

# Determine base directory (parent of app folder, i.e., watch/)
BASEDIR = Path(__file__).resolve().parent.parent

# Load .env from project app root (watch/)
env_path = BASEDIR / ".env"
if env_path.exists():
    load_dotenv(dotenv_path=env_path)
else:
    # Also try repo root .env
    repo_root_env = BASEDIR.parent / ".env"
    if repo_root_env.exists():
        load_dotenv(dotenv_path=repo_root_env)
    else:
        load_dotenv()

class Config:
    """Base configuration class."""
    
    # Security: SECRET_KEY must be set in production
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-secret-key-change-in-production'
    
    # Database configuration
    database_url = os.environ.get('DATABASE_URL')
    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        # Default SQLite database for local development
        default_db_uri = f'sqlite:///{BASEDIR / "instance" / "watch_db.sqlite"}'
        SQLALCHEMY_DATABASE_URI = default_db_uri
        print(f"🔍 Using local SQLite database: {default_db_uri}")
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # File upload configuration
    UPLOAD_FOLDER = BASEDIR / 'instance' / 'uploads'
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB max file size
    ALLOWED_EXTENSIONS = {'txt', 'pdf', 'png', 'jpg', 'jpeg', 'gif', 'doc', 'docx'}
    
    # Session configuration - Auto logout when browser tab is closed
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = 'Lax'
    SESSION_COOKIE_SECURE = False  # Set to True in production with HTTPS
    SESSION_COOKIE_NAME = 'watch_session'
    SESSION_PERMANENT = False  # Session expires when browser closes
    PERMANENT_SESSION_LIFETIME = 14400  # 4 hours (fallback)
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
    
    # Email configuration
    MAIL_SERVER = os.environ.get('MAIL_SERVER')
    MAIL_PORT = int(os.environ.get('MAIL_PORT') or 587)
    MAIL_USE_TLS = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
    MAIL_USERNAME = os.environ.get('MAIL_USERNAME')
    MAIL_PASSWORD = os.environ.get('MAIL_PASSWORD')
    MAIL_DEFAULT_SENDER = os.environ.get('MAIL_DEFAULT_SENDER')
    
    # Logging
    LOG_LEVEL = os.environ.get('LOG_LEVEL', 'INFO')
    
    # Debug mode
    DEBUG = False

class DevelopmentConfig(Config):
    """Development configuration."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False

class ProductionConfig(Config):
    """Production configuration."""
    DEBUG = False
    SESSION_COOKIE_SECURE = True

class NetworkConfig(Config):
    """Network configuration for local network access."""
    DEBUG = True
    SESSION_COOKIE_SECURE = False