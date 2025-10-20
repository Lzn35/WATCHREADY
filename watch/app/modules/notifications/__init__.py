#!/usr/bin/env python3
"""
Notifications Module
"""

from flask import Blueprint

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

# Import routes after blueprint creation to avoid circular imports
try:
    from . import routes
except ImportError as e:
    print(f"Warning: Could not import notifications routes: {e}")
