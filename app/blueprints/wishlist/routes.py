from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.wishlist import Wishlist
from ...models.collection import UserCollection
from ...models.user import User
from ...models.pokemon import Form, Species, EvolutionChain
from ..collection.routes import REGIONS


def get_missing_normal_forms(user_id: int) -> list[tuple[Form, Species]]:
    """Wishlist automática: toda forma normal que o treinador ainda não possui."""
    owned_subq = (
        db.session.query(UserCollection.form_id)
        .filter(
            UserCollection.user_id == user_id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        )
        .scalar_subquery()
    )
    return (
        db.session.query(Form, Species)
        .join(Species, Species.id == Form.species_id)
        .filter(Form.form_name == "normal", Form.id.notin_(owned_subq))
        .order_by(Species.id)
        .all()
    )


@bp.route("/")
@login_required
def index():
    missing = get_missing_normal_forms(current_user.id)
    missing_ids = [f.id for f, _ in missing]

    # Prioridade = linha na tabela wishlists (opcional, um toque na estrela)
    priority_ids = {
        row[0]
        for row in db.session.query(Wishlist.form_id).filter_by(user_id=current_user.id).all()
    }

    # Quantos outros treinadores oferecem cada faltante para troca
    offers: dict[int, int] = {}
    if missing_ids:
        offers = dict(
            db.session.query(UserCollection.form_id, db.func.count(UserCollection.id))
            .join(User, User.id == UserCollection.user_id)
            .filter(
                User.visibility != "private",  # só quem aparece nas trocas (D1)
                UserCollection.form_id.in_(missing_ids),
                UserCollection.user_id != current_user.id,
                UserCollection.owned.is_(True),
                UserCollection.quantity > 0,
                UserCollection.for_trade.is_(True),
            )
            .group_by(UserCollection.form_id)
            .all()
        )

    evolve_from = get_evolve_sources(current_user.id, missing_ids)

    # ⭐ manual primeiro; depois Alta (nada da família) antes de Evoluir;
    # dentro de cada grupo, quem tem oferta de troca; por fim número da Pokédex
    missing.sort(key=lambda fs: (
        fs[0].id not in priority_ids,
        fs[0].id in evolve_from,
        fs[0].id not in offers,
        fs[1].id,
    ))

    return render_template(
        "wishlist/index.html",
        missing=missing,
        priority_ids=priority_ids,
        offers=offers,
        evolve_from=evolve_from,
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
