"""
Email Configuration for SMTP
Supports both Gmail and Outlook/Microsoft 365
"""

# Email Provider Options
EMAIL_PROVIDERS = {
    'gmail': {
        'name': 'Gmail',
        'smtp_server': 'smtp.gmail.com',
        'smtp_port': 587,
        'use_tls': True,
        'instructions': '''
To use Gmail:
1. Go to https://myaccount.google.com/security
2. Enable 2-Step Verification
3. Go to https://myaccount.google.com/apppasswords
4. Generate an "App Password" for "Mail"
5. Use that 16-character password here (not your regular Gmail password)
        '''
    },
    'outlook': {
        'name': 'Outlook/Microsoft 365',
        'smtp_server': 'smtp-mail.outlook.com',
        'smtp_port': 587,
        'use_tls': True,
        'instructions': '''
To use Outlook/Microsoft 365:
1. Go to https://account.microsoft.com/security
2. Enable Two-step verification (if not already enabled)
3. Go to https://account.live.com/proofs/AppPassword
4. Generate an "App Password"
5. Use your Outlook email and the app password here
        '''
    }
}

# Default Email Settings (to be configured by user)
EMAIL_SETTINGS = {
    'enabled': False,  # Set to True to enable email sending
    'provider': 'gmail',  # 'gmail' or 'outlook'
    'sender_email': '',  # Your email address
    'sender_password': '',  # Your app password
    'sender_name': 'Discipline Office',  # Default sender name
}

def get_smtp_config(provider='gmail'):
    """Get SMTP configuration for the specified provider"""
    if provider not in EMAIL_PROVIDERS:
        provider = 'gmail'
    
    return EMAIL_PROVIDERS[provider]

def is_email_configured():
    """Check if email is properly configured"""
    return (
        EMAIL_SETTINGS['enabled'] and
        EMAIL_SETTINGS['sender_email'] and
        EMAIL_SETTINGS['sender_password']
    )
