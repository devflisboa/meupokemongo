from flask import Blueprint

bp = Blueprint("scan", __name__)

from . import routes  # noqa: F401, E402
