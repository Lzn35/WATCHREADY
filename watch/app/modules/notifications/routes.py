#!/usr/bin/env python3
"""
Notification Routes
Handles notification API endpoints
"""

from flask import jsonify, request
from ...auth_utils import login_required, get_current_user
from ...services.notification_service import NotificationService
from ...models import Notification, User, Role
from ...extensions import csrf
from . import bp

@bp.get('/api/notifications')
@csrf.exempt
def get_notifications():
    """Get notifications for the current user"""
    try:
        # Get current user - this should work for both admin and committee roles
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not authenticated'}), 401
        
        # Get notifications for the user
        notifications = NotificationService.get_user_notifications(user.id, limit=20)
        
        notifications_data = []
        for notification in notifications:
            # Calculate time ago
            time_ago = "Just now"
            if notification.created_at:
                from datetime import datetime, timezone
                now = datetime.now(timezone.utc)
                if notification.created_at.tzinfo is None:
                    # If notification.created_at is naive, assume UTC
                    created_at = notification.created_at.replace(tzinfo=timezone.utc)
                else:
                    created_at = notification.created_at
                
                diff = now - created_at
                if diff.days > 0:
                    time_ago = f"{diff.days} day{'s' if diff.days > 1 else ''} ago"
                elif diff.seconds > 3600:
                    hours = diff.seconds // 3600
                    time_ago = f"{hours} hour{'s' if hours > 1 else ''} ago"
                elif diff.seconds > 60:
                    minutes = diff.seconds // 60
                    time_ago = f"{minutes} minute{'s' if minutes > 1 else ''} ago"
                else:
                    time_ago = "Just now"
            
            notifications_data.append({
                'id': notification.id,
                'title': notification.title,
                'message': notification.message,
                'type': notification.notification_type,
                'is_read': notification.is_read,
                'created_at': notification.created_at.isoformat() if notification.created_at else None,
                'time_ago': time_ago,
                'redirect_url': notification.redirect_url
            })
        
        return jsonify({
            'notifications': notifications_data,
            'unread_count': NotificationService.get_unread_count(user.id)
        })
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.post('/api/notifications/<int:notification_id>/read')
@csrf.exempt
@login_required
def mark_notification_read(notification_id):
    """Mark a notification as read"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        success = NotificationService.mark_as_read(notification_id, user.id)
        if success:
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Notification not found'}), 404
            
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.post('/api/notifications/mark-all-read')
@csrf.exempt
@login_required
def mark_all_notifications_read():
    """Mark all notifications as read for the current user"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        NotificationService.mark_all_as_read(user.id)
        return jsonify({'success': True})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@bp.post('/api/notifications/delete-all')
@csrf.exempt
@login_required
def delete_all_notifications():
    """Delete all notifications for the current user"""
    try:
        user = get_current_user()
        if not user:
            return jsonify({'error': 'User not found'}), 401
        
        # Delete all notifications for the user
        from ...extensions import db
        deleted_count = Notification.query.filter_by(user_id=user.id).delete()
        db.session.commit()
        
        return jsonify({'success': True, 'deleted_count': deleted_count})
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500
