from flask import Flask, request
from .extensions import db, csrf, login_manager, limiter
from .config import Config
import os

def create_app(config_class=Config):
    """Application factory for WATCH Flask app with security hardening."""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(config_class)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Configure sessions - Auto logout when browser closes
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'watch:'
    # PERMANENT_SESSION_LIFETIME controlled by config class

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)  # CSRF protection now ENABLED
    limiter.init_app(app)
    
    # Initialize database settings for ACID compliance (WAL mode, pragmas, etc.)
    from .services.database import init_database_settings
    with app.app_context():
        init_database_settings(app)
    
    # Setup comprehensive logging (database operations, errors, etc.)
    from .utils.logging_config import setup_logging
    setup_logging(app)
    
    # Setup security logging (admin protection, file uploads, access control)
    from .utils.security_logger import security_logger
    security_logger.init_app(app)
    
    # Setup security headers middleware (X-Frame-Options, CSP, etc.)
    from .middleware.security_headers import init_security_headers
    init_security_headers(app)
    
    # Configure Login Manager
    login_manager.login_view = 'auth.login'
    login_manager.login_message = 'Please log in to access this page.'
    login_manager.login_message_category = 'info'
    
    # User loader function
    @login_manager.user_loader
    def load_user(user_id):
        from .models import User
        return User.query.get(int(user_id))
    
    # Load user before each request
    @app.before_request
    def load_logged_in_user():
        from .auth_utils import load_user
        load_user()
    
    # Make current_user available in templates
    @app.context_processor
    def inject_user():
        from .auth_utils import get_current_user
        return dict(current_user=get_current_user())

    # Register blueprints if exist (safe import)
    try:
        from .routes import core_bp
        app.register_blueprint(core_bp)
    except Exception:
        pass

    try:
        from .modules.auth import bp as auth_bp
        app.register_blueprint(auth_bp)
    except Exception:
        pass

    try:
        from .modules.ocr import bp as ocr_bp
        app.register_blueprint(ocr_bp, url_prefix="/ocr")
    except Exception:
        pass

    try:
        from .modules.media.routes import media_bp
        app.register_blueprint(media_bp, url_prefix="/media")
    except Exception:
        pass

    try:
        from .modules.cases import bp as cases_bp
        app.register_blueprint(cases_bp, url_prefix="/cases")
    except Exception:
        pass

    try:
        from .modules.complaints import bp as complaints_bp
        app.register_blueprint(complaints_bp, url_prefix="/complaints")
    except Exception:
        pass

    try:
        from .modules.settings import bp as settings_bp
        app.register_blueprint(settings_bp, url_prefix="/settings")
    except Exception:
        pass

    try:
        from .modules.attendance import bp as attendance_bp
        app.register_blueprint(attendance_bp, url_prefix="/attendance")
    except Exception:
        pass
    
    # Register notifications module
    try:
        from .modules.notifications import bp as notifications_bp
        app.register_blueprint(notifications_bp, url_prefix="/notifications")
    except Exception:
        pass

    # Register error handlers
    try:
        from .errors import register_error_handlers
        register_error_handlers(app)
    except Exception:
        pass

    # Add cache headers: long-cache for static, strict no-store for dynamic
    @app.after_request
    def add_no_cache_headers(response):
        """Set caching: static assets cached, dynamic content no-store"""
        if request.path.startswith('/static/'):
            response.headers["Cache-Control"] = "public, max-age=31536000, immutable"
        else:
            response.headers["Cache-Control"] = "no-store, no-cache, must-revalidate, post-check=0, pre-check=0, max-age=0"
            response.headers["Pragma"] = "no-cache"
            response.headers["Expires"] = "-1"
        return response

    return app
