from flask import Blueprint

bp = Blueprint("anime", __name__, template_folder="../../templates/anime")

from . import routes  # noqa: F401, E402
