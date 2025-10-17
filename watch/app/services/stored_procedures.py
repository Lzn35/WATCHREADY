"""
Stored Procedure-Style Functions for ACID-Compliant Database Operations
All functions implement proper transaction handling with rollback on errors.
"""

import logging
from datetime import datetime, date
from typing import Optional, Dict, Any, List
from sqlalchemy.exc import SQLAlchemyError
from ..extensions import db
from ..models import (
    User, Role, Person, Case, MinorCase, MajorCase,
    Appointment, Schedule, AttendanceChecklist, AttendanceHistory,
    AuditLog, ActivityLog, Notification, SystemSettings, EmailSettings
)

# Configure logging
logger = logging.getLogger(__name__)


class StoredProcedureError(Exception):
    """Custom exception for stored procedure errors"""
    pass


# ==================== USER MANAGEMENT ====================

def sp_add_user(username: str, password: str, role_name: str, 
                full_name: Optional[str] = None, email: Optional[str] = None,
                is_protected: bool = False) -> Dict[str, Any]:
    """
    Add a new user to the system.
    
    Args:
        username: Unique username for the user
        password: Plain text password (will be hashed)
        role_name: Role name (e.g., 'admin', 'user')
        full_name: Optional full name
        email: Optional email address
        is_protected: Whether the account is protected from deletion
        
    Returns:
        Dictionary with success status and user data or error message
    """
    try:
        # Validate role exists
        role = Role.query.filter_by(name=role_name).first()
        if not role:
            raise StoredProcedureError(f"Role '{role_name}' does not exist")
        
        # Check if username already exists
        existing_user = User.query.filter_by(username=username).first()
        if existing_user:
            raise StoredProcedureError(f"Username '{username}' already exists")
        
        # Create new user
        user = User(
            username=username,
            role_id=role.id,
            full_name=full_name,
            email=email,
            is_protected=is_protected,
            is_active=True
        )
        user.set_password(password)
        
        db.session.add(user)
        db.session.commit()
        
        logger.info(f"User created successfully: {username} (ID: {user.id})")
        
        return {
            'success': True,
            'user_id': user.id,
            'username': user.username,
            'message': 'User created successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_add_user: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_add_user: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_update_user(user_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update user information.
    
    Args:
        user_id: ID of the user to update
        update_data: Dictionary of fields to update
        
    Returns:
        Dictionary with success status and message
    """
    try:
        user = User.query.get(user_id)
        if not user:
            raise StoredProcedureError(f"User with ID {user_id} not found")
        
        # Update allowed fields
        allowed_fields = ['full_name', 'title', 'email', 'phone', 'gender', 
                         'gmail', 'outlook', 'is_active', 'role_id']
        
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(user, field):
                setattr(user, field, value)
        
        # Handle password update separately if provided
        if 'password' in update_data:
            user.set_password(update_data['password'])
        
        db.session.commit()
        
        logger.info(f"User updated successfully: ID {user_id}")
        
        return {
            'success': True,
            'user_id': user.id,
            'message': 'User updated successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_update_user: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_update_user: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_delete_user(user_id: int, force: bool = False) -> Dict[str, Any]:
    """
    Delete a user from the system.
    
    Args:
        user_id: ID of the user to delete
        force: If True, bypass protection checks (use with caution)
        
    Returns:
        Dictionary with success status and message
    """
    try:
        user = User.query.get(user_id)
        if not user:
            raise StoredProcedureError(f"User with ID {user_id} not found")
        
        # Check if user is protected
        if user.is_protected and not force:
            raise StoredProcedureError("Cannot delete protected user account")
        
        username = user.username
        db.session.delete(user)
        db.session.commit()
        
        logger.info(f"User deleted successfully: {username} (ID: {user_id})")
        
        return {
            'success': True,
            'message': f'User {username} deleted successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_delete_user: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_delete_user: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


# ==================== PERSON MANAGEMENT ====================

def sp_add_person(full_name: str, role: str, program_or_dept: Optional[str] = None,
                 section: Optional[str] = None, first_name: Optional[str] = None,
                 last_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Add a new person (student, faculty, or staff).
    
    Args:
        full_name: Full name of the person
        role: Role type ('student', 'faculty', 'staff')
        program_or_dept: Program for students or department for faculty/staff
        section: Section (required for students)
        first_name: First name (optional, parsed from full_name if not provided)
        last_name: Last name (optional, parsed from full_name if not provided)
        
    Returns:
        Dictionary with success status and person data
    """
    try:
        # Validate role
        if role not in ['student', 'faculty', 'staff']:
            raise StoredProcedureError(f"Invalid role: {role}")
        
        # Check if person already exists
        existing_person = Person.query.filter_by(
            full_name=full_name,
            role=role
        ).first()
        
        if existing_person:
            raise StoredProcedureError(f"Person '{full_name}' with role '{role}' already exists")
        
        # Create new person
        person = Person(
            full_name=full_name,
            first_name=first_name,
            last_name=last_name,
            role=role,
            program_or_dept=program_or_dept,
            section=section if role == 'student' else None
        )
        
        db.session.add(person)
        db.session.commit()
        
        logger.info(f"Person created successfully: {full_name} (ID: {person.id})")
        
        return {
            'success': True,
            'person_id': person.id,
            'full_name': person.full_name,
            'message': 'Person created successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_add_person: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_add_person: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_update_person(person_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
    """
    Update person information.
    
    Args:
        person_id: ID of the person to update
        update_data: Dictionary of fields to update
        
    Returns:
        Dictionary with success status and message
    """
    try:
        person = Person.query.get(person_id)
        if not person:
            raise StoredProcedureError(f"Person with ID {person_id} not found")
        
        # Update allowed fields
        allowed_fields = ['full_name', 'first_name', 'last_name', 'role',
                         'program_or_dept', 'section']
        
        for field, value in update_data.items():
            if field in allowed_fields and hasattr(person, field):
                setattr(person, field, value)
        
        db.session.commit()
        
        logger.info(f"Person updated successfully: ID {person_id}")
        
        return {
            'success': True,
            'person_id': person.id,
            'message': 'Person updated successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_update_person: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_update_person: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_delete_person(person_id: int, cascade: bool = False) -> Dict[str, Any]:
    """
    Delete a person from the system.
    
    Args:
        person_id: ID of the person to delete
        cascade: If True, also delete all associated cases
        
    Returns:
        Dictionary with success status and message
    """
    try:
        person = Person.query.get(person_id)
        if not person:
            raise StoredProcedureError(f"Person with ID {person_id} not found")
        
        # Check for associated cases
        case_count = Case.query.filter_by(person_id=person_id).count()
        if case_count > 0 and not cascade:
            raise StoredProcedureError(
                f"Cannot delete person with {case_count} associated case(s). "
                "Use cascade=True to delete all cases as well."
            )
        
        full_name = person.full_name
        db.session.delete(person)
        db.session.commit()
        
        logger.info(f"Person deleted successfully: {full_name} (ID: {person_id})")
        
        return {
            'success': True,
            'message': f'Person {full_name} deleted successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_delete_person: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_delete_person: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


# ==================== CASE MANAGEMENT ====================

def sp_add_case(person_id: int, case_type: str, description: Optional[str] = None,
               date_reported: Optional[date] = None, status: str = 'open',
               remarks: Optional[str] = None, attachment_data: Optional[Dict] = None) -> Dict[str, Any]:
    """
    Add a new case for a person.
    
    Args:
        person_id: ID of the person the case is for
        case_type: Type of case ('minor' or 'major')
        description: Description of the case
        date_reported: Date the case was reported (defaults to today)
        status: Case status (defaults to 'open')
        remarks: Additional remarks
        attachment_data: Optional dictionary with attachment info (filename, path, size, type)
        
    Returns:
        Dictionary with success status and case data
    """
    try:
        # Validate person exists
        person = Person.query.get(person_id)
        if not person:
            raise StoredProcedureError(f"Person with ID {person_id} not found")
        
        # Validate case type
        if case_type not in ['minor', 'major']:
            raise StoredProcedureError(f"Invalid case type: {case_type}")
        
        # Create new case
        case = Case(
            person_id=person_id,
            case_type=case_type,
            description=description,
            date_reported=date_reported or date.today(),
            status=status,
            remarks=remarks
        )
        
        # Add attachment data if provided
        if attachment_data:
            case.attachment_filename = attachment_data.get('filename')
            case.attachment_path = attachment_data.get('path')
            case.attachment_size = attachment_data.get('size')
            case.attachment_type = attachment_data.get('type')
        
        db.session.add(case)
        db.session.commit()
        
        logger.info(f"Case created successfully: {case_type} case for {person.full_name} (ID: {case.id})")
        
        return {
            'success': True,
            'case_id': case.id,
            'person_name': person.full_name,
            'case_type': case_type,
            'message': 'Case created successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_add_case: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_add_case: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_update_case_status(case_id: int, status: str, remarks: Optional[str] = None) -> Dict[str, Any]:
    """
    Update the status of a case.
    
    Args:
        case_id: ID of the case to update
        status: New status value
        remarks: Optional updated remarks
        
    Returns:
        Dictionary with success status and message
    """
    try:
        case = Case.query.get(case_id)
        if not case:
            raise StoredProcedureError(f"Case with ID {case_id} not found")
        
        case.status = status
        if remarks is not None:
            case.remarks = remarks
        
        db.session.commit()
        
        logger.info(f"Case status updated successfully: ID {case_id} -> {status}")
        
        return {
            'success': True,
            'case_id': case.id,
            'status': status,
            'message': 'Case status updated successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_update_case_status: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_update_case_status: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_delete_case(case_id: int) -> Dict[str, Any]:
    """
    Delete a case from the system.
    
    Args:
        case_id: ID of the case to delete
        
    Returns:
        Dictionary with success status and message
    """
    try:
        case = Case.query.get(case_id)
        if not case:
            raise StoredProcedureError(f"Case with ID {case_id} not found")
        
        db.session.delete(case)
        db.session.commit()
        
        logger.info(f"Case deleted successfully: ID {case_id}")
        
        return {
            'success': True,
            'message': 'Case deleted successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_delete_case: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_delete_case: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


# ==================== APPOINTMENT MANAGEMENT ====================

def sp_add_appointment(full_name: str, email: str, appointment_date: datetime,
                      appointment_type: str, appointment_description: Optional[str] = None,
                      status: str = 'Pending') -> Dict[str, Any]:
    """
    Add a new appointment.
    
    Args:
        full_name: Full name of the person making appointment
        email: Email address
        appointment_date: Date and time of appointment
        appointment_type: Type ('Complaint', 'Admission', 'Meeting')
        appointment_description: Optional description
        status: Appointment status (defaults to 'Pending')
        
    Returns:
        Dictionary with success status and appointment data
    """
    try:
        # Validate appointment type
        if appointment_type not in ['Complaint', 'Admission', 'Meeting']:
            raise StoredProcedureError(f"Invalid appointment type: {appointment_type}")
        
        # Check spam protection
        is_spam, count = Appointment.check_spam_protection(email)
        if is_spam:
            raise StoredProcedureError(f"Daily appointment limit reached for {email}")
        
        # Create new appointment
        appointment = Appointment(
            full_name=full_name,
            email=email,
            appointment_date=appointment_date,
            appointment_type=appointment_type,
            appointment_description=appointment_description,
            status=status
        )
        
        db.session.add(appointment)
        db.session.commit()
        
        logger.info(f"Appointment created successfully: {full_name} (ID: {appointment.id})")
        
        return {
            'success': True,
            'appointment_id': appointment.id,
            'full_name': full_name,
            'message': 'Appointment created successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_add_appointment: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_add_appointment: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_update_appointment_status(appointment_id: int, status: str) -> Dict[str, Any]:
    """
    Update appointment status.
    
    Args:
        appointment_id: ID of the appointment to update
        status: New status ('Pending', 'Scheduled', 'Cancelled', 'Rescheduled')
        
    Returns:
        Dictionary with success status and message
    """
    try:
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            raise StoredProcedureError(f"Appointment with ID {appointment_id} not found")
        
        # Validate status
        valid_statuses = ['Pending', 'Scheduled', 'Cancelled', 'Rescheduled']
        if status not in valid_statuses:
            raise StoredProcedureError(f"Invalid status: {status}")
        
        appointment.status = status
        db.session.commit()
        
        logger.info(f"Appointment status updated: ID {appointment_id} -> {status}")
        
        return {
            'success': True,
            'appointment_id': appointment.id,
            'status': status,
            'message': 'Appointment status updated successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_update_appointment_status: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_update_appointment_status: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_delete_appointment(appointment_id: int) -> Dict[str, Any]:
    """
    Delete an appointment.
    
    Args:
        appointment_id: ID of the appointment to delete
        
    Returns:
        Dictionary with success status and message
    """
    try:
        appointment = Appointment.query.get(appointment_id)
        if not appointment:
            raise StoredProcedureError(f"Appointment with ID {appointment_id} not found")
        
        db.session.delete(appointment)
        db.session.commit()
        
        logger.info(f"Appointment deleted successfully: ID {appointment_id}")
        
        return {
            'success': True,
            'message': 'Appointment deleted successfully'
        }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_delete_appointment: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_delete_appointment: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


# ==================== ATTENDANCE MANAGEMENT ====================

def sp_add_attendance(professor_name: str, status: str, 
                     attendance_date: Optional[date] = None) -> Dict[str, Any]:
    """
    Add attendance record for a professor.
    
    Args:
        professor_name: Name of the professor
        status: Attendance status ('Present', 'Absent', 'Late')
        attendance_date: Date of attendance (defaults to today)
        
    Returns:
        Dictionary with success status and attendance data
    """
    try:
        # Validate status
        if status not in ['Present', 'Absent', 'Late']:
            raise StoredProcedureError(f"Invalid attendance status: {status}")
        
        attendance_date = attendance_date or date.today()
        
        # Check if attendance already exists for this professor on this date
        existing = AttendanceChecklist.query.filter_by(
            professor_name=professor_name,
            date=attendance_date
        ).first()
        
        if existing:
            # Update existing record
            existing.status = status
            db.session.commit()
            
            logger.info(f"Attendance updated: {professor_name} - {status}")
            
            return {
                'success': True,
                'attendance_id': existing.id,
                'professor_name': professor_name,
                'status': status,
                'message': 'Attendance updated successfully'
            }
        else:
            # Create new record
            attendance = AttendanceChecklist(
                professor_name=professor_name,
                status=status,
                date=attendance_date
            )
            
            db.session.add(attendance)
            db.session.commit()
            
            logger.info(f"Attendance created: {professor_name} - {status}")
            
            return {
                'success': True,
                'attendance_id': attendance.id,
                'professor_name': professor_name,
                'status': status,
                'message': 'Attendance created successfully'
            }
        
    except StoredProcedureError as e:
        db.session.rollback()
        logger.error(f"Validation error in sp_add_attendance: {str(e)}")
        return {'success': False, 'error': str(e)}
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_add_attendance: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


# ==================== LOGGING ====================

def sp_log_audit(action_type: str, description: str, user_id: Optional[int] = None,
                ip_address: Optional[str] = None, user_agent: Optional[str] = None) -> Dict[str, Any]:
    """
    Create an audit log entry.
    
    Args:
        action_type: Type of action
        description: Description of the action
        user_id: Optional user ID
        ip_address: Optional IP address
        user_agent: Optional user agent string
        
    Returns:
        Dictionary with success status and log ID
    """
    try:
        log_entry = AuditLog(
            action_type=action_type,
            description=description,
            user_id=user_id,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        db.session.add(log_entry)
        db.session.commit()
        
        return {
            'success': True,
            'log_id': log_entry.id,
            'message': 'Audit log created successfully'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_log_audit: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}


def sp_log_activity(user_id: int, action: str, description: str) -> Dict[str, Any]:
    """
    Create an activity log entry for a user.
    
    Args:
        user_id: ID of the user
        action: Action performed
        description: Description of the action
        
    Returns:
        Dictionary with success status and log ID
    """
    try:
        log_entry = ActivityLog(
            user_id=user_id,
            action=action,
            description=description
        )
        
        db.session.add(log_entry)
        
        # Keep only the latest 10 logs per user
        user_logs = ActivityLog.query.filter_by(user_id=user_id).order_by(
            ActivityLog.timestamp.desc()
        ).all()
        
        if len(user_logs) > 10:
            for old_log in user_logs[10:]:
                db.session.delete(old_log)
        
        db.session.commit()
        
        return {
            'success': True,
            'log_id': log_entry.id,
            'message': 'Activity log created successfully'
        }
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error in sp_log_activity: {str(e)}")
        return {'success': False, 'error': f'Database error: {str(e)}'}

