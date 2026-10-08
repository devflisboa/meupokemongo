import os
from flask import render_template, abort, current_app, send_from_directory
from . import bp
from ...models.anime import Temporada, Episodio


@bp.route("/")
def index():
    temporadas = Temporada.query.order_by(Temporada.ordem, Temporada.numero).all()
    return render_template("anime/index.html", temporadas=temporadas)


@bp.route("/temporada/<int:temporada_id>/")
def temporada(temporada_id):
    t = Temporada.query.get_or_404(temporada_id)
    episodios = t.episodios.all()
    return render_template("anime/temporada.html", temporada=t, episodios=episodios)


@bp.route("/ep/<int:ep_id>/")
def player(ep_id):
    ep = Episodio.query.get_or_404(ep_id)
    t  = ep.temporada

    anterior  = Episodio.query.filter_by(temporada_id=t.id, numero=ep.numero - 1).first()
    proximo   = Episodio.query.filter_by(temporada_id=t.id, numero=ep.numero + 1).first()
    episodios = t.episodios.all()

    return render_template(
        "anime/player.html",
        ep=ep, temporada=t,
        anterior=anterior, proximo=proximo,
        episodios=episodios,
    )


@bp.route("/video/<path:filename>")
def video(filename):
    """Serve o arquivo de vídeo com suporte a Range requests (seek no player)."""
    folder = current_app.config.get("ANIME_VIDEO_FOLDER", "")
    if not folder or not os.path.isdir(folder):
        abort(404)
    return send_from_directory(folder, filename, conditional=True)
