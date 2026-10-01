from flask import Blueprint

bp = Blueprint("collection", __name__)

from . import routes  # noqa: F401, E402
