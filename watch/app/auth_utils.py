"""Authentication utilities for Flask WATCH system"""

from functools import wraps
from flask import session, redirect, url_for, request, g, flash
from .models import User


def login_required(f):
    """Decorator to require authentication for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Save the page they were trying to access
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function


def admin_required(f):
    """Decorator to require admin role for routes"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            # Not logged in
            session['next_url'] = request.url
            return redirect(url_for('auth.login'))
        
        # Get current user
        user = User.query.get(session['user_id'])
        if not user:
            flash('User not found. Please log in again.', 'error')
            return redirect(url_for('auth.login'))
        
        # Check if user is admin
        if not user.is_admin():
            flash('Access Denied. This feature is only available to administrators.', 'error')
            return redirect(url_for('core.dashboard'))
        
        return f(*args, **kwargs)
    return decorated_function


def load_user():
    """Load current user from session"""
    user_id = session.get('user_id')
    if user_id:
        g.current_user = User.query.get(user_id)
    else:
        g.current_user = None


def is_authenticated():
    """Check if current user is authenticated"""
    # Check if user_id exists in session and is not None
    if 'user_id' not in session or session['user_id'] is None:
        return False
    
    # Additional security: Verify user still exists in database
    try:
        user_id = session.get('user_id')
        user = User.query.get(user_id)
        return user is not None
    except:
        # If there's any database error, consider user not authenticated
        return False


def get_current_user():
    """Get the current authenticated user"""
    if hasattr(g, 'current_user'):
        return g.current_user
    return None


def login_user(user, remember=False):
    """Log in a user by setting session
    
    Args:
        user: User object to log in
        remember: If True, session persists across browser restarts. 
                  If False (default), session expires when browser/tab closes.
    """
    session['user_id'] = user.id
    session['username'] = user.username
    # Only make session permanent if "Remember Me" is checked
    # Default: session expires when browser/tab closes
    session.permanent = remember


def logout_user():
    """Log out the current user by clearing session"""
    # Clear specific session keys first
    session.pop('user_id', None)
    session.pop('username', None)
    session.pop('next_url', None)
    
    # Clear entire session for security
    session.clear()
    
    # Mark session as not permanent
    session.permanent = False
