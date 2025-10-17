"""
Security Headers Middleware for WATCH System
Adds essential security headers to all HTTP responses
"""

from flask import Flask
import os


class SecurityHeadersMiddleware:
    """
    WSGI middleware to add security headers to all responses.
    
    Headers added:
    - X-Frame-Options: Prevent clickjacking
    - X-Content-Type-Options: Prevent MIME sniffing
    - X-XSS-Protection: Enable XSS filter
    - Referrer-Policy: Control referrer information
    - Content-Security-Policy: Control resource loading (basic policy)
    """
    
    def __init__(self, app=None):
        self.app = app
        if app:
            self.init_app(app)
    
    def init_app(self, app: Flask):
        """Initialize security headers for Flask app"""
        
        @app.after_request
        def add_security_headers(response):
            """Add security headers to every response"""
            
            # Prevent clickjacking attacks
            if 'X-Frame-Options' not in response.headers:
                response.headers['X-Frame-Options'] = 'SAMEORIGIN'
            
            # Prevent MIME type sniffing
            if 'X-Content-Type-Options' not in response.headers:
                response.headers['X-Content-Type-Options'] = 'nosniff'
            
            # Enable XSS protection in older browsers
            if 'X-XSS-Protection' not in response.headers:
                response.headers['X-XSS-Protection'] = '1; mode=block'
            
            # Control referrer information
            if 'Referrer-Policy' not in response.headers:
                response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
            
            # Enhanced Content Security Policy
            # This policy allows Google Analytics, CDN resources, and necessary functionality
            if 'Content-Security-Policy' not in response.headers:
                csp_policy = (
                    "default-src 'self' 'unsafe-inline' 'unsafe-eval' https: data:; "
                    "script-src 'self' 'unsafe-inline' 'unsafe-eval' https: http: data: https://www.googletagmanager.com https://www.google-analytics.com https://cdnjs.cloudflare.com http://cdnjs.cloudflare.com; "
                    "script-src-elem 'self' 'unsafe-inline' https: http: https://www.googletagmanager.com https://www.google-analytics.com https://cdnjs.cloudflare.com http://cdnjs.cloudflare.com; "
                    "style-src 'self' 'unsafe-inline' https: data: https://fonts.googleapis.com; "
                    "font-src 'self' https: data: https://fonts.gstatic.com; "
                    "img-src 'self' data: https: https://www.google-analytics.com; "
                    "connect-src 'self' https://www.google-analytics.com https://www.googletagmanager.com; "
                    "frame-src 'self' https:; "
                    "object-src 'none'; "
                    "base-uri 'self';"
                )
                response.headers['Content-Security-Policy'] = csp_policy
            
            # Permissions Policy (formerly Feature-Policy)
            if 'Permissions-Policy' not in response.headers:
                response.headers['Permissions-Policy'] = (
                    "geolocation=(), "
                    "microphone=(), "
                    "camera=()"
                )

            # HSTS - only enable when explicitly set (i.e., under HTTPS in prod)
            if os.getenv('ENABLE_HSTS', 'False').lower() in ("1", "true", "yes"):
                response.headers['Strict-Transport-Security'] = 'max-age=31536000; includeSubDomains; preload'
            
            return response
        
        app.logger.info("Security headers middleware initialized")


def init_security_headers(app: Flask):
    """
    Convenience function to initialize security headers.
    
    Args:
        app: Flask application instance
    """
    middleware = SecurityHeadersMiddleware(app)
    return middleware

