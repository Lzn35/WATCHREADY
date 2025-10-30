from flask import Flask
from .extensions import db, csrf, login_manager, limiter
from .config import Config
import os

def create_app(config_class=Config):
    """Application factory for WATCH Flask app."""
    app = Flask(__name__, static_folder='static', static_url_path='/static')
    app.config.from_object(config_class)
    
    # Ensure upload directory exists
    os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
    
    # Configure sessions - Auto logout when browser closes
    app.config['SESSION_TYPE'] = 'filesystem'
    app.config['SESSION_PERMANENT'] = False  # Session expires when browser closes
    app.config['SESSION_USE_SIGNER'] = True
    app.config['SESSION_KEY_PREFIX'] = 'watch:'

    # Initialize extensions
    db.init_app(app)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)
    
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
        try:
            from .auth_utils import load_user
            load_user()
        except Exception as e:
            print(f"⚠️ Error in before_request handler: {e}")
            import traceback
            traceback.print_exc()
            # Continue processing request even if user loading fails
    
    # Make current_user available in templates
    @app.context_processor
    def inject_user():
        try:
            from .auth_utils import get_current_user
            return dict(current_user=get_current_user())
        except Exception as e:
            print(f"⚠️ Error in context_processor: {e}")
            return dict(current_user=None)

    # Register blueprints
    try:
        from .routes import core_bp
        app.register_blueprint(core_bp)
    except Exception as e:
        print(f"Error registering core blueprint: {e}")

    try:
        from .modules.auth import bp as auth_bp
        app.register_blueprint(auth_bp, url_prefix='/auth')
    except Exception as e:
        print(f"Error registering auth blueprint: {e}")

    try:
        from .modules.cases import bp as cases_bp
        app.register_blueprint(cases_bp, url_prefix='/cases')
    except Exception as e:
        print(f"Error registering cases blueprint: {e}")

    try:
        from .modules.complaints import bp as complaints_bp
        app.register_blueprint(complaints_bp, url_prefix='/complaints')
    except Exception as e:
        print(f"Error registering complaints blueprint: {e}")

    try:
        from .modules.attendance import bp as attendance_bp
        app.register_blueprint(attendance_bp, url_prefix='/attendance')
    except Exception as e:
        print(f"Error registering attendance blueprint: {e}")

    try:
        from .modules.media import bp as media_bp
        app.register_blueprint(media_bp, url_prefix='/media')
    except Exception as e:
        print(f"Error registering media blueprint: {e}")

    try:
        from .modules.notifications import bp as notifications_bp
        app.register_blueprint(notifications_bp, url_prefix='/notifications')
    except Exception as e:
        print(f"Error registering notifications blueprint: {e}")

    try:
        from .modules.settings import bp as settings_bp
        app.register_blueprint(settings_bp, url_prefix='/settings')
    except Exception as e:
        print(f"Error registering settings blueprint: {e}")

    try:
        from .modules.ocr import bp as ocr_bp
        app.register_blueprint(ocr_bp, url_prefix='/ocr')
    except Exception as e:
        print(f"Error registering ocr blueprint: {e}")

    # Register error handlers
    try:
        from .errors import register_error_handlers
        register_error_handlers(app)
    except Exception as e:
        print(f"Error registering error handlers: {e}")

    # Add comprehensive error logging handler LAST (after all blueprints)
    @app.errorhandler(Exception)
    def handle_exception(e):
        """Handle all unhandled exceptions"""
        import traceback
        error_msg = str(e)
        traceback_str = traceback.format_exc()
        
        print(f"🚨 UNHANDLED EXCEPTION: {error_msg}")
        print(f"📋 TRACEBACK:\n{traceback_str}")
        
        # Log to file if possible
        try:
            import logging
            logging.basicConfig(level=logging.ERROR)
            logging.error(f"Unhandled exception: {error_msg}\n{traceback_str}")
        except:
            pass
        
        return """
        <!DOCTYPE html>
        <html>
        <head><title>500 - Server Error</title></head>
        <body>
            <h1>500 - Server Error</h1>
            <p>Something went wrong. Please try again later.</p>
            <p><a href="/">Return to Home</a></p>
        </body>
        </html>
        """, 500

    return app