from datetime import date
from flask import render_template, abort, request, jsonify, current_app
from flask_login import current_user
from . import bp
from ...extensions import csrf
from ...services.collection_service import get_collection_stats, get_missing_pokemon, get_pending_evolutions
from ...services.matching_service import get_active_matches_for_user
from ...services.analytics_service import log_event
from ...extensions import db
from ...models.user import User
from ...models.collection import UserCollection
from ...models.pokemon import Form

# Meses em inglês para montar a URL do site oficial
_MONTH_EN = {
    1: "january", 2: "february", 3: "march", 4: "april",
    5: "may", 6: "june", 7: "july", 8: "august",
    9: "september", 10: "october", 11: "november", 12: "december",
}

GAME_EVENTS = [
    {
        "title": "Semana Mundial do Espaço",
        "category": "Evento Especial",
        "date": "4–10 de out",
        "description": "Pikachu Astronauta faz estreia mundial! Pesquisa temporária gratuita com encontro garantido.",
        "badge": "bg-indigo-100 text-indigo-700",
        "image_url": "https://lh3.googleusercontent.com/qmKASG93iVfM7wXo20u46tH4KyFM3Y52Rp0wBNNaoPblF-2MT0Qmra8EdlN4Uqb8n-x1I_vaZEOBokaBvFJK9-vlPXRsI1OU2zj9Qds",
        "url": "https://pokemongo.com/en/news/world-space-week-2026",
    },
    {
        "title": "Dia Comunitário — Zorua",
        "category": "Dia Comunitário",
        "date": "10 de out · 14h–17h",
        "description": "Zorua em destaque. Evolua para Zoroark e aprenda Soco Enganador. Bônus de PE e Doces.",
        "badge": "bg-gray-100 text-gray-700",
        "image_url": "https://lh3.googleusercontent.com/ceoPPXZSHd10nn28HI8DVWvgnXq2vQeWRgsjjC1jHs0CTw0YgowKWrSoKJHNolzfFnG2UoCcGch2mfbN8yoNyii3x15BmmXn8TqrG0U",
        "url": "https://pokemongo.com/en/news/communityday-october-2026-zorua",
    },
    {
        "title": "Maratona das Folhas: Caminhada Companheira",
        "category": "Evento Especial",
        "date": "13–19 de out",
        "description": "Bramblin estreia no GO! Mega Manectric alcança o Super Nível. Growlithe de Hisui com Incenso.",
        "badge": "bg-emerald-100 text-emerald-700",
        "image_url": "https://lh3.googleusercontent.com/zk6NTDv0rngAmui4G_58zN_RpKsMy66tEAIFyTQkpHpQeFh0tAyDSmh2OdD61EtEfA1g9jmqnubXIArQ6mkSIzUy6I97URVZ__rQ0A",
        "url": "https://pokemongo.com/en/news/fall-marathon-buddy-trek-2026",
    },
    {
        "title": "Dia de Chocar Sandile",
        "category": "Hatch Day",
        "date": "17 de out",
        "description": "Sandile em Ovos de 2 km com mais chance de Brilhante! ½ distância de incubação e Candy extra.",
        "badge": "bg-amber-100 text-amber-700",
        "image_url": "https://lh3.googleusercontent.com/1KTYlzx5ELkb-sjHcUnlkqRZqgH6o6zn_coO2G54QtULKb7XU7f4mSbsC0otOarQey9fR5sO0bLSRI5pjF50aiK-CpcQgujdYxcpKQQR",
        "url": "https://pokemongo.com/en/news/sandile-hatch-day-2026",
    },
    {
        "title": "adidas × Pokémon GO",
        "category": "Parceria",
        "date": "até 13 fev 2027",
        "description": "Visite uma loja adidas para desbloquear pesquisa com bonê, jaqueta e encontro com Lucario.",
        "badge": "bg-slate-100 text-slate-700",
        "image_url": "https://lh3.googleusercontent.com/V8KxsOIOlODCRRSMML9kQVBwd34t9teBV-y7AmaPr-w0liKdvKDyl_X03IT8C-61eHglnseLZzAYVZK-wS86vy02bf9aYYbPIQynZv69",
        "url": "https://pokemongo.com/news/pokemon-x-adidas-2026",
    },
    {
        "title": "Área Selvagem GO 2026",
        "category": "GO Wild Area",
        "date": "6–8 nov (presencial) · 14–15 nov (global)",
        "description": "Dialga e Palkia Dinamax estreiam! Evento presencial em Sendai e Cidade do México.",
        "badge": "bg-teal-100 text-teal-700",
        "image_url": "https://lh3.googleusercontent.com/-DOgjFf8fTm7lMO6LYK5vXr4yVXqo-SQ04L6OXobY_4ty_su7sYjEI6fpIIDHs7UOvvc_9CRP1Ox7kNSv1ynowxxFBT8ZvS7JTDw8D4",
        "url": "https://pokemongo.com/gowildarea",
    },
]


@bp.route("/")
def index():
    log_event("PAGE_VIEW", {"page": "home"})

    stats = None
    missing = []
    pending_evolutions = []
    matches = []
    quick_wins_total = 0

    if current_user.is_authenticated:
        from ..wishlist.routes import get_missing_normal_forms, get_evolve_sources
        stats = get_collection_stats(current_user.id)
        missing = get_missing_pokemon(current_user.id)[:5]
        pending_evolutions = get_pending_evolutions(current_user.id)[:3]
        matches = get_active_matches_for_user(current_user.id)[:4]
        # Mesma regra da Wishlist: faltantes que basta evoluir de algo que já possui
        missing_ids = [f.id for f, _ in get_missing_normal_forms(current_user.id)]
        quick_wins_total = len(get_evolve_sources(current_user.id, missing_ids))

    total_trainers = db.session.query(User).count()

    today = date.today()
    events_page_url = (
        f"https://pokemongo.com/pt-BR/events/{_MONTH_EN[today.month]}-{today.year}"
    )

    return render_template(
        "main/index.html",
        stats=stats,
        missing=missing,
        pending_evolutions=pending_evolutions,
        quick_wins_total=quick_wins_total,
        matches=matches,
        total_trainers=total_trainers,
        game_events=GAME_EVENTS,
        events_page_url=events_page_url,
    )


@bp.route("/api/log", methods=["POST"])
@csrf.exempt
def api_log():
    data = request.get_json(force=True) or {}
    event = str(data.get("event", ""))[:64]
    if event:
        log_event(event, data.get("data", {}))
    return jsonify({"ok": True})


@bp.route("/trade/<username>")
def trade_binder(username: str):
    """
    Trade Binder público (#18): link para divulgar — o que tenho para troca e o que procuro.
    Sem login. Logado, destaca o que o visitante tem e o dono procura (troca de mão dupla).
    """
    from ...models.wishlist import Wishlist
    from ...services.matching_service import proximity_tier, TIER_LABEL

    owner = db.session.query(User).filter_by(username=username).first_or_404()
    is_self = current_user.is_authenticated and current_user.id == owner.id
    if not owner.show_in_trades and not (is_self or (current_user.is_authenticated and current_user.is_admin)):
        abort(404)

    owned = {
        uc.form_id: uc
        for uc in db.session.query(UserCollection).filter(
            UserCollection.user_id == owner.id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        )
    }
    trade_forms = (
        db.session.query(Form)
        .filter(Form.id.in_([fid for fid, uc in owned.items() if uc.for_trade] or [-1]))
        .order_by(Form.species_id)
        .all()
    )

    # O que o dono procura: ⭐ prioridades dele que ainda faltam
    priority_forms = (
        db.session.query(Form)
        .join(Wishlist, Wishlist.form_id == Form.id)
        .filter(Wishlist.user_id == owner.id, Form.id.notin_(list(owned) or [-1]))
        .order_by(Form.species_id)
        .all()
    )

    # Visitante logado: o que ELE tem para troca e falta ao dono → convite de mão dupla
    i_can_offer, tier_label = [], None
    if current_user.is_authenticated and not is_self:
        i_can_offer = (
            db.session.query(Form)
            .join(UserCollection, UserCollection.form_id == Form.id)
            .filter(
                UserCollection.user_id == current_user.id,
                UserCollection.owned.is_(True),
                UserCollection.quantity > 0,
                UserCollection.for_trade.is_(True),
                Form.id.notin_(list(owned) or [-1]),
            )
            .order_by(Form.species_id)
            .all()
        )
        tier = proximity_tier(current_user, owner)
        tier_label = TIER_LABEL.get(tier) if tier is not None else "Fora do seu alcance de troca"

    total_normal = db.session.query(Form).filter_by(form_name="normal").count()
    log_event("PAGE_VIEW", {"page": "trade_binder", "owner": owner.username})
    return render_template(
        "trades/binder.html",
        owner=owner,
        is_self=is_self,
        trade_forms=trade_forms,
        collection_map=owned,
        priority_forms=priority_forms,
        missing_count=total_normal - len(owned),
        i_can_offer=i_can_offer,
        tier_label=tier_label,
        share_url=request.url.split("?")[0],
    )


@bp.route("/estoque/<username>")
def estoque(username: str):
    """Página pública de coleção completa — sem login obrigatório."""
    profile_user = db.session.query(User).filter_by(username=username).first_or_404()

    # Quem desligou "aparecer nas trocas" só é visível para si mesmo (e admin)
    is_self = current_user.is_authenticated and current_user.id == profile_user.id
    is_admin = current_user.is_authenticated and current_user.is_admin
    if not profile_user.show_in_trades and not (is_self or is_admin):
        abort(404)

    # IDs de formas que o usuário possui (owned) e para troca
    collection_map: dict[int, UserCollection] = {
        uc.form_id: uc
        for uc in db.session.query(UserCollection).filter_by(
            user_id=profile_user.id, owned=True
        ).filter(UserCollection.quantity > 0).all()
    }
    trade_form_ids = {
        fid for fid, uc in collection_map.items() if uc.for_trade
    }

    # Todas as formas normais, ordenadas por species_id
    all_forms = (
        db.session.query(Form)
        .filter_by(form_name="normal")
        .order_by(Form.species_id)
        .all()
    )

    owned_forms = [f for f in all_forms if f.id in collection_map]
    missing_forms = [f for f in all_forms if f.id not in collection_map]
    trade_forms = [f for f in all_forms if f.id in trade_form_ids]

    # #20: faltantes vão como JSON compacto e o navegador desenha 30 por vez
    # (antes: ~770 cards ocultos no HTML, pesado no celular)
    poke_name = current_app.jinja_env.filters["poke_name"]
    missing_data = [
        {
            "id": f.species_id,
            "n": poke_name(f.species.name_pt or f.species.name),
            "t": f.type1 or "",
            "s": f.sprite_url or "",
            "b": "m" if f.species.is_mythical else ("l" if f.species.is_legendary else ""),
        }
        for f in missing_forms
    ]

    stats = get_collection_stats(profile_user.id)
    share_url = request.url.split("?")[0]

    all_users = []
    if current_user.is_authenticated and current_user.is_admin:
        all_users = db.session.query(User).order_by(User.username).all()

    return render_template(
        "main/estoque.html",
        profile_user=profile_user,
        all_forms=all_forms,
        owned_forms=owned_forms,
        missing_forms=missing_forms,
        missing_data=missing_data,
        trade_forms=trade_forms,
        collection_map=collection_map,
        stats=stats,
        share_url=share_url,
        all_users=all_users,
    )
