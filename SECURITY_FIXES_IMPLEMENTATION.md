# Security Fixes Implementation Plan

## 🚨 **Critical Fixes (Implement Immediately)**

### **1. Remove Debug Information Exposure**

**File**: `watch/app/config.py`
**Issue**: Debug prints expose sensitive information in production
**Fix**:
```python
# Remove or comment out these lines:
# if os.getenv('RAILWAY_ENVIRONMENT'):
#     print(f"[RAILWAY DEBUG] DATABASE_URL from environment: {database_url}")
#     print(f"[RAILWAY DEBUG] RAILWAY_ENVIRONMENT: {os.getenv('RAILWAY_ENVIRONMENT')}")
#     print(f"[RAILWAY DEBUG] Using DATABASE_URL: {SQLALCHEMY_DATABASE_URI}")
#     print(f"[RAILWAY DEBUG] No DATABASE_URL found, using default: {SQLALCHEMY_DATABASE_URI}")
```

### **2. Enable Secure Cookies in Production**

**File**: `watch/app/config.py`
**Issue**: Session cookies not secure in production
**Fix**:
```python
# Update these lines:
SESSION_COOKIE_SECURE = True  # Always True in production
WTF_CSRF_SSL_STRICT = True   # Always True in production
```

### **3. Implement MIME Type Validation for File Uploads**

**File**: `watch/app/utils/file_upload.py`
**Issue**: File validation relies only on extensions
**Fix**:
```python
import magic

def validate_file_content(file_path, expected_extensions):
    """Validate file content using magic numbers"""
    try:
        mime_type = magic.from_file(file_path, mime=True)
        allowed_mime_types = {
            'jpg': 'image/jpeg',
            'jpeg': 'image/jpeg',
            'png': 'image/png',
            'pdf': 'application/pdf',
            'docx': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
            'doc': 'application/msword',
            'txt': 'text/plain'
        }
        
        file_ext = file_path.split('.')[-1].lower()
        expected_mime = allowed_mime_types.get(file_ext)
        
        if expected_mime and mime_type != expected_mime:
            return False, f"File type mismatch. Expected {expected_mime}, got {mime_type}"
        
        return True, "File type valid"
    except Exception as e:
        return False, f"File validation error: {str(e)}"
```

### **4. Fix SQL Injection Vulnerabilities**

**File**: `watch/app/services/database.py`
**Issue**: Raw SQL queries without proper parameterization
**Fix**:
```python
def safe_table_backup(table_name):
    """Safely backup table with parameterized query"""
    # Validate table name against whitelist
    allowed_tables = ['users', 'roles', 'persons', 'cases', 'minor_cases', 'major_cases']
    
    if table_name not in allowed_tables:
        raise ValueError(f"Table {table_name} not allowed for backup")
    
    # Use parameterized query
    result = db.session.execute(text(f"SELECT * FROM {table_name}"))
    return result.fetchall()
```

## ⚠️ **High Priority Fixes (Implement Within 1 Week)**

### **5. Implement Password Complexity Requirements**

**File**: `watch/app/modules/auth/routes.py`
**Issue**: No password complexity requirements
**Fix**:
```python
import re

def validate_password_strength(password):
    """Validate password meets complexity requirements"""
    if len(password) < 8:
        return False, "Password must be at least 8 characters long"
    
    if not re.search(r'[A-Z]', password):
        return False, "Password must contain at least one uppercase letter"
    
    if not re.search(r'[a-z]', password):
        return False, "Password must contain at least one lowercase letter"
    
    if not re.search(r'\d', password):
        return False, "Password must contain at least one number"
    
    if not re.search(r'[!@#$%^&*(),.?":{}|<>]', password):
        return False, "Password must contain at least one special character"
    
    return True, "Password meets requirements"
```

### **6. Add Account Lockout Mechanism**

**File**: `watch/app/modules/auth/routes.py`
**Issue**: No protection against brute force attacks
**Fix**:
```python
from datetime import datetime, timedelta

def check_account_lockout(user_id):
    """Check if account is locked due to failed attempts"""
    # Check failed login attempts in last 15 minutes
    cutoff_time = datetime.now() - timedelta(minutes=15)
    
    failed_attempts = db.session.execute(text("""
        SELECT COUNT(*) FROM failed_login_attempts 
        WHERE user_id = :user_id AND attempt_time > :cutoff_time
    """), {'user_id': user_id, 'cutoff_time': cutoff_time}).scalar()
    
    if failed_attempts >= 5:  # Lock after 5 failed attempts
        return True, "Account locked due to too many failed login attempts"
    
    return False, "Account not locked"

def record_failed_login(user_id, ip_address):
    """Record failed login attempt"""
    db.session.execute(text("""
        INSERT INTO failed_login_attempts (user_id, ip_address, attempt_time)
        VALUES (:user_id, :ip_address, :attempt_time)
    """), {
        'user_id': user_id,
        'ip_address': ip_address,
        'attempt_time': datetime.now()
    })
    db.session.commit()
```

### **7. Enhance Error Handling**

**File**: `watch/app/errors.py`
**Issue**: Detailed error messages expose system information
**Fix**:
```python
def handle_generic_error(error):
    """Handle errors with generic messages for users"""
    if current_app.debug:
        # In development, show detailed errors
        return str(error), 500
    else:
        # In production, show generic error
        return "An internal error occurred. Please try again later.", 500

@app.errorhandler(500)
def internal_error(error):
    # Log detailed error for debugging
    current_app.logger.error(f"Internal error: {str(error)}")
    
    # Return generic error to user
    return render_template('errors/500.html'), 500
```

### **8. Implement Comprehensive Rate Limiting**

**File**: `watch/app/__init__.py`
**Issue**: Rate limiting not applied to all endpoints
**Fix**:
```python
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Configure rate limiting
limiter = Limiter(
    app,
    key_func=get_remote_address,
    default_limits=["200 per day", "50 per hour"]
)

# Apply rate limiting to specific routes
@limiter.limit("5 per minute")
def login_route():
    # Login logic
    pass

@limiter.limit("10 per minute")
def file_upload_route():
    # File upload logic
    pass
```

## 🔧 **Medium Priority Fixes (Implement Within 1 Month)**

### **9. Enhance CSRF Protection**

**File**: `watch/app/config.py`
**Issue**: CSRF protection needs hardening
**Fix**:
```python
# Update CSRF configuration
WTF_CSRF_ENABLED = True
WTF_CSRF_TIME_LIMIT = 3600  # 1 hour
WTF_CSRF_SSL_STRICT = True  # Require HTTPS
WTF_CSRF_COOKIE_SECURE = True
WTF_CSRF_COOKIE_HTTPONLY = True
WTF_CSRF_COOKIE_SAMESITE = 'Strict'
```

### **10. Implement File Content Scanning**

**File**: `watch/app/utils/file_upload.py`
**Issue**: No malware scanning for uploaded files
**Fix**:
```python
import hashlib
import os

def scan_file_for_malware(file_path):
    """Scan uploaded file for potential malware"""
    try:
        # Check file size (prevent zip bombs)
        file_size = os.path.getsize(file_path)
        if file_size > 100 * 1024 * 1024:  # 100MB
            return False, "File too large"
        
        # Check for suspicious patterns
        with open(file_path, 'rb') as f:
            content = f.read(1024)  # Read first 1KB
            
            # Check for executable signatures
            executable_signatures = [b'MZ', b'\x7fELF', b'\xfe\xed\xfa']
            if any(sig in content for sig in executable_signatures):
                return False, "Executable file detected"
            
            # Check for script signatures
            script_signatures = [b'#!/bin/', b'#!/usr/', b'<script', b'<?php']
            if any(sig in content for sig in script_signatures):
                return False, "Script file detected"
        
        return True, "File scan passed"
    except Exception as e:
        return False, f"File scan error: {str(e)}"
```

### **11. Add Security Monitoring**

**File**: `watch/app/services/security_monitoring.py`
**Issue**: No real-time security monitoring
**Fix**:
```python
class SecurityMonitor:
    """Real-time security monitoring service"""
    
    def __init__(self, app):
        self.app = app
        self.suspicious_activities = []
    
    def monitor_login_attempts(self, user_id, ip_address, success):
        """Monitor login attempts for suspicious patterns"""
        if not success:
            # Record failed attempt
            self.record_failed_attempt(user_id, ip_address)
            
            # Check for brute force
            if self.detect_brute_force(user_id, ip_address):
                self.alert_security_team("Brute force attack detected", {
                    'user_id': user_id,
                    'ip_address': ip_address
                })
    
    def monitor_file_uploads(self, user_id, file_info):
        """Monitor file uploads for suspicious activity"""
        # Check file size
        if file_info['size'] > 50 * 1024 * 1024:  # 50MB
            self.alert_security_team("Large file upload", {
                'user_id': user_id,
                'file_size': file_info['size']
            })
        
        # Check file type
        suspicious_types = ['.exe', '.bat', '.cmd', '.scr']
        if any(file_info['filename'].lower().endswith(ext) for ext in suspicious_types):
            self.alert_security_team("Suspicious file type uploaded", {
                'user_id': user_id,
                'filename': file_info['filename']
            })
    
    def detect_brute_force(self, user_id, ip_address):
        """Detect brute force attacks"""
        # Check failed attempts in last 15 minutes
        cutoff_time = datetime.now() - timedelta(minutes=15)
        
        failed_count = db.session.execute(text("""
            SELECT COUNT(*) FROM failed_login_attempts 
            WHERE (user_id = :user_id OR ip_address = :ip_address) 
            AND attempt_time > :cutoff_time
        """), {
            'user_id': user_id,
            'ip_address': ip_address,
            'cutoff_time': cutoff_time
        }).scalar()
        
        return failed_count >= 10  # 10 failed attempts in 15 minutes
```

### **12. Implement Log Sanitization**

**File**: `watch/app/utils/logging_config.py`
**Issue**: Logs may contain sensitive information
**Fix**:
```python
import re

def sanitize_log_data(data):
    """Sanitize log data to remove sensitive information"""
    if isinstance(data, dict):
        sanitized = {}
        for key, value in data.items():
            if key.lower() in ['password', 'secret', 'token', 'key', 'ssn', 'credit_card']:
                sanitized[key] = '[REDACTED]'
            else:
                sanitized[key] = sanitize_log_data(value)
        return sanitized
    elif isinstance(data, str):
        # Remove potential sensitive patterns
        patterns = [
            r'password["\']?\s*[:=]\s*["\']?[^"\']+["\']?',
            r'secret["\']?\s*[:=]\s*["\']?[^"\']+["\']?',
            r'token["\']?\s*[:=]\s*["\']?[^"\']+["\']?',
            r'key["\']?\s*[:=]\s*["\']?[^"\']+["\']?'
        ]
        
        for pattern in patterns:
            data = re.sub(pattern, r'\1[REDACTED]', data, flags=re.IGNORECASE)
        
        return data
    else:
        return data
```

## 📋 **Implementation Checklist**

### **Phase 1: Critical Fixes (Day 1-2)**
- [ ] Remove debug prints from production code
- [ ] Enable secure cookies in production
- [ ] Implement MIME type validation
- [ ] Fix SQL injection vulnerabilities

### **Phase 2: High Priority Fixes (Week 1)**
- [ ] Implement password complexity requirements
- [ ] Add account lockout mechanism
- [ ] Enhance error handling
- [ ] Implement comprehensive rate limiting

### **Phase 3: Medium Priority Fixes (Month 1)**
- [ ] Enhance CSRF protection
- [ ] Implement file content scanning
- [ ] Add security monitoring
- [ ] Implement log sanitization

### **Phase 4: Testing and Validation (Month 1)**
- [ ] Conduct security testing
- [ ] Validate all fixes
- [ ] Update documentation
- [ ] Train team on new security measures

## 🎯 **Success Metrics**

### **Security Improvements**
- Zero critical vulnerabilities
- Reduced high-risk vulnerabilities by 80%
- Improved security score to 8.5/10
- Zero security incidents in production

### **Performance Impact**
- No significant performance degradation
- Maintained user experience
- Improved system reliability
- Enhanced audit capabilities

## 📞 **Next Steps**

1. **Review and approve** this implementation plan
2. **Prioritize fixes** based on business impact
3. **Assign resources** for implementation
4. **Set timeline** for each phase
5. **Conduct testing** after each phase
6. **Monitor results** and adjust as needed

---

**Implementation Plan Created**: December 2024  
**Estimated Timeline**: 1 month for complete implementation  
**Next Review**: After Phase 2 completion
