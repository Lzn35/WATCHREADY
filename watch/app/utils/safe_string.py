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


def create_error_response(error_msg, redirect_url=None):
    """Create standardized error response"""
    try:
        safe_print(f"ERROR: {error_msg}")
        if redirect_url:
            from flask import flash, redirect
            flash(f'Error: {error_msg}', 'error')
            return redirect(redirect_url)
        else:
            from flask import jsonify
            return jsonify({'success': False, 'error': error_msg}), 500
    except Exception as e:
        safe_print(f"CRITICAL ERROR in error handling: {str(e)}")
        if redirect_url:
            from flask import redirect
            return redirect(redirect_url)
        else:
            from flask import jsonify
            return jsonify({'success': False, 'error': 'Internal server error'}), 500
