"""
Email service for sending appointment notifications.
Supports Gmail and Outlook SMTP for actual email sending.
"""

import logging
import smtplib
import socket
import threading
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import Optional
from ..models import Appointment, User, EmailSettings

logger = logging.getLogger(__name__)

# SMTP Configuration for different providers
SMTP_CONFIG = {
    'gmail': {
        'name': 'Gmail',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_tls': True,
    },
    'outlook': {
        'name': 'Outlook/Microsoft 365',
        'smtp_server': 'smtp.office365.com',
        'smtp_port': 587,
        'use_tls': True,
    },
    'outlook_ssl': {
        'name': 'Outlook (SSL Port 465)',
        'smtp_server': 'smtp.office365.com',
        'smtp_port': 465,
        'use_tls': False,
        'use_ssl': True,
    },
    'outlook_legacy': {
        'name': 'Outlook (Legacy)',
        'smtp_server': 'smtp-mail.outlook.com',
        'smtp_port': 587,
        'use_tls': True,
    }
}

class EmailService:
    """Email service for appointment notifications"""
    
    @staticmethod
    def _send_email_sync(to_email: str, subject: str, body: str, from_name: str = None, from_email: str = None) -> bool:
        """
        Send an email using SMTP (Gmail or Outlook)
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            from_name: Sender's display name
            from_email: Sender's email address (overrides config)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get email settings from database
            try:
                email_settings = EmailSettings.get_settings()
            except Exception as e:
                logger.error(f"Failed to get email settings: {e}")
                print(f"❌ Error loading email settings: {e}")
                return False
            
            # Check if email is configured
            try:
                is_configured = email_settings.is_configured()
            except Exception as e:
                logger.error(f"Failed to check email configuration: {e}")
                print(f"❌ Error checking email configuration: {e}")
                return False
            
            if not is_configured:
                logger.warning("Email not configured - email will only be logged to console")
                print(f"\n{'='*60}")
                print(f"EMAIL NOT SENT (Email not configured)")
                print(f"{'='*60}")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Body:\n{body}")
                print(f"\nTIP: Configure email in Settings > System Settings > Email Configuration")
                print(f"{'='*60}\n")
                return False
            
            # Get SMTP configuration
            provider = email_settings.provider
            smtp_config = SMTP_CONFIG.get(provider, SMTP_CONFIG['gmail'])
            
            # Use provided email or database email
            sender_email = from_email or email_settings.sender_email
            sender_name = from_name or email_settings.sender_name
            
            # Get password for current provider
            try:
                sender_password = email_settings.get_current_password()
            except Exception as e:
                logger.error(f"Failed to get email password: {e}")
                print(f"❌ Error getting email password: {e}")
                return False
            
            # Validate password exists
            if not sender_password:
                logger.error("Email password is empty or not configured")
                print(f"\n{'='*60}")
                print(f"EMAIL NOT SENT: Password is missing or empty")
                print(f"Provider: {email_settings.provider}")
                print(f"Email: {sender_email}")
                print(f"\nTIP: Make sure you've entered the App Password in Email Configuration")
                print(f"{'='*60}\n")
                return False
            
            # Create message
            message = MIMEMultipart()
            message['From'] = f"{sender_name} <{sender_email}>"
            message['To'] = to_email
            message['Subject'] = subject
            
            # Attach body
            message.attach(MIMEText(body, 'plain'))
            
            # Connect to SMTP server and send (with reduced timeout for faster failure)
            print(f"\n{'='*60}")
            print(f"SENDING EMAIL via {smtp_config['name']} (background thread)")
            print(f"Server: {smtp_config['smtp_server']}:{smtp_config['smtp_port']}")
            print(f"From: {sender_name} <{sender_email}>")
            print(f"To: {to_email}")
            print(f"Use TLS: {smtp_config.get('use_tls', False)}")
            print(f"Use SSL: {smtp_config.get('use_ssl', False)}")
            print(f"{'='*60}")
            
            # Use SSL or TLS based on configuration (with shorter timeout for faster response)
            # Reduced timeout since it's now in background thread
            if smtp_config.get('use_ssl'):
                # Use SMTP_SSL for port 465 (with timeout)
                server = smtplib.SMTP_SSL(smtp_config['smtp_server'], smtp_config['smtp_port'], timeout=15)
                server.login(sender_email, sender_password)
                server.send_message(message)
                server.quit()
            else:
                # Use regular SMTP with STARTTLS for port 587 (with timeout)
                with smtplib.SMTP(smtp_config['smtp_server'], smtp_config['smtp_port'], timeout=15) as server:
                    if smtp_config['use_tls']:
                        server.starttls()
                    
                    # Login
                    server.login(sender_email, sender_password)
                    
                    # Send email
                    server.send_message(message)
            
            print(f"EMAIL SENT SUCCESSFULLY!")
            print(f"From: {sender_name} <{sender_email}>")
            print(f"To: {to_email}")
            print(f"Subject: {subject}")
            print(f"{'='*60}\n")
            
            logger.info(f"Email sent successfully to {to_email}")
            return True
            
        except smtplib.SMTPAuthenticationError as e:
            logger.error(f"SMTP Authentication failed: {e}")
            print(f"\nEMAIL SEND FAILED: Authentication Error")
            print(f"Error: {str(e)}")
            
            # Check if it's Gmail and provide specific guidance
            if email_settings.provider == 'gmail':
                print(f"\nGmail Authentication Troubleshooting:")
                print(f"1. Make sure you're using an App Password (16 characters)")
                print(f"2. Enable 2-Step Verification in your Google account")
                print(f"3. Generate App Password for 'Mail' application")
                print(f"4. Don't use your regular Gmail password")
            else:
                print(f"Please check your email credentials or request App Password from IT")
            print()
            return False
            
        except (smtplib.SMTPException, socket.timeout, TimeoutError) as e:
            logger.error(f"SMTP/Network Error: {e}")
            print(f"\nEMAIL SEND FAILED: SMTP/Network Error")
            print(f"Error: {str(e)}")
            print(f"This might be due to network timeout or SMTP server issue.")
            print()
            return False
            
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            print(f"\nEMAIL SEND FAILED: {str(e)}")
            print()
            return False
    
    @staticmethod
    def send_email(to_email: str, subject: str, body: str, from_name: str = None, from_email: str = None) -> bool:
        """
        Send an email asynchronously (non-blocking) using threading.
        Returns immediately - actual sending happens in background thread.
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            body: Email body (plain text)
            from_name: Sender's display name
            from_email: Sender's email address (overrides config)
            
        Returns:
            bool: True if email was queued successfully, False otherwise
        """
        try:
            # Check if email is configured first (quick check)
            email_settings = EmailSettings.get_settings()
            if not email_settings.is_configured():
                logger.warning("Email not configured - email will only be logged to console")
                print(f"\n{'='*60}")
                print(f"EMAIL NOT SENT (Email not configured)")
                print(f"{'='*60}")
                print(f"To: {to_email}")
                print(f"Subject: {subject}")
                print(f"Body:\n{body}")
                print(f"\nTIP: Configure email in Settings > System Settings > Email Configuration")
                print(f"{'='*60}\n")
                return False
            
            # Send email in background thread (non-blocking)
            def send_in_background():
                try:
                    EmailService._send_email_sync(to_email, subject, body, from_name, from_email)
                except Exception as e:
                    logger.error(f"Background email sending error: {e}")
                    print(f"❌ Background email error: {e}")
            
            # Start thread
            email_thread = threading.Thread(target=send_in_background, daemon=True)
            email_thread.start()
            
            logger.info(f"Email queued for sending to {to_email} (background thread)")
            print(f"📧 Email queued for sending to {to_email} (processing in background...)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to queue email: {e}")
            print(f"\nEMAIL QUEUE FAILED: {str(e)}")
            return False
    
    @staticmethod
    def send_appointment_confirmation(appointment: Appointment, sender_user: Optional[User] = None) -> bool:
        """
        Send confirmation email to student when appointment is confirmed
        
        Args:
            appointment: The confirmed appointment
            sender_user: The user who confirmed the appointment (Discipline Officer/Committee)
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get sender information
            sender_name = sender_user.full_name if sender_user and sender_user.full_name else "Discipline Office"
            sender_email = sender_user.email if sender_user and sender_user.email else None
            sender_title = sender_user.title if sender_user and sender_user.title else "Discipline Officer"
            
            # For display in email body
            email_settings_db = EmailSettings.get_settings()
            contact_email = sender_email or email_settings_db.sender_email or "discipline@school.edu"
            
            subject = f"Appointment Confirmed - {sender_title}"
            
            body = f"""
Dear {appointment.full_name},

Your appointment with the Discipline Office has been confirmed.

Appointment Details:
- Date & Time: {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}
- Type: {appointment.appointment_type}
- Appointment ID: APT-{str(appointment.id).zfill(3)}

Please arrive 5 minutes before your scheduled time.

If you need to reschedule or have any questions, please contact us at:
- Email: {contact_email}
- Contact Person: {sender_name}

Best regards,
{sender_name}
{sender_title}
            """.strip()
            
            # Send the actual email
            return EmailService.send_email(
                to_email=appointment.email,
                subject=subject,
                body=body,
                from_name=sender_name,
                from_email=sender_email
            )
            
        except Exception as e:
            logger.error(f"Failed to send confirmation email: {e}")
            return False
    
    @staticmethod
    def send_appointment_reschedule(appointment: Appointment, sender_user: Optional[User] = None, custom_message: str = None) -> bool:
        """
        Send reschedule email to student when appointment needs to be rescheduled
        
        Args:
            appointment: The appointment that needs rescheduling
            sender_user: The user who requested the reschedule (Discipline Officer/Committee)
            custom_message: Custom message with available times from discipline officer
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get sender information
            sender_name = sender_user.full_name if sender_user and sender_user.full_name else "Discipline Office"
            sender_email = sender_user.email if sender_user and sender_user.email else None
            sender_title = sender_user.title if sender_user and sender_user.title else "Discipline Officer"
            
            # For display in email body
            email_settings_db = EmailSettings.get_settings()
            contact_email = sender_email or email_settings_db.sender_email or "discipline@school.edu"
            
            subject = f"Appointment Reschedule Required - {sender_title}"
            
            # Use custom message if provided, otherwise use default template
            if custom_message:
                reschedule_info = custom_message
            else:
                reschedule_info = "Please scan the QR code at the Discipline Officer's office again to schedule a new appointment at a more convenient time."
            
            body = f"""
Dear {appointment.full_name},

Unfortunately, your appointment with the Discipline Office needs to be rescheduled.

Original Appointment Details:
- Date & Time: {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}
- Type: {appointment.appointment_type}
- Appointment ID: APT-{str(appointment.id).zfill(3)}

{reschedule_info}

For assistance or questions, you can contact us at:
- Email: {contact_email}
- Contact Person: {sender_name}

We apologize for any inconvenience.

Best regards,
{sender_name}
{sender_title}
            """.strip()
            
            # Send the actual email
            return EmailService.send_email(
                to_email=appointment.email,
                subject=subject,
                body=body,
                from_name=sender_name,
                from_email=sender_email
            )
            
        except Exception as e:
            logger.error(f"Failed to send reschedule email: {e}")
            return False
    
    @staticmethod
    def send_appointment_created(appointment: Appointment) -> bool:
        """
        Send acknowledgment email to student when appointment is created
        
        Args:
            appointment: The newly created appointment
            
        Returns:
            bool: True if email was sent successfully, False otherwise
        """
        try:
            # Get email settings for sender name and email
            email_settings_db = EmailSettings.get_settings()
            sender_name = email_settings_db.sender_name or "Discipline Office"
            contact_email = email_settings_db.sender_email or "discipline@school.edu"
            
            subject = "Appointment Request Received - Discipline Office"
            
            body = f"""
Dear {appointment.full_name},

Your appointment request has been received and is pending confirmation.

Appointment Details:
- Date & Time: {appointment.appointment_date.strftime('%B %d, %Y at %I:%M %p')}
- Type: {appointment.appointment_type}
- Status: Pending Confirmation
- Appointment ID: APT-{str(appointment.id).zfill(3)}

You will receive another email once your appointment is confirmed by the Discipline Officer.

If you have any questions, please contact us at: {contact_email}

Best regards,
{sender_name}
Discipline Office
            """.strip()
            
            # Send the actual email using saved email settings
            return EmailService.send_email(
                to_email=appointment.email,
                subject=subject,
                body=body,
                from_name=sender_name,
                from_email=None  # Use email from settings
            )
            
        except Exception as e:
            logger.error(f"Failed to send created email: {e}")
            return False
