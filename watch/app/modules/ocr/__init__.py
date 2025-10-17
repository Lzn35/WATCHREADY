from flask import Blueprint

bp = Blueprint('ocr', __name__)

from . import routes

