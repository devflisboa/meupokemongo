from flask import Blueprint

bp = Blueprint("jornada", __name__, template_folder="../../templates/jornada")

from . import routes  # noqa: F401, E402
