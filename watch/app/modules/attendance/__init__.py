from flask import Blueprint


bp = Blueprint("attendance", __name__)


from . import routes  # noqa: E402,F401


