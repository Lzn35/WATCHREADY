from flask import Blueprint


bp = Blueprint("cases", __name__)


from . import routes  # noqa: E402,F401


