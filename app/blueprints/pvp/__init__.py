from flask import Blueprint

bp = Blueprint("pvp", __name__, template_folder="../../templates/pvp")

from . import routes  # noqa: F401, E402
