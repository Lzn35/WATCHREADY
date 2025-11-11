"""Session timeout middleware for WATCH system
Implements automatic session expiration after 10 minutes of inactivity
"""

from flask import session, redirect, url_for, flash, request
from datetime import datetime, timedelta
from functools import wraps

# Session timeout duration (in minutes) - Panel recommendation: 5-10 minutes
SESSION_TIMEOUT_MINUTES = 10

def check_session_timeout():
    """
    Check if user session has timed out due to inactivity
    
    Returns:
        bool: True if session has timed out, False otherwise
    """
    if 'user_id' in session:
        last_activity = session.get('last_activity')
        
        if last_activity:
            try:
                # Parse last activity time
                last_activity_time = datetime.fromisoformat(last_activity)
                now = datetime.utcnow()
                
                # Calculate time difference
                time_diff = now - last_activity_time
                timeout_duration = timedelta(minutes=SESSION_TIMEOUT_MINUTES)
                
                if time_diff > timeout_duration:
                    # Session has timed out
                    username = session.get('username', 'User')
                    
                    # Log timeout before clearing session
                    try:
                        from ..models import AuditLog
                        AuditLog.log_activity(
                            action_type='Session Timeout',
                            description=f'User {username} session timed out after {SESSION_TIMEOUT_MINUTES} minutes of inactivity',
                            user_id=session.get('user_id'),
                            ip_address=request.remote_addr if request else None
                        )
                    except:
                        pass  # Don't let logging errors break the timeout
                    
                    # Clear session
                    session.clear()
                    
                    # Flash timeout message
                    flash(f'Your session has timed out due to inactivity ({SESSION_TIMEOUT_MINUTES} minutes). Please login again.', 'warning')
                    return True
                else:
                    # Update last activity time
                    session['last_activity'] = now.isoformat()
                    return False
            except (ValueError, TypeError):
                # If there's any error parsing the time, reset it
                session['last_activity'] = datetime.utcnow().isoformat()
                return False
        else:
            # Set initial last activity if not present
            session['last_activity'] = datetime.utcnow().isoformat()
            return False
    
    return False


def session_timeout_required(f):
    """
    Decorator to check session timeout on protected routes
    Can be used as an additional layer on top of login_required
    """
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if check_session_timeout():
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    return decorated_function




