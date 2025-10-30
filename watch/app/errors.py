from flask import render_template, current_app, request, session
import logging

def register_error_handlers(app):
    """Register secure error handlers that prevent information disclosure"""
    
    @app.errorhandler(400)
    def bad_request(e):
        """Handle bad request errors"""
        # Log the actual error for debugging
        current_app.logger.warning(f"Bad request: {str(e)}")
        
        # Return generic error to user
        return render_template("errors/400.html"), 400

    @app.errorhandler(401)
    def unauthorized(e):
        """Handle unauthorized access"""
        # Log unauthorized access attempt
        current_app.logger.warning(f"Unauthorized access attempt from IP: {request.remote_addr}")
        
        return render_template("errors/401.html"), 401

    @app.errorhandler(403)
    def forbidden(e):
        """Handle forbidden access"""
        # Log forbidden access attempt
        current_app.logger.warning(f"Forbidden access attempt from IP: {request.remote_addr}")
        
        return render_template("errors/403.html"), 403

    @app.errorhandler(404)
    def not_found(e):
        """Handle page not found errors"""
        # Log 404 for potential security scanning
        current_app.logger.info(f"404 error for path: {request.path} from IP: {request.remote_addr}")
        
        return render_template("errors/404.html"), 404

    @app.errorhandler(413)
    def file_too_large(e):
        """Handle file too large errors"""
        current_app.logger.warning(f"File too large upload attempt from IP: {request.remote_addr}")
        
        return render_template("errors/413.html"), 413

    @app.errorhandler(429)
    def rate_limit_exceeded(e):
        """Handle rate limiting errors"""
        current_app.logger.warning(f"Rate limit exceeded from IP: {request.remote_addr}")
        
        return render_template("errors/429.html"), 429

    @app.errorhandler(500)
    def internal_server_error(e):
        """Handle internal server errors securely"""
        # Log detailed error for debugging
        current_app.logger.error(f"Internal server error: {str(e)}")
        
        # Log additional context for debugging
        current_app.logger.error(f"Request URL: {request.url}")
        current_app.logger.error(f"Request method: {request.method}")
        current_app.logger.error(f"User agent: {request.headers.get('User-Agent', 'Unknown')}")
        
        # Return generic error to user
        return render_template("errors/500.html"), 500

    @app.errorhandler(Exception)
    def handle_unexpected_error(e):
        """Handle unexpected errors"""
        # Log the error
        current_app.logger.error(f"Unexpected error: {str(e)}", exc_info=True)
        
        # Return generic error
        return render_template("errors/500.html"), 500

    def log_security_error(error_type, details):
        """Log security-related errors"""
        current_app.logger.warning(f"SECURITY_ERROR: {error_type} - {details}")
        
        # Log to security log if available
        try:
            from .utils.security_logger import log_security_event
            log_security_event('ERROR', f"{error_type}: {details}")
        except:
            pass  # Don't fail if security logger is not available

