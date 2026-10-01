from flask import Blueprint

bp = Blueprint("import_", __name__)

from . import routes  # noqa: F401, E402
