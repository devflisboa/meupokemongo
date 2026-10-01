from flask import Blueprint

bp = Blueprint("wishlist", __name__)

from . import routes  # noqa: F401, E402
