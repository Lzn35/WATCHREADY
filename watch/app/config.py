# watch/app/config.py
# Consolidated and secure configuration for WATCH Flask application
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
    """Consolidated configuration class with secure defaults."""
    
    # Security: SECRET_KEY must be set in production
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-change-me-in-production")
    
    # Database configuration - Portable and environment-based
    # Support both SQLite (development) and PostgreSQL (production)
    instance_path = BASEDIR / 'instance'
    default_db_path = instance_path / 'watch_db.sqlite'
    default_db_uri = f"sqlite:///{str(default_db_path).replace(chr(92), '/')}"
    
    # Check if DATABASE_URL is provided (for PostgreSQL/MySQL)
    database_url = os.getenv("DATABASE_URL")
    if database_url:
        SQLALCHEMY_DATABASE_URI = database_url
    else:
        SQLALCHEMY_DATABASE_URI = default_db_uri
    
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # Database-specific engine options
    if database_url and 'postgresql' in database_url:
        # PostgreSQL configuration
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'pool_size': 10,
            'max_overflow': 20,
            'pool_timeout': 30,
        }
    elif database_url and 'mysql' in database_url:
        # MySQL configuration
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
            'pool_size': 10,
            'max_overflow': 20,
        }
    else:
        # SQLite configuration (default)
        SQLALCHEMY_ENGINE_OPTIONS = {
            'pool_pre_ping': True,
            'pool_recycle': 3600,
        }
    
    # CSRF Protection
    WTF_CSRF_ENABLED = True
    WTF_CSRF_TIME_LIMIT = None  # No timeout for development; set to 3600 in production
    WTF_CSRF_SSL_STRICT = False  # Set to True in production with HTTPS
    
    # Debug mode - default False; override in dev via env
    DEBUG = os.getenv("DEBUG", "False").lower() in ("1", "true", "yes")
    
    # File Upload Security
    MAX_CONTENT_LENGTH = int(os.getenv("MAX_CONTENT_LENGTH", 100 * 1024 * 1024))  # 100 MB default
    UPLOAD_FOLDER = os.getenv("UPLOAD_FOLDER", str(BASEDIR / "instance" / "uploads"))
    ALLOWED_EXTENSIONS = set(
        x.strip().lower() 
        for x in os.getenv("ALLOWED_EXTENSIONS", "jpg,jpeg,png,gif,bmp,webp,pdf,docx,doc,txt,rtf,mp4,avi,mov,wmv,flv,webm,mp3,wav,zip,rar,7z").split(",")
    )
    
    # Session Security - Auto logout when browser/tab closes
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.getenv("SESSION_COOKIE_SECURE", "False").lower() in ("1", "true", "yes")
    PERMANENT_SESSION_LIFETIME = 86400  # 24 hours for CSRF token stability
    SESSION_PERMANENT = False  # Session expires when browser closes
    # Note: SESSION_COOKIE_SECURE should be True in actual production under HTTPS
    
    # Template Auto-Reload (False in production for performance)
    TEMPLATES_AUTO_RELOAD = os.getenv("TEMPLATES_AUTO_RELOAD", "False").lower() in ("1", "true", "yes")
    
    # JSON Configuration
    JSON_SORT_KEYS = False
    JSONIFY_PRETTYPRINT_REGULAR = False
    
    # MySQL Configuration (for future migration)
    # Uncomment and configure when ready to migrate from SQLite to MySQL
    # MYSQL_HOST = os.getenv("MYSQL_HOST", "localhost")
    # MYSQL_PORT = int(os.getenv("MYSQL_PORT", 3306))
    # MYSQL_USER = os.getenv("MYSQL_USER", "watch_user")
    # MYSQL_PASSWORD = os.getenv("MYSQL_PASSWORD", "")
    # MYSQL_DATABASE = os.getenv("MYSQL_DATABASE", "watch_db")
    # To enable MySQL: set DATABASE_URL=mysql+pymysql://${MYSQL_USER}:${MYSQL_PASSWORD}@${MYSQL_HOST}:${MYSQL_PORT}/${MYSQL_DATABASE}
    
    # Tesseract OCR path (if used)
    TESSERACT_PATH = os.getenv("TESSERACT_PATH", "")


class ProductionConfig(Config):
    """Hardened production defaults for HTTPS deployments"""
    DEBUG = False
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = True
    SESSION_COOKIE_SECURE = True
    TEMPLATES_AUTO_RELOAD = False
    ENABLE_HSTS = True
    # MySQL recommended defaults when migrating
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    # Rate limiting defaults (can be overridden by env)
    RATELIMIT_DEFAULT = None
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')


class NetworkConfig(Config):
    """Network deployment config for local HTTP access (between dev and prod)"""
    DEBUG = False
    WTF_CSRF_TIME_LIMIT = 3600
    WTF_CSRF_SSL_STRICT = False  # Allow HTTP for local network
    SESSION_COOKIE_SECURE = False  # Allow HTTP for local network
    TEMPLATES_AUTO_RELOAD = False
    ENABLE_HSTS = False  # Disable HSTS for HTTP
    # MySQL recommended defaults when migrating
    SQLALCHEMY_ENGINE_OPTIONS = {
        'pool_pre_ping': True,
        'pool_recycle': 280,
    }
    # Rate limiting defaults (can be overridden by env)
    RATELIMIT_DEFAULT = None
    RATELIMIT_STORAGE_URI = os.getenv('RATELIMIT_STORAGE_URI', 'memory://')


class DevelopmentConfig(Config):
    """Developer-friendly defaults for local runs"""
    DEBUG = True
    WTF_CSRF_TIME_LIMIT = None
    WTF_CSRF_SSL_STRICT = False
    SESSION_COOKIE_SECURE = False
    TEMPLATES_AUTO_RELOAD = True
    RATELIMIT_DEFAULT = None
    RATELIMIT_STORAGE_URI = 'memory://'
