from flask import render_template, redirect, url_for, abort, flash
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.trade import TradeMatch, WhatsappClick
from ...services.matching_service import (
    run_matching_for_user, get_active_matches_for_user, get_reciprocal_trades,
)
from ...services.analytics_service import log_event


@bp.route("/")
@login_required
def index():
    # Matching automático ao abrir a tela — o usuário não precisa clicar em "Buscar matches"
    run_matching_for_user(current_user.id)
    matches = get_active_matches_for_user(current_user.id)
    reciprocal = get_reciprocal_trades(current_user.id)
    return render_template("trades/index.html", matches=matches, reciprocal=reciprocal)


@bp.route("/sync")
@login_required
def sync():
    """Roda o matching engine para o usuário atual."""
    created = run_matching_for_user(current_user.id)
    return redirect(url_for("trades.index"))


@bp.route("/whatsapp/<int:match_id>")
@login_required
def whatsapp_click(match_id: int):
    """RF11: registra o clique e redireciona para wa.me (RB10)."""
    match = db.session.get(TradeMatch, match_id)
    if not match or match.wisher_id != current_user.id:
        abort(403)

    owner = match.owner
    pokemon_name = match.form.species.name_pt or match.form.species.name
    message = (
        f"Olá, {owner.username}! Vi no MeuPokémonGO que você tem {pokemon_name} disponível para troca. "
        f"Podemos negociar? Meu código de amigo: {current_user.trainer_code or 'não informado'}"
    )
    # Só com consentimento do dono (D5) — sem isso, o contato é pelo código de amigo
    wa_url = owner.whatsapp_url(message)
    if not wa_url:
        flash(f"{owner.username} não liberou WhatsApp. Use o código de amigo para adicioná-lo no jogo.", "warning")
        return redirect(url_for("trades.index"))

    # Registrar antes de redirecionar (RB10)
    db.session.add(WhatsappClick(match_id=match_id, clicker_id=current_user.id))
    match.status = "contacted"
    db.session.commit()
    log_event("WHATSAPP_CLICK", {"match_id": match_id})
    return redirect(wa_url)


@bp.route("/fechar/<int:match_id>", methods=["POST"])
@login_required
def fechar(match_id: int):
    match = db.session.get(TradeMatch, match_id)
    if not match or match.wisher_id != current_user.id:
        abort(403)
    match.status = "completed"
    db.session.commit()
    log_event("TRADE_COMPLETED", {"match_id": match_id})
    return redirect(url_for("trades.index"))


@bp.route("/cancelar/<int:match_id>", methods=["POST"])
@login_required
def cancelar(match_id: int):
    match = db.session.get(TradeMatch, match_id)
    if not match or match.wisher_id != current_user.id:
        abort(403)
    match.status = "cancelled"
    db.session.commit()
    log_event("TRADE_CANCELLED", {"match_id": match_id})
    return redirect(url_for("trades.index"))
