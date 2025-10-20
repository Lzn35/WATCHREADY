#!/usr/bin/env python3
"""
Notification Service for WATCH System
Handles transparent notifications between Discipline Officer and Discipline Committee
"""

from datetime import datetime
from ..extensions import db
from ..models import Notification, User, Role

class NotificationService:
    """Service for managing notifications with transparency logic"""
    
    @staticmethod
    def create_admin_notification(title, message, notification_type, reference_id=None, redirect_url=None, action_user=None):
        """
        Create notification for Discipline Officer (Admin) to see all actions
        """
        # Find all admin users (discipline officers)
        admin_role = Role.query.filter_by(name='Admin').first()
        if not admin_role:
            return None
        
        admin_users = User.query.filter_by(role_id=admin_role.id).all()
        if not admin_users:
            return None
        
        # Create notifications for all admin users
        notifications = []
        for admin_user in admin_users:
            # Use message as is (no role prefix needed)
            full_message = message
            
            notification = Notification(
                title=title,
                message=full_message,
                notification_type=notification_type,
                reference_id=reference_id,
                redirect_url=redirect_url,
                user_id=admin_user.id,
                is_read=False
            )
            notifications.append(notification)
        
        db.session.add_all(notifications)
        db.session.commit()
        return notifications
    
    @staticmethod
    def create_committee_notification(title, message, notification_type, reference_id=None, redirect_url=None, committee_user_id=None):
        """
        Create notification for Discipline Committee (only appointment-related)
        """
        if notification_type != 'appointment':
            # Committee only sees appointment notifications
            return None
        
        notification = Notification(
            title=title,
            message=message,
            notification_type=notification_type,
            reference_id=reference_id,
            redirect_url=redirect_url,
            user_id=committee_user_id,
            is_read=False
        )
        
        db.session.add(notification)
        db.session.commit()
        return notification
    
    @staticmethod
    def notify_case_action(action, case_type, case_id, action_user_name, case_details=None):
        """
        Notify admin when committee member performs case actions
        """
        if action == 'created':
            title = f"New {case_type.title()} Case Added"
            message = f"has added a new {case_type} case"
            redirect_url = None  # No redirect, just show notification
        elif action == 'updated':
            title = f"{case_type.title()} Case Updated"
            message = f"has updated a {case_type} case"
            redirect_url = None  # No redirect, just show notification
        elif action == 'deleted':
            title = f"{case_type.title()} Case Deleted"
            message = f"has deleted a {case_type} case"
            redirect_url = None  # No redirect, just show notification
        else:
            return None
        
        return NotificationService.create_admin_notification(
            title=title,
            message=message,
            notification_type='case',
            reference_id=case_id,
            redirect_url=redirect_url,
            action_user=action_user_name
        )
    
    @staticmethod
    def notify_appointment_action(action, appointment_id, action_user_name, appointment_details=None):
        """
        Notify both admin and committee for appointment actions
        """
        if action == 'created':
            title = "New Appointment Request"
            # Enhanced message with person's name, type, and time
            if appointment_details:
                person_name = appointment_details.get('full_name', 'Unknown')
                appointment_type = appointment_details.get('appointment_type', 'Unknown')
                appointment_time = appointment_details.get('appointment_date', 'Unknown')
                message = f"{person_name} requested a {appointment_type} appointment for {appointment_time}"
            else:
                message = f"{action_user_name} has scheduled a new appointment"
            redirect_url = "/complaints/appointments"  # Redirect to appointments page
        elif action == 'confirmed':
            title = "Appointment Confirmed"
            if appointment_details:
                person_name = appointment_details.get('full_name', 'Unknown')
                appointment_type = appointment_details.get('appointment_type', 'Unknown')
                appointment_time = appointment_details.get('appointment_date', 'Unknown')
                message = f"{person_name}'s {appointment_type} appointment for {appointment_time} has been confirmed"
            else:
                message = f"{action_user_name} has confirmed an appointment"
            redirect_url = "/complaints/appointments"  # Redirect to appointments page
        elif action == 'rescheduled':
            title = "Appointment Rescheduled"
            if appointment_details:
                person_name = appointment_details.get('full_name', 'Unknown')
                appointment_type = appointment_details.get('appointment_type', 'Unknown')
                appointment_time = appointment_details.get('appointment_date', 'Unknown')
                message = f"{person_name}'s {appointment_type} appointment has been rescheduled to {appointment_time}"
            else:
                message = f"{action_user_name} has rescheduled an appointment"
            redirect_url = "/complaints/appointments"  # Redirect to appointments page
        elif action == 'cancelled':
            title = "Appointment Cancelled"
            if appointment_details:
                person_name = appointment_details.get('full_name', 'Unknown')
                appointment_type = appointment_details.get('appointment_type', 'Unknown')
                appointment_time = appointment_details.get('appointment_date', 'Unknown')
                message = f"{person_name}'s {appointment_type} appointment for {appointment_time} has been cancelled"
            else:
                message = f"{action_user_name} has cancelled an appointment"
            redirect_url = "/complaints/appointments"  # Redirect to appointments page
        else:
            return None
        
        # Notify admin
        admin_notification = NotificationService.create_admin_notification(
            title=title,
            message=message,
            notification_type='appointment',
            reference_id=appointment_id,
            redirect_url=redirect_url,
            action_user=action_user_name
        )
        
        # Notify all committee members (only appointment notifications)
        committee_role = Role.query.filter_by(name='User').first()  # Assuming 'User' role is for committee
        if committee_role:
            committee_users = User.query.filter_by(role_id=committee_role.id).all()
            for committee_user in committee_users:
                NotificationService.create_committee_notification(
                    title=title,
                    message=message,
                    notification_type='appointment',
                    reference_id=appointment_id,
                    redirect_url=redirect_url,
                    committee_user_id=committee_user.id
                )
        
        return admin_notification
    
    @staticmethod
    def notify_attendance_action(action, action_user_name, attendance_details=None):
        """
        Notify admin when committee member performs attendance actions
        """
        if action == 'marked':
            title = "Attendance Marked"
            message = f"has marked attendance"
            redirect_url = None  # No redirect, just show notification
        elif action == 'updated':
            title = "Attendance Updated"
            message = f"has updated attendance records"
            redirect_url = None  # No redirect, just show notification
        else:
            return None
        
        return NotificationService.create_admin_notification(
            title=title,
            message=message,
            notification_type='attendance',
            redirect_url=redirect_url,
            action_user=action_user_name
        )
    
    @staticmethod
    def notify_system_action(action, action_user_name, details=None):
        """
        Notify admin when committee member performs system actions
        """
        if action == 'login':
            title = "System Access"
            message = f"has logged into the system"
            redirect_url = None  # No redirect, just show notification
        elif action == 'logout':
            title = "System Access"
            message = f"has logged out of the system"
            redirect_url = None  # No redirect, just show notification
        elif action == 'profile_updated':
            title = "Profile Updated"
            message = f"has updated their profile"
            redirect_url = None  # No redirect, just show notification
        else:
            return None
        
        return NotificationService.create_admin_notification(
            title=title,
            message=message,
            notification_type='system',
            redirect_url=redirect_url,
            action_user=action_user_name
        )
    
    @staticmethod
    def get_user_notifications(user_id, limit=10):
        """
        Get notifications for a specific user
        """
        return Notification.query.filter_by(user_id=user_id).order_by(Notification.created_at.desc()).limit(limit).all()
    
    @staticmethod
    def get_unread_count(user_id):
        """
        Get count of unread notifications for a user
        """
        return Notification.query.filter_by(user_id=user_id, is_read=False).count()
    
    @staticmethod
    def mark_as_read(notification_id, user_id):
        """
        Mark a notification as read
        """
        notification = Notification.query.filter_by(id=notification_id, user_id=user_id).first()
        if notification:
            notification.is_read = True
            db.session.commit()
            return True
        return False
    
    @staticmethod
    def mark_all_as_read(user_id):
        """
        Mark all notifications as read for a user
        """
        Notification.query.filter_by(user_id=user_id, is_read=False).update({'is_read': True})
        db.session.commit()
        return True
