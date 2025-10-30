"""
Utility functions for safe string handling and error management
"""

import re
import unicodedata


def sanitize_string(text):
    """Sanitize string input to prevent encoding issues"""
    if not text:
        return ""
    
    # Convert to string if not already
    text = str(text)
    
    # Remove or replace problematic characters
    # Keep only printable ASCII characters and basic Unicode
    text = ''.join(char for char in text if unicodedata.category(char)[0] != 'C' or char in '\n\r\t')
    
    # Remove emojis and other non-ASCII characters that might cause issues
    text = re.sub(r'[^\x00-\x7F\u00A0-\uFFFF]', '', text)
    
    # Strip whitespace
    return text.strip()


def safe_print(message):
    """Safely print messages without encoding issues"""
    try:
        print(str(message).encode('ascii', 'ignore').decode('ascii'))
    except:
        print("Error printing message")


def sanitize_form_data(form_data):
    """Sanitize all form data to prevent encoding issues"""
    sanitized = {}
    for key, value in form_data.items():
        if isinstance(value, str):
            sanitized[key] = sanitize_string(value)
        else:
            sanitized[key] = value
    return sanitized


def validate_required_fields(form_data, required_fields):
    """Validate that all required fields are present and not empty"""
    missing_fields = []
    for field in required_fields:
        if not form_data.get(field, '').strip():
            missing_fields.append(field)
    return missing_fields


def escape_js_string(text):
    """
    Escape a string for safe use in JavaScript.
    Prevents XSS attacks when injecting user data into JavaScript code.
    
    Args:
        text: The string to escape
    
    Returns:
        str: Escaped string safe for JavaScript
    """
    if text is None:
        return ''
    
    text = str(text)
    # Escape special JavaScript characters
    text = text.replace('\\', '\\\\')  # Backslash
    text = text.replace("'", "\\'")    # Single quote
    text = text.replace('"', '\\"')    # Double quote
    text = text.replace('\n', '\\n')   # Newline
    text = text.replace('\r', '\\r')   # Carriage return
    text = text.replace('</', '<\\/')  # Prevent script tag closing
    return text


def sanitize_error_message(error_msg: str) -> str:
    """
    Sanitize error messages for production to prevent information disclosure.
    In production, only show generic messages.
    
    Args:
        error_msg: The error message to sanitize
    
    Returns:
        str: Sanitized error message
    """
    try:
        from flask import current_app
        # In production mode, show generic errors only
        if not current_app.debug and not current_app.config.get('DEBUG', False):
            # Check if it's a generic/user-friendly error already
            generic_errors = [
                'not found', 'required', 'invalid', 'unauthorized',
                'forbidden', 'bad request', 'validation'
            ]
            if any(keyword in error_msg.lower() for keyword in generic_errors):
                return error_msg  # Already user-friendly
            
            # For technical errors, return generic message
            if 'traceback' in error_msg.lower() or 'exception' in error_msg.lower():
                return "An error occurred. Please try again or contact support."
            
            # For database errors, hide details
            if 'database' in error_msg.lower() or 'sql' in error_msg.lower():
                return "A database error occurred. Please try again."
        
        return error_msg
    except RuntimeError:
        # Outside Flask context, return as-is
        return error_msg


def create_error_response(error_msg, redirect_url=None):
    """Create standardized error response"""
    try:
        # Sanitize error message for production
        safe_error_msg = sanitize_error_message(error_msg)
        safe_print(f"ERROR: {error_msg}")
        if redirect_url:
            from flask import flash, redirect
            flash(f'Error: {safe_error_msg}', 'error')
            return redirect(redirect_url)
        else:
            from flask import jsonify
            return jsonify({'success': False, 'error': safe_error_msg}), 500
    except Exception as e:
        safe_print(f"CRITICAL ERROR in error handling: {str(e)}")
        if redirect_url:
            from flask import redirect
            return redirect(redirect_url)
        else:
            from flask import jsonify
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
