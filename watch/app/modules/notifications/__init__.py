#!/usr/bin/env python3
"""
Notifications Module
"""

from flask import Blueprint

bp = Blueprint('notifications', __name__, url_prefix='/notifications')

from . import routes
