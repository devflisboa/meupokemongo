from flask import Blueprint

bp = Blueprint("trades", __name__)

from . import routes  # noqa: F401, E402
