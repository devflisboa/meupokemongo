"""Jornada (#27) — páginas e API JSON. Regras em app/services/jornada/.

Páginas: / (Mapa Global, público) · /jogar · /ranking · /time · /treinador/<u> ·
         /hall-da-fama (público) · /descobertas
"""
from flask import abort, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from . import bp
from ...extensions import db, limiter
from ...services.jornada import motor, pvp, social
from ...services.jornada.conteudo import carregar


def _por_usuario() -> str:
    return f"user:{current_user.get_id()}"


@bp.errorhandler(motor.JogoErro)
def _erro_jogo(e: motor.JogoErro):
    db.session.rollback()
    return jsonify(ok=False, erro=e.mensagem), e.status


def _ok(res: dict):
    social.limpar_cache()            # o mapa reflete a jogada na hora para quem jogou
    return jsonify(ok=True, resultado=res, estado=motor.estado(current_user.id))


def _json() -> dict:
    return request.get_json(silent=True) or {}


def _ids(campo: str = "ids") -> list[int]:
    ids = _json().get(campo)
    if not isinstance(ids, list) or not all(isinstance(i, int) for i in ids):
        raise motor.JogoErro("Lista de criaturas inválida.")
    return ids


def _ctx(**extra) -> dict:
    """Contexto comum do layout da Jornada (header com PP/energia quando logado)."""
    c = carregar()
    est = motor.estado(current_user.id) if current_user.is_authenticated else None
    return {"jogo": c.jogo, "itens": c.itens, "eu": est, **extra}


# ── páginas ────────────────────────────────────────────────────────────────

@bp.route("/")
def index():
    fase = 1
    if current_user.is_authenticated:
        fase = motor.obter_jogador(current_user.id).fase
        db.session.commit()
    return render_template("jornada/mapa.html", **_ctx(mapa=social.mapa(fase), aba="mapa"))


@bp.route("/jogar")
@login_required
def jogar():
    ctx = _ctx(aba="jogar")
    fase = carregar().fase(ctx["eu"]["fase"])
    return render_template("jornada/jogar.html", regiao=fase.regiao, casas=fase.casas,
                           vizinhos=social.vizinhos(fase.numero, current_user.id),
                           feed=social.feed(fase.numero, excluir_user=current_user.id, limite=15),
                           ultimo_turno=social.ultimo_turno_id(), **ctx)


@bp.route("/ranking")
@login_required
def ranking():
    ctx = _ctx(aba="ranking")
    aba = request.args.get("aba", "fase")
    fase = None if aba == "global" else ctx["eu"]["fase"]
    return render_template("jornada/ranking.html", ranking=social.ranking(fase, current_user.id),
                           aba_ranking=aba, **ctx)


@bp.route("/time")
@login_required
def time():
    return render_template("jornada/time.html", **_ctx(aba="time"))


@bp.route("/treinador/<username>")
@login_required
def treinador(username: str):
    ctx = _ctx(aba="perfil" if username.lower() == current_user.username.lower() else "mapa")
    card = social.card(username, current_user.id)
    if not card:
        abort(404)
    return render_template("jornada/treinador.html", card=card, **ctx)


@bp.route("/eu")
@login_required
def eu():
    motor.obter_jogador(current_user.id)
    db.session.commit()
    return redirect(url_for("jornada.treinador", username=current_user.username))


@bp.route("/hall-da-fama")
def hall():
    return render_template("jornada/hall.html", campeoes=social.hall_da_fama(1), **_ctx(aba="mapa"))


@bp.route("/descobertas")
@login_required
def descobertas():
    return render_template("jornada/descobertas.html",
                           cat=social.descobertas(1, current_user.id), **_ctx(aba="time"))


# ── API — leitura ──────────────────────────────────────────────────────────

@bp.route("/api/estado")
@login_required
def api_estado():
    est = motor.estado(current_user.id)
    desde = request.args.get("desde", type=int)
    out = {"ok": True, "estado": est}
    if desde is not None:
        out["feed"] = social.feed(est["fase"], desde=desde, excluir_user=current_user.id)
        out["vizinhos"] = social.vizinhos(est["fase"], current_user.id)
        out["ultimo_turno"] = social.ultimo_turno_id()
    return jsonify(out)


@bp.route("/api/mapa")
def api_mapa():
    return jsonify(ok=True, mapa=social.mapa(request.args.get("fase", 1, type=int)))


# ── API — ações ────────────────────────────────────────────────────────────

@bp.route("/api/rolar", methods=["POST"])
@login_required
@limiter.limit("30/minute", key_func=_por_usuario)
def api_rolar():
    return _ok(motor.rolar(current_user.id))


@bp.route("/api/capturar", methods=["POST"])
@login_required
@limiter.limit("30/minute", key_func=_por_usuario)
def api_capturar():
    return _ok(motor.capturar(current_user.id, item=_json().get("item") or None))


@bp.route("/api/pular", methods=["POST"])
@login_required
def api_pular():
    return _ok(motor.pular(current_user.id))


@bp.route("/api/item", methods=["POST"])
@login_required
def api_item():
    d = _json()
    return _ok(motor.usar_item(current_user.id, d.get("item", ""), d.get("criatura")))


@bp.route("/api/time", methods=["POST"])
@login_required
def api_time():
    return _ok(motor.definir_time(current_user.id, _ids()))


@bp.route("/api/desafio", methods=["POST"])
@login_required
@limiter.limit("10/minute", key_func=_por_usuario)
def api_desafio():
    return _ok(motor.desafio(current_user.id, _ids()))


@bp.route("/api/pvp/desafiar", methods=["POST"])
@login_required
@limiter.limit("10/minute", key_func=_por_usuario)
def api_pvp_desafiar():
    d = _json()
    if not isinstance(d.get("criatura"), int):
        raise motor.JogoErro("Escolha a criatura que vai lutar.")
    return _ok(pvp.desafiar(current_user.id, str(d.get("alvo", "")), d["criatura"], bool(d.get("isca"))))


@bp.route("/api/pvp/<int:batalha_id>/responder", methods=["POST"])
@login_required
@limiter.limit("10/minute", key_func=_por_usuario)
def api_pvp_responder(batalha_id: int):
    d = _json()
    if not isinstance(d.get("criatura"), int):
        raise motor.JogoErro("Escolha a criatura que vai lutar.")
    return _ok(pvp.responder(current_user.id, batalha_id, d["criatura"], bool(d.get("isca"))))
