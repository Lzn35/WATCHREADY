from flask import Blueprint


bp = Blueprint("settings", __name__)


from . import routes  # noqa: E402,F401
from . import test_data_routes  # noqa: E402,F401


