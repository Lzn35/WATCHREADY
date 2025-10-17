from flask import Blueprint


bp = Blueprint("complaints", __name__)


from . import routes  # noqa: E402,F401


