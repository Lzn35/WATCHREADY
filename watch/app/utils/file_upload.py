"""
File upload utilities for WATCH system.
Handles secure file uploads with proper validation and sanitization.
"""

import os
import uuid
import hashlib
from datetime import datetime

# Conditional import for magic (MIME type detection)
try:
    import magic
    MAGIC_AVAILABLE = True
except ImportError:
    MAGIC_AVAILABLE = False
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


def validate_file_content(file_path, expected_extensions):
    """
    Validate file content using magic numbers for enhanced security.
    
    Args:
        file_path: Path to the file to validate
        expected_extensions: List of expected file extensions
        
    Returns:
        tuple: (is_valid, error_message)
    """
    try:
        # Check if magic is available
        if not MAGIC_AVAILABLE:
            return True, "MIME validation skipped (magic not available)"
        
        # Get MIME type using python-magic
        mime_type = magic.from_file(file_path, mime=True)
        
        # Define allowed MIME types for each extension
        allowed_mime_types = {
            'jpg': ['image/jpeg'],
            'jpeg': ['image/jpeg'],
            'png': ['image/png'],
            'gif': ['image/gif'],
            'bmp': ['image/bmp'],
            'webp': ['image/webp'],
            'pdf': ['application/pdf'],
            'docx': ['application/vnd.openxmlformats-officedocument.wordprocessingml.document'],
            'doc': ['application/msword'],
            'txt': ['text/plain'],
            'rtf': ['application/rtf', 'text/rtf'],
            'mp4': ['video/mp4'],
            'avi': ['video/x-msvideo'],
            'mov': ['video/quicktime'],
            'wmv': ['video/x-ms-wmv'],
            'flv': ['video/x-flv'],
            'webm': ['video/webm'],
            'mp3': ['audio/mpeg'],
            'wav': ['audio/wav'],
            'zip': ['application/zip'],
            'rar': ['application/x-rar-compressed'],
            '7z': ['application/x-7z-compressed']
        }
        
        # Check if any expected extension matches the MIME type
        for ext in expected_extensions:
            if ext.lower() in allowed_mime_types:
                if mime_type in allowed_mime_types[ext.lower()]:
                    return True, "File type valid"
        
        return False, f"File type mismatch. Expected one of {expected_extensions}, got {mime_type}"
        
    except Exception as e:
        return False, f"File validation error: {str(e)}"


def scan_file_for_malware(file_path):
    """
    Scan uploaded file for potential malware and suspicious content.
    
    Args:
        file_path: Path to the file to scan
        
    Returns:
        tuple: (is_safe, error_message)
    """
    try:
        # Check file size (prevent zip bombs)
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:  # 100MB limit
            return False, "File too large (maximum 100MB)"
        
        # Check for suspicious patterns in file content
        with open(file_path, 'rb') as f:
            content = f.read(1024)  # Read first 1KB
            
            # Check for executable signatures
            executable_signatures = [b'MZ', b'\x7fELF', b'\xfe\xed\xfa', b'\xca\xfe\xba\xbe']
            if any(sig in content for sig in executable_signatures):
                return False, "Executable file detected - not allowed"
            
            # Check for script signatures
            script_signatures = [b'#!/bin/', b'#!/usr/', b'<script', b'<?php', b'<%', b'<%=']
            if any(sig in content for sig in script_signatures):
                return False, "Script file detected - not allowed"
            
            # Check for suspicious patterns
            suspicious_patterns = [b'eval(', b'exec(', b'system(', b'shell_exec(']
            if any(pattern in content for pattern in suspicious_patterns):
                return False, "Suspicious code patterns detected"
        
        return True, "File scan passed"
        
    except Exception as e:
        return False, f"File scan error: {str(e)}"

def get_file_size(file):
    """
    Get file size in bytes.
    
    Args:
        file: File object with seek/tell methods
        
    Returns:
        int: File size in bytes
    """
    file.seek(0, 2)  # Seek to end
    size = file.tell()
    file.seek(0)  # Reset to beginning
    return size

def generate_unique_filename(original_filename):
    """
    Generate a unique filename to prevent conflicts and maintain security.
    
    Args:
        original_filename: Original filename from upload
        
    Returns:
        str: Unique filename with timestamp and UUID
    """
    # Get file extension
    if '.' in original_filename:
        extension = original_filename.rsplit('.', 1)[1].lower()
    else:
        extension = ''
    
    # Generate unique filename with timestamp and UUID
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    unique_id = str(uuid.uuid4())[:8]
    
    if extension:
        return f"{timestamp}_{unique_id}.{extension}"
    else:
        return f"{timestamp}_{unique_id}"

def save_upload(file_storage, subdir=""):
    """
    Save uploaded file with enhanced security validation.
    
    Args:
        file_storage: FileStorage object from Flask request.files
        subdir: Optional subdirectory within UPLOAD_FOLDER
        
    Returns:
        str: Absolute path to saved file
        
    Raises:
        ValueError: If file is invalid or missing
        werkzeug.exceptions.BadRequest: If file type is not allowed
    """
    if not file_storage or file_storage.filename == "":
        raise ValueError("No file provided")
    
    # Validate file extension
    if not allowed_file(file_storage.filename):
        allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', set())
        abort(400, f"Invalid file type. Allowed types: {', '.join(sorted(allowed_exts))}")
    
    # Sanitize filename
    filename = secure_filename(file_storage.filename)
    
    # Create upload directory
    upload_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], subdir)
    os.makedirs(upload_dir, exist_ok=True)
    
    # Save file temporarily for validation
    file_path = os.path.join(upload_dir, filename)
    file_storage.save(file_path)
    
    # Enhanced security validation
    try:
        # Get file extension for MIME validation
        file_ext = filename.rsplit('.', 1)[1].lower() if '.' in filename else ''
        
        # Validate MIME type
        is_valid, error_msg = validate_file_content(file_path, [file_ext])
        if not is_valid:
            os.remove(file_path)  # Remove invalid file
            abort(400, f"File validation failed: {error_msg}")
        
        # Scan for malware
        is_safe, scan_error = scan_file_for_malware(file_path)
        if not is_safe:
            os.remove(file_path)  # Remove unsafe file
            abort(400, f"File security scan failed: {scan_error}")
            
    except Exception as e:
        # Clean up file if validation fails
        if os.path.exists(file_path):
            os.remove(file_path)
        abort(400, f"File validation error: {str(e)}")
    
    return file_path

def save_attachment(file, case_id, case_type='major'):
    """
    Save uploaded file for a case attachment to database as BLOB with enhanced security and logging.
    
    Args:
        file: The uploaded file object (FileStorage)
        case_id: ID of the case
        case_type: Type of case ('major' or 'minor')
    
    Returns:
        dict: File information including filename, size, type, hash
        None: If upload failed
        
    Raises:
        ValueError: If file validation fails
        werkzeug.exceptions.BadRequest: If file type is not allowed
    """
    if not file or file.filename == '':
        return None
    
    # Check if file is allowed
    if not allowed_file(file.filename):
        allowed_exts = current_app.config.get('ALLOWED_EXTENSIONS', set())
        raise ValueError(f"File type not allowed. Allowed types: {', '.join(sorted(allowed_exts))}")
    
    # Check file size (Flask will handle MAX_CONTENT_LENGTH automatically with 413 error)
    # But we can also check manually for better error messages
    file_size = get_file_size(file)
    max_size = current_app.config.get('MAX_CONTENT_LENGTH', 10 * 1024 * 1024)
    if file_size > max_size:
        raise ValueError(f"File too large. Maximum size: {max_size // (1024*1024)}MB")
    
    # Read file content
    file.seek(0)  # Reset to beginning
    file_data = file.read()
    
    # Generate file hash for integrity
    file_hash = hashlib.sha256(file_data).hexdigest()
    
    # Generate secure filename
    original_filename = secure_filename(file.filename)
    
    # Get MIME type
    mime_type = file.content_type or 'application/octet-stream'
    
    # Security logging - log file upload
    try:
        from flask import session
        from .security_logger import log_file_upload
        log_file_upload(
            filename=original_filename,
            file_size=file_size,
            file_type=mime_type,
            case_id=case_id,
            uploader_id=session.get('user_id'),
            uploader_name=session.get('username')
        )
    except Exception as log_error:
        # Don't fail upload if logging fails
        current_app.logger.error(f"Security logging failed: {str(log_error)}")
    
    return {
        'filename': original_filename,
        'data': file_data,
        'size': file_size,
        'type': mime_type,
        'hash': file_hash
    }

def delete_attachment(file_path):
    """
    Delete an attachment file securely with logging.
    NOTE: This function is now deprecated for database storage.
    Files are automatically deleted when database records are deleted.
    
    Args:
        file_path: Path to the file to delete (legacy support)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        if os.path.exists(file_path):
            # Verify file is within allowed upload directory
            upload_folder = current_app.config.get('UPLOAD_FOLDER', '')
            instance_path = current_app.instance_path
            
            real_path = os.path.realpath(file_path)
            real_upload = os.path.realpath(os.path.join(instance_path, 'uploads'))
            
            # Prevent path traversal attacks
            if not real_path.startswith(real_upload):
                current_app.logger.error(f"Attempted to delete file outside upload directory: {file_path}")
                # Log suspicious activity
                try:
                    from .security_logger import log_suspicious_activity
                    log_suspicious_activity('PATH_TRAVERSAL_ATTEMPT', f"Attempted to delete: {file_path}")
                except:
                    pass
                return False
            
            # Get filename for logging
            filename = os.path.basename(file_path)
            
            # Delete file
            os.remove(file_path)
            
            # Security logging
            try:
                from flask import session
                from .security_logger import log_file_deletion
                log_file_deletion(
                    filename=filename,
                    deleter_id=session.get('user_id'),
                    deleter_name=session.get('username')
                )
            except Exception as log_error:
                # Don't fail deletion if logging fails
                current_app.logger.error(f"Security logging failed: {str(log_error)}")
            
            return True
    except Exception as e:
        current_app.logger.error(f"Error deleting file {file_path}: {str(e)}")
    return False

def clear_case_attachment(case):
    """
    Clear attachment data from a case (for database storage).
    
    Args:
        case: Case object (MajorCase or Case model)
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Clear attachment fields
        case.attachment_filename = None
        case.attachment_data = None
        case.attachment_size = None
        case.attachment_type = None
        case.attachment_hash = None
        
        # Security logging
        try:
            from flask import session
            from .security_logger import log_file_deletion
            log_file_deletion(
                filename=case.attachment_filename or 'unknown',
                deleter_id=session.get('user_id'),
                deleter_name=session.get('username')
            )
        except Exception as log_error:
            # Don't fail deletion if logging fails
            current_app.logger.error(f"Security logging failed: {str(log_error)}")
        
        return True
    except Exception as e:
        current_app.logger.error(f"Error clearing attachment from case: {str(e)}")
    return False

def get_attachment_url(file_path, case_id, case_type='major'):
    """
    Generate URL for accessing attachment.
    
    Args:
        file_path: Absolute path to the file
        case_id: ID of the case
        case_type: Type of case ('major' or 'minor')
        
    Returns:
        str: URL path to access the file, or None if invalid
    """
    if not file_path:
        return None
    
    # Convert absolute path to relative path for URL
    instance_path = current_app.instance_path
    if file_path.startswith(instance_path):
        relative_path = os.path.relpath(file_path, instance_path)
        return f"/uploads/{case_type}/{case_id}/{os.path.basename(relative_path)}"
    
    return None

def format_file_size(size_bytes):
    """
    Format file size in human readable format.
    
    Args:
        size_bytes: File size in bytes
        
    Returns:
        str: Formatted file size (e.g., "1.5 MB")
    """
    if size_bytes == 0:
        return "0 B"
    
    size_names = ["B", "KB", "MB", "GB"]
    i = 0
    while size_bytes >= 1024 and i < len(size_names) - 1:
        size_bytes /= 1024.0
        i += 1
    
    return f"{size_bytes:.1f} {size_names[i]}"
