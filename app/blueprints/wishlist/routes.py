from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.wishlist import Wishlist
from ...models.collection import UserCollection
from ...models.user import User
from ...models.pokemon import Form, Species, EvolutionChain
from ..collection.routes import REGIONS
from ...data.regional import exclusive_info, trade_only_in_brazil, form_category, CATEGORIES


def _reachable_owner_filter(me: User):
    """SQL equivalente a matching_service.proximity_tier(me, owner) is not None."""
    if me.can_trade_remote or not me.city:
        return db.true()
    return db.or_(
        db.and_(User.city == me.city, User.state == me.state),
        User.can_trade_remote.is_(True),
        User.city.is_(None),
    )


def get_missing_normal_forms(user_id: int, categories: set[str] | None = None) -> list[tuple[Form, Species]]:
    """
    Wishlist automática: toda forma normal que o treinador não possui, mais as formas
    alternativas das categorias pedidas (#14: regional, mega, gmax, especial).
    """
    owned_subq = (
        db.session.query(UserCollection.form_id)
        .filter(
            UserCollection.user_id == user_id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        )
        .scalar_subquery()
    )
    query = (
        db.session.query(Form, Species)
        .join(Species, Species.id == Form.species_id)
        .filter(Form.id.notin_(owned_subq))
    )
    if not categories:
        query = query.filter(Form.form_name == "normal")
    rows = query.order_by(Species.id, Form.form_name != "normal", Form.form_name).all()
    if categories:
        rows = [(f, s) for f, s in rows if f.form_name == "normal" or f.category in categories]
    return rows


def _parse_categories(raw: str) -> set[str]:
    """'?formas=regional,mega' → {'regional','mega'}; compatível com o antigo '?formas=1'."""
    if raw == "1":
        return {"regional"}
    return {c for c in raw.split(",") if c in CATEGORIES}


def build_wishlist(user: User, categories: set[str] | None = None, offers_for: User | None = None) -> dict:
    """
    A "inteligência" da wishlist num lugar só — usada na Wishlist e no Trade Binder (#18).
    Ordem: ⭐ manual → Alta (exclusivos de região no topo) → Evoluir; dentro de cada grupo,
    quem tem oferta de troca; por fim número da Pokédex.
    `offers_for`: de quem contar as ofertas de troca (padrão: o próprio usuário, com proximidade).
    """
    missing = get_missing_normal_forms(user.id, categories=categories)
    missing_ids = [f.id for f, _ in missing]

    # Prioridade = linha na tabela wishlists (opcional, um toque na estrela)
    priority_ids = {
        row[0] for row in db.session.query(Wishlist.form_id).filter_by(user_id=user.id).all()
    }

    # Quantos outros treinadores oferecem cada faltante para troca
    viewer = offers_for or user
    offers: dict[int, int] = {}
    if missing_ids:
        offers = dict(
            db.session.query(UserCollection.form_id, db.func.count(UserCollection.id))
            .join(User, User.id == UserCollection.user_id)
            .filter(
                User.visibility != "private",  # só quem aparece nas trocas (D1)
                _reachable_owner_filter(viewer),  # mesma regra de proximidade do matching (#24)
                UserCollection.form_id.in_(missing_ids),
                UserCollection.user_id != user.id,
                UserCollection.owned.is_(True),
                UserCollection.quantity > 0,
                UserCollection.for_trade.is_(True),
            )
            .group_by(UserCollection.form_id)
            .all()
        )

    evolve_from = get_evolve_sources(user.id, missing_ids)

    # Exclusivos de outra região do mundo: no Brasil, só por troca (#14)
    exclusives = {
        f.id: exclusive_info(s.id)[0]
        for f, s in missing
        if f.form_name == "normal" and trade_only_in_brazil(s.id)
    }

    missing.sort(key=lambda fs: (
        fs[0].id not in priority_ids,
        fs[0].id in evolve_from,
        fs[0].id not in exclusives,
        fs[0].id not in offers,
        fs[1].id,
        fs[0].form_name != "normal",
    ))
    return {
        "missing": missing,
        "priority_ids": priority_ids,
        "offers": offers,
        "evolve_from": evolve_from,
        "exclusives": exclusives,
    }


@bp.route("/")
@login_required
def index():
    categories = _parse_categories(request.args.get("formas", ""))
    wl = build_wishlist(current_user, categories=categories)

    # Total de formas por categoria (para os botões liga/desliga)
    category_totals: dict[str, int] = {}
    for (name,) in db.session.query(Form.form_name).filter(Form.form_name != "normal"):
        cat = form_category(name)
        if cat:
            category_totals[cat] = category_totals.get(cat, 0) + 1
    category_links = {
        cat: ",".join(sorted(categories ^ {cat}))  # liga/desliga só esta categoria
        for cat in CATEGORIES
    }

    return render_template(
        "wishlist/index.html",
        **wl,
        categories=categories,
        category_names=CATEGORIES,
        category_totals=category_totals,
        category_links=category_links,
        regions=REGIONS,
    )


def get_evolve_sources(user_id: int, missing_ids: list[int]) -> dict[int, dict]:
    """
    Prioridade automática pela cadeia evolutiva.
    Para cada faltante, procura uma pré-evolução (qualquer etapa anterior) que o treinador possui:
    se achar, basta evoluir com doces → prioridade "Evoluir" (mais fácil).
    Sem nada da linha anterior → fica de fora do dict → prioridade "Alta".
    Retorna {form_id_faltante: {"name": pré-evolução possuída, "candy": doces somados ou None}}.
    """
    if not missing_ids:
        return {}

    # to_form → [(from_form, doces)]
    parents: dict[int, list[tuple[int, int | None]]] = {}
    for from_id, to_id, candy in db.session.query(
        EvolutionChain.from_form_id, EvolutionChain.to_form_id, EvolutionChain.candy_cost
    ).all():
        parents.setdefault(to_id, []).append((from_id, candy))

    owned_ids = {
        row[0]
        for row in db.session.query(UserCollection.form_id).filter(
            UserCollection.user_id == user_id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        ).all()
    }

    source: dict[int, tuple[int, int | None]] = {}  # faltante → (pré-evolução possuída, doces)
    for fid in missing_ids:
        # sobe a cadeia (BFS) até achar a etapa possuída mais próxima, somando os doces
        queue, seen = [(p, c) for p, c in parents.get(fid, [])], set()
        while queue:
            p, cost = queue.pop(0)
            if p in seen:
                continue
            seen.add(p)
            if p in owned_ids:
                source[fid] = (p, cost)
                break
            for gp, c in parents.get(p, []):
                queue.append((gp, None if cost is None or c is None else cost + c))

    if not source:
        return {}
    names = {
        f.id: (s.name_pt or s.name)
        for f, s in db.session.query(Form, Species)
        .join(Species, Species.id == Form.species_id)
        .filter(Form.id.in_({p for p, _ in source.values()}))
        .all()
    }
    return {fid: {"name": names.get(pid, ""), "candy": cost} for fid, (pid, cost) in source.items()}


@bp.route("/priority/<int:form_id>", methods=["POST"])
@login_required
def toggle_priority(form_id: int):
    if not db.session.get(Form, form_id):
        abort(404)
    item = db.session.query(Wishlist).filter_by(user_id=current_user.id, form_id=form_id).first()
    if item:
        db.session.delete(item)
        prioritized = False
    else:
        db.session.add(Wishlist(user_id=current_user.id, form_id=form_id, priority="high"))
        prioritized = True
    db.session.commit()
    return jsonify({"ok": True, "priority": prioritized})
