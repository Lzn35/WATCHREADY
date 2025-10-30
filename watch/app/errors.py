from flask import render_template
from .utils.safe_string import sanitize_error_message

def register_error_handlers(app):
    @app.errorhandler(404)
    def not_found(e):
        return render_template("errors/404.html"), 404

    @app.errorhandler(401)
    def unauthorized(e):
        return render_template("errors/401.html"), 401

    @app.errorhandler(500)
    def server_error(e):
        # In production, don't expose error details
        error_msg = str(e) if app.debug else "An internal server error occurred."
        # Log the actual error for debugging (won't be shown to user)
        if not app.debug:
            app.logger.error(f"500 Error: {str(e)}")
        return render_template("errors/500.html"), 500

