#!/usr/bin/env python3
"""
Notification Tracker Decorator
Automatically tracks user actions and sends notifications
"""

from functools import wraps
from flask import request, session
from watch.app.services.notification_service import NotificationService
from watch.app.models import User

def track_action(action_type, action_name):
    """
    Decorator to track user actions and send notifications
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # Get current user
            current_user_id = session.get('user_id')
            if not current_user_id:
                return f(*args, **kwargs)
            
            current_user = User.query.get(current_user_id)
            if not current_user:
                return f(*args, **kwargs)
            
            # Execute the original function
            result = f(*args, **kwargs)
            
            # Only send notifications for committee members (not admin)
            if current_user.username != 'discipline_officer':
                try:
                    # Send notification based on action type
                    if action_type == 'case':
                        case_type = kwargs.get('case_type', 'minor')
                        case_id = kwargs.get('case_id', None)
                        NotificationService.notify_case_action(
                            action=action_name,
                            case_type=case_type,
                            case_id=case_id,
                            action_user_name=current_user.full_name or current_user.username
                        )
                    elif action_type == 'appointment':
                        appointment_id = kwargs.get('appointment_id', None)
                        NotificationService.notify_appointment_action(
                            action=action_name,
                            appointment_id=appointment_id,
                            action_user_name=current_user.full_name or current_user.username
                        )
                    elif action_type == 'attendance':
                        NotificationService.notify_attendance_action(
                            action=action_name,
                            action_user_name=current_user.full_name or current_user.username
                        )
                    elif action_type == 'system':
                        NotificationService.notify_system_action(
                            action=action_name,
                            action_user_name=current_user.full_name or current_user.username
                        )
                except Exception as e:
                    # Don't let notification errors break the main functionality
                    print(f"Notification error: {e}")
                    pass
            
            return result
        return decorated_function
    return decorator

def track_login_logout(action_name):
    """
    Special decorator for login/logout tracking
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            result = f(*args, **kwargs)
            
            # Get current user after login
            current_user_id = session.get('user_id')
            if current_user_id:
                current_user = User.query.get(current_user_id)
                if current_user and current_user.username != 'discipline_officer':
                    try:
                        NotificationService.notify_system_action(
                            action=action_name,
                            action_user_name=current_user.full_name or current_user.username
                        )
                    except Exception as e:
                        print(f"Notification error: {e}")
                        pass
            
            return result
        return decorated_function
    return decorator
