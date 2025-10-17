"""
Security Event Logger for WATCH System
Tracks security-related events: admin protection, file uploads, access violations
"""

import logging
import os
from pathlib import Path
from logging.handlers import RotatingFileHandler
from datetime import datetime
from flask import request, session


class SecurityLogger:
    """Handles security event logging for the WATCH system"""
    
    def __init__(self, app=None):
        self.logger = None
        if app:
            self.init_app(app)
    
    def init_app(self, app):
        """Initialize security logging for Flask app"""
        # Create logs directory if it doesn't exist
        log_dir = Path(app.root_path).parent / 'logs'
        log_dir.mkdir(exist_ok=True)
        
        # Setup security logger
        self.logger = logging.getLogger('watch.security')
        self.logger.setLevel(logging.INFO)
        
        # Prevent duplicate handlers
        if not self.logger.handlers:
            # Security log file with rotation
            security_log_file = log_dir / 'security.log'
            security_handler = RotatingFileHandler(
                security_log_file,
                maxBytes=10 * 1024 * 1024,  # 10 MB
                backupCount=10
            )
            security_handler.setLevel(logging.INFO)
            
            # Detailed formatter for security events
            formatter = logging.Formatter(
                '[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S'
            )
            security_handler.setFormatter(formatter)
            
            self.logger.addHandler(security_handler)
        
        app.logger.info("Security logging initialized")
    
    def _get_request_info(self):
        """Get current request information safely"""
        try:
            return {
                'ip': request.remote_addr if request else 'N/A',
                'user_agent': request.headers.get('User-Agent', 'N/A') if request else 'N/A',
                'endpoint': request.endpoint if request else 'N/A',
                'user_id': session.get('user_id', 'N/A') if session else 'N/A',
                'username': session.get('username', 'N/A') if session else 'N/A'
            }
        except RuntimeError:
            # Outside request context
            return {
                'ip': 'N/A',
                'user_agent': 'N/A',
                'endpoint': 'N/A',
                'user_id': 'N/A',
                'username': 'N/A'
            }
    
    def log_admin_protection(self, action, target_user_id, target_username, reason):
        """
        Log attempts to modify/delete protected admin accounts
        
        Args:
            action: Action attempted (e.g., 'DELETE', 'MODIFY')
            target_user_id: ID of the protected user
            target_username: Username of the protected user
            reason: Reason protection triggered
        """
        if not self.logger:
            return
        
        info = self._get_request_info()
        self.logger.warning(
            f"ADMIN_PROTECTION | Action: {action} | Target: {target_username} (ID:{target_user_id}) | "
            f"Reason: {reason} | User: {info['username']} (ID:{info['user_id']}) | "
            f"IP: {info['ip']} | Endpoint: {info['endpoint']}"
        )
    
    def log_file_upload(self, filename, file_size, file_type, case_id=None, uploader_id=None, uploader_name=None):
        """
        Log file upload events
        
        Args:
            filename: Original filename
            file_size: File size in bytes
            file_type: MIME type
            case_id: Associated case ID (optional)
            uploader_id: User ID who uploaded
            uploader_name: Username who uploaded
        """
        if not self.logger:
            return
        
        info = self._get_request_info()
        size_mb = file_size / (1024 * 1024)
        
        self.logger.info(
            f"FILE_UPLOAD | File: {filename} | Size: {size_mb:.2f}MB | Type: {file_type} | "
            f"Case: {case_id or 'N/A'} | Uploader: {uploader_name or info['username']} (ID:{uploader_id or info['user_id']}) | "
            f"IP: {info['ip']}"
        )
    
    def log_file_deletion(self, filename, case_id=None, deleter_id=None, deleter_name=None):
        """
        Log file deletion events
        
        Args:
            filename: Filename deleted
            case_id: Associated case ID (optional)
            deleter_id: User ID who deleted
            deleter_name: Username who deleted
        """
        if not self.logger:
            return
        
        info = self._get_request_info()
        
        self.logger.info(
            f"FILE_DELETE | File: {filename} | Case: {case_id or 'N/A'} | "
            f"Deleter: {deleter_name or info['username']} (ID:{deleter_id or info['user_id']}) | "
            f"IP: {info['ip']}"
        )
    
    def log_access_denied(self, resource, reason):
        """
        Log access denied events
        
        Args:
            resource: Resource that was denied
            reason: Reason for denial
        """
        if not self.logger:
            return
        
        info = self._get_request_info()
        
        self.logger.warning(
            f"ACCESS_DENIED | Resource: {resource} | Reason: {reason} | "
            f"User: {info['username']} (ID:{info['user_id']}) | IP: {info['ip']} | "
            f"Endpoint: {info['endpoint']}"
        )
    
    def log_suspicious_activity(self, activity_type, details):
        """
        Log suspicious activity
        
        Args:
            activity_type: Type of suspicious activity
            details: Additional details
        """
        if not self.logger:
            return
        
        info = self._get_request_info()
        
        self.logger.warning(
            f"SUSPICIOUS_ACTIVITY | Type: {activity_type} | Details: {details} | "
            f"User: {info['username']} (ID:{info['user_id']}) | IP: {info['ip']} | "
            f"User-Agent: {info['user_agent']}"
        )
    
    def log_security_event(self, event_type, message):
        """
        Log general security event
        
        Args:
            event_type: Type of event
            message: Event message
        """
        if not self.logger:
            return
        
        info = self._get_request_info()
        
        self.logger.info(
            f"SECURITY_EVENT | Type: {event_type} | Message: {message} | "
            f"User: {info['username']} (ID:{info['user_id']}) | IP: {info['ip']}"
        )


# Global security logger instance
security_logger = SecurityLogger()


# Convenience functions
def log_admin_protection(action, target_user_id, target_username, reason):
    """Convenience function for admin protection logging"""
    security_logger.log_admin_protection(action, target_user_id, target_username, reason)


def log_file_upload(filename, file_size, file_type, case_id=None, uploader_id=None, uploader_name=None):
    """Convenience function for file upload logging"""
    security_logger.log_file_upload(filename, file_size, file_type, case_id, uploader_id, uploader_name)


def log_file_deletion(filename, case_id=None, deleter_id=None, deleter_name=None):
    """Convenience function for file deletion logging"""
    security_logger.log_file_deletion(filename, case_id, deleter_id, deleter_name)


def log_access_denied(resource, reason):
    """Convenience function for access denied logging"""
    security_logger.log_access_denied(resource, reason)


def log_suspicious_activity(activity_type, details):
    """Convenience function for suspicious activity logging"""
    security_logger.log_suspicious_activity(activity_type, details)


def log_security_event(event_type, message):
    """Convenience function for security events"""
    security_logger.log_security_event(event_type, message)

