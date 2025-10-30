"""
Validation utilities for WATCH system
"""
import re
from typing import Any, Optional
from datetime import datetime, date


def is_valid_text_input(value: Any, field_name: str = "Field", min_length: int = 1, max_length: Optional[int] = None) -> tuple[bool, str]:
    """
    Validate text input to prevent whitespace-only entries
    
    Args:
        value: The input value to validate
        field_name: Name of the field for error messages
        min_length: Minimum required length after trimming
        max_length: Maximum allowed length after trimming
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Convert to string and handle None
    if value is None:
        return False, f"{field_name} is required."
    
    text_value = str(value).strip()
    
    # Check if empty after trimming (this catches whitespace-only input)
    if not text_value:
        # Check if original value had content (meaning it was whitespace-only)
        if str(value).strip() == '' and str(value):
            return False, f"{field_name} cannot contain only whitespace characters."
        else:
            return False, f"{field_name} cannot be empty."
    
    # Check minimum length
    if len(text_value) < min_length:
        return False, f"{field_name} must be at least {min_length} character(s) long."
    
    # Check maximum length
    if max_length and len(text_value) > max_length:
        return False, f"{field_name} must not exceed {max_length} characters."
    
    return True, ""


def validate_name(name: str, field_name: str = "Name") -> tuple[bool, str]:
    """
    Validate names (first name, last name, full name, professor name, etc.)
    
    Args:
        name: The name to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    is_valid, error = is_valid_text_input(name, field_name, min_length=1, max_length=100)
    
    if not is_valid:
        return False, error
    
    # Check for valid name characters (letters, spaces, hyphens, apostrophes)
    name_pattern = r"^[a-zA-Z\s\-'\.]+$"
    if not re.match(name_pattern, name):
        return False, f"{field_name} can only contain letters, spaces, hyphens, apostrophes, and periods."
    
    # Check that name doesn't start or end with special characters
    if name.startswith((' ', '-', "'", '.')) or name.endswith((' ', '-', "'", '.')):
        return False, f"{field_name} cannot start or end with spaces or special characters."
    
    # Check for multiple consecutive spaces
    if '  ' in name:
        return False, f"{field_name} cannot contain multiple consecutive spaces."
    
    return True, ""


def validate_subject_course(subject: str, field_name: str = "Subject") -> tuple[bool, str]:
    """
    Validate subject/course names
    
    Args:
        subject: The subject/course to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    is_valid, error = is_valid_text_input(subject, field_name, min_length=1, max_length=150)
    
    if not is_valid:
        return False, error
    
    # Check for valid subject/course characters (letters, numbers, spaces, common punctuation)
    subject_pattern = r"^[a-zA-Z0-9\s\-'\.\(\)&]+$"
    if not re.match(subject_pattern, subject):
        return False, f"{field_name} can only contain letters, numbers, spaces, and common punctuation."
    
    return True, ""


def validate_section(section: str, field_name: str = "Section") -> tuple[bool, str]:
    """
    Validate section names
    
    Args:
        section: The section to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    is_valid, error = is_valid_text_input(section, field_name, min_length=1, max_length=50)
    
    if not is_valid:
        return False, error
    
    # Check for valid section characters (letters, numbers, spaces, hyphens)
    section_pattern = r"^[a-zA-Z0-9\s\-]+$"
    if not re.match(section_pattern, section):
        return False, f"{field_name} can only contain letters, numbers, spaces, and hyphens."
    
    return True, ""


def validate_department(department: str, field_name: str = "Department") -> tuple[bool, str]:
    """
    Validate department names
    
    Args:
        department: The department to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    is_valid, error = is_valid_text_input(department, field_name, min_length=1, max_length=100)
    
    if not is_valid:
        return False, error
    
    # Check for valid department characters (letters, spaces, common punctuation, parentheses)
    dept_pattern = r"^[a-zA-Z\s\-'\.&()]+$"
    if not re.match(dept_pattern, department):
        return False, f"{field_name} can only contain letters, spaces, and common punctuation."
    
    return True, ""


def validate_faculty_department(department: str, field_name: str = "Department") -> tuple[bool, str]:
    """
    Validate faculty department dropdown values
    
    Args:
        department: The department to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    is_valid, error = is_valid_text_input(department, field_name, min_length=1, max_length=100)
    
    if not is_valid:
        return False, error
    
    # Valid faculty departments
    valid_departments = [
        "Information Communications Technology (ICT)",
        "General Education (GE)", 
        "Business Management (BM)"
    ]
    
    if department not in valid_departments:
        return False, f"{field_name} must be one of: ICT, GE, or BM."
    
    return True, ""


def validate_room(room: str, field_name: str = "Room") -> tuple[bool, str]:
    """
    Validate room names/numbers
    
    Args:
        room: The room to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Room is optional, so empty is OK
    if not room or not str(room).strip():
        return True, ""
    
    room_value = str(room).strip()
    
    # Check for valid room characters (letters, numbers, spaces, hyphens, common punctuation)
    room_pattern = r"^[a-zA-Z0-9\s\-\.]+$"
    if not re.match(room_pattern, room_value):
        return False, f"{field_name} can only contain letters, numbers, spaces, hyphens, and periods."
    
    return True, ""


def validate_email(email: str, field_name: str = "Email") -> tuple[bool, str]:
    """
    Validate email addresses
    
    Args:
        email: The email to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Email is optional, so empty is OK
    if not email or not str(email).strip():
        return True, ""
    
    email_value = str(email).strip()
    
    # Basic email validation
    email_pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
    if not re.match(email_pattern, email_value):
        return False, f"{field_name} must be a valid email address."
    
    return True, ""


def validate_phone(phone: str, field_name: str = "Phone") -> tuple[bool, str]:
    """
    Validate phone numbers (Philippines format - maximum 12 digits)
    
    Args:
        phone: The phone number to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Phone is optional, so empty is OK
    if not phone or not str(phone).strip():
        return True, ""
    
    phone_value = str(phone).strip()
    
    # Check for valid phone characters (numbers, spaces, hyphens, parentheses, plus)
    phone_pattern = r"^[\d\s\-\(\)\+]+$"
    if not re.match(phone_pattern, phone_value):
        return False, f"{field_name} can only contain numbers, spaces, hyphens, parentheses, and plus signs."
    
    # Must contain at least some digits
    if not re.search(r'\d', phone_value):
        return False, f"{field_name} must contain at least one digit."
    
    # Extract only digits for length validation
    digits_only = re.sub(r'[^\d]', '', phone_value)
    
    # Check maximum length (12 digits for Philippines phone numbers)
    if len(digits_only) > 12:
        return False, f"{field_name} cannot exceed 12 digits (Philippines format)."
    
    # Check minimum length (at least 7 digits for valid phone numbers)
    if len(digits_only) < 7:
        return False, f"{field_name} must be at least 7 digits long."
    
    return True, ""


def validate_description(description: str, field_name: str = "Description") -> tuple[bool, str]:
    """
    Validate descriptions/remarks
    
    Args:
        description: The description to validate
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    # Description is optional, so empty is OK
    if not description or not str(description).strip():
        return True, ""
    
    description_value = str(description).strip()
    
    # Check minimum length for descriptions
    if len(description_value) < 3:
        return False, f"{field_name} must be at least 3 characters long if provided."
    
    # Check maximum length
    if len(description_value) > 500:
        return False, f"{field_name} must not exceed 500 characters."
    
    return True, ""


def sanitize_and_validate_text(value: Any, validation_func, field_name: str = "Field") -> tuple[bool, str, str]:
    """
    Sanitize text input and validate it
    
    Args:
        value: The input value
        validation_func: The validation function to use
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message, sanitized_value)
    """
    if value is None:
        return False, f"{field_name} is required.", ""
    
    # Sanitize: strip whitespace and normalize
    sanitized_value = str(value).strip()
    
    # Validate using provided function
    is_valid, error = validation_func(sanitized_value, field_name)
    
    return is_valid, error, sanitized_value


# Common validation patterns
VALIDATION_PATTERNS = {
    'name': r"^[a-zA-Z\s\-'\.]+$",
    'subject': r"^[a-zA-Z0-9\s\-'\.\(\)&]+$",
    'section': r"^[a-zA-Z0-9\s\-]+$",
    'department': r"^[a-zA-Z\s\-'\.&]+$",
    'room': r"^[a-zA-Z0-9\s\-\.]+$",
    'email': r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
    'phone': r"^[\d\s\-\(\)\+]+$",
}


def validate_case_date(date_str: str, field_name: str = "Date") -> tuple[bool, str]:
    """
    Validate case date to prevent future dates
    
    Args:
        date_str: The date string to validate (YYYY-MM-DD format)
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not date_str or not date_str.strip():
        return False, f"{field_name} is required."
    
    try:
        # Parse the date
        case_date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        today = date.today()
        
        # Check if date is in the future
        if case_date > today:
            return False, f"{field_name} cannot be set for a future date. Maximum allowed date is today ({today.strftime('%Y-%m-%d')})."
        
        # Check if date is too far in the past (optional - can be removed if not needed)
        # For example, don't allow dates more than 1 year in the past
        one_year_ago = date.today().replace(year=date.today().year - 1)
        if case_date < one_year_ago:
            return False, f"{field_name} cannot be set for more than one year ago. Minimum allowed date is {one_year_ago.strftime('%Y-%m-%d')}."
        
        return True, ""
        
    except ValueError:
        return False, f"{field_name} must be in YYYY-MM-DD format."


def validate_schedule_date(date_str: str, field_name: str = "Date") -> tuple[bool, str]:
    """
    Validate schedule date (can be future date for scheduling)
    
    Args:
        date_str: The date string to validate (YYYY-MM-DD format)
        field_name: Name of the field for error messages
    
    Returns:
        tuple: (is_valid, error_message)
    """
    if not date_str or not date_str.strip():
        return False, f"{field_name} is required."
    
    try:
        # Parse the date
        schedule_date = datetime.strptime(date_str.strip(), '%Y-%m-%d').date()
        
        # For schedules, we can allow future dates but not too far in the past
        # Don't allow schedules for more than 1 year in the past
        one_year_ago = date.today().replace(year=date.today().year - 1)
        if schedule_date < one_year_ago:
            return False, f"{field_name} cannot be set for more than one year ago. Minimum allowed date is {one_year_ago.strftime('%Y-%m-%d')}."
        
        return True, ""
        
    except ValueError:
        return False, f"{field_name} must be in YYYY-MM-DD format."


def get_validation_pattern(field_type: str) -> str:
    """
    Get validation pattern for a field type
    
    Args:
        field_type: Type of field (name, subject, section, etc.)
    
    Returns:
        str: Regular expression pattern
    """
    return VALIDATION_PATTERNS.get(field_type, r"^[a-zA-Z0-9\s\-'\.\(\)&]+$")
