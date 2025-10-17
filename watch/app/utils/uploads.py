"""
Secure upload utilities for WATCH system.
Provides simplified upload interface with configuration-based validation.
"""

import os
from werkzeug.utils import secure_filename
from flask import current_app, abort

def allowed_file(filename):
    """
    Check if file extension is allowed based on application configuration.
    
    Args:
        filename: Name of the file to check
        
    Returns:
        bool: True if file extension is allowed, False otherwise
    """
    if not filename or '.' not in filename:
        return False
    
    extension = filename.rsplit('.', 1)[1].lower()
    allowed_extensions = current_app.config.get('ALLOWED_EXTENSIONS', set())
    
    return extension in allowed_extensions

def save_upload(fileobj, subdir=''):
    """
    Save uploaded file securely with validation.
    
    Args:
        fileobj: FileStorage object from Flask request.files
        subdir: Optional subdirectory within UPLOAD_FOLDER
        
    Returns:
        str: Absolute path to saved file
        
    Raises:
        ValueError: If file is invalid or missing
        werkzeug.exceptions.BadRequest: If file type is not allowed
    """
    if not fileobj or not fileobj.filename:
        raise ValueError('No file provided')
    
    # Validate file type
    if not allowed_file(fileobj.filename):
        allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', set())
        abort(400, f"Invalid file type. Allowed types: {', '.join(sorted(allowed_exts))}")
    
    # Get upload folder from config
    upload_folder = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    
    # Add subdirectory if specified
    if subdir:
        upload_folder = os.path.join(upload_folder, subdir)
    
    # Create directory if it doesn't exist
    os.makedirs(upload_folder, exist_ok=True)
    
    # Sanitize filename
    filename = secure_filename(fileobj.filename)
    
    # Build full path and save
    path = os.path.join(upload_folder, filename)
    fileobj.save(path)
    
    return path
