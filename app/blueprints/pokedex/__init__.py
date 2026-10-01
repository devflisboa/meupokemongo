from flask import Blueprint

bp = Blueprint("pokedex", __name__)

from . import routes  # noqa: F401, E402
