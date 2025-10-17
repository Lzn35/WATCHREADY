from flask import Blueprint, send_from_directory, abort, current_app
from flask_login import login_required
import os

media_bp = Blueprint('media', __name__)

@media_bp.route('/view-file/<path:filename>')
@login_required
def view_file(filename):
    uploads = current_app.config.get('UPLOAD_FOLDER', 'uploads')
    safe_path = os.path.join(uploads, filename)
    uploads_real = os.path.realpath(uploads)
    requested_real = os.path.realpath(safe_path)
    if not requested_real.startswith(uploads_real):
        abort(404)
    if not os.path.exists(safe_path):
        abort(404)
    return send_from_directory(uploads, filename, as_attachment=False)

