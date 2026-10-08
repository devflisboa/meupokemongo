from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from sqlalchemy import case
from . import bp
from ...extensions import db
from ...models.collection import UserCollection
from ...models.individual import UserPokemon
from ...models.pokemon import Form, Species, EvolutionChain
from ...services.analytics_service import log_event

REGIONS = [
    {"name": "Kanto",  "start": 1,   "end": 151,  "count": 151},
    {"name": "Johto",  "start": 152,  "end": 251,  "count": 100},
    {"name": "Hoenn",  "start": 252,  "end": 386,  "count": 135},
    {"name": "Sinnoh", "start": 387,  "end": 493,  "count": 107},
    {"name": "Unova",  "start": 494,  "end": 649,  "count": 156},
    {"name": "Kalos",  "start": 650,  "end": 721,  "count": 72},
    {"name": "Alola",  "start": 722,  "end": 809,  "count": 86},
    {"name": "Galar",  "start": 810,  "end": 898,  "count": 89},
    {"name": "Hisui",  "start": 899,  "end": 905,  "count": 6},
    {"name": "Paldea", "start": 906,  "end": 1025, "count": 120},
]


@bp.route("/")
@login_required
def index():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    generation = request.args.get("generation", type=int)
    show = request.args.get("show", "all")  # all | owned | missing

    query = db.session.query(Species)
    if q:
        if q.isdigit():
            query = query.filter(Species.id == int(q))
        else:
            query = query.filter(
                db.or_(Species.name.ilike(f"%{q}%"), Species.name_pt.ilike(f"%{q}%"))
            )
    if generation:
        query = query.filter(Species.generation == generation)

    # Owned form IDs do usuário (para filtros)
    owned_form_ids = {
        row[0]
        for row in db.session.query(UserCollection.form_id).filter(
            UserCollection.user_id == current_user.id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        ).all()
    }
    owned_species_ids = {
        row[0]
        for row in db.session.query(Form.species_id).filter(Form.id.in_(owned_form_ids)).all()
    } if owned_form_ids else set()

    # Progresso Shiny / 100% (#15) — sobre as entradas possuídas
    flags = db.session.query(Form.species_id, UserCollection.has_shiny, UserCollection.has_perfect).join(
        UserCollection, UserCollection.form_id == Form.id
    ).filter(
        UserCollection.user_id == current_user.id,
        UserCollection.owned.is_(True),
        UserCollection.quantity > 0,
    ).all()
    shiny_species = {sid for sid, sh, _ in flags if sh}
    perfect_species = {sid for sid, _, pf in flags if pf}
    progress = {
        "shiny": len(shiny_species),
        "perfect": len(perfect_species),
        "shundo": len(shiny_species & perfect_species),
    }

    if show == "owned":
        query = query.filter(Species.id.in_(owned_species_ids))
    elif show == "missing":
        query = query.filter(Species.id.notin_(owned_species_ids))
    elif show == "shiny":
        query = query.filter(Species.id.in_(shiny_species or {-1}))
    elif show == "perfect":
        query = query.filter(Species.id.in_(perfect_species or {-1}))

    # Espécies com cadeia de evolução primeiro; sem evolução nenhuma por último
    chain_species_sq = (
        db.session.query(Form.species_id)
        .filter(
            Form.id.in_(
                db.session.query(EvolutionChain.from_form_id)
                .union(db.session.query(EvolutionChain.to_form_id))
            )
        )
        .subquery()
    )
    has_evol = case((Species.id.in_(chain_species_sq), 0), else_=1)
    pagination = query.order_by(has_evol, Species.id).paginate(page=page, per_page=24, error_out=False)

    page_species_ids = [s.id for s in pagination.items]

    forms_by_species = {}
    if page_species_ids:
        for f in db.session.query(Form).filter(
            Form.species_id.in_(page_species_ids),
            Form.form_name == "normal",
        ).all():
            forms_by_species[f.species_id] = f

    form_ids_page = [f.id for f in forms_by_species.values()]
    entries_by_form = {}
    if form_ids_page:
        for e in db.session.query(UserCollection).filter(
            UserCollection.user_id == current_user.id,
            UserCollection.form_id.in_(form_ids_page),
        ).all():
            entries_by_form[e.form_id] = e

    species_data = {}
    for sid in page_species_ids:
        form = forms_by_species.get(sid)
        entry = entries_by_form.get(form.id) if form else None
        species_data[sid] = {"form": form, "entry": entry}

    total_owned = len(owned_species_ids)
    total_species = db.session.query(Species).count()

    return render_template(
        "collection/index.html",
        pagination=pagination,
        species_data=species_data,
        q=q,
        generation=generation,
        show=show,
        total_owned=total_owned,
        total_species=total_species,
        progress=progress,
    )


@bp.route("/catalogar")
@login_required
def catalogar():
    regiao_name = request.args.get("regiao", "Kanto")
    region = next((r for r in REGIONS if r["name"] == regiao_name), REGIONS[0])

    rows = (
        db.session.query(Form, Species)
        .join(Species, Species.id == Form.species_id)
        .filter(
            Form.form_name == "normal",
            Species.id >= region["start"],
            Species.id <= region["end"],
        )
        .order_by(Species.id)
        .all()
    )

    form_ids = [f.id for f, s in rows]
    owned_set: set[int] = set()
    if form_ids:
        owned_set = {
            uc.form_id
            for uc in db.session.query(UserCollection).filter(
                UserCollection.user_id == current_user.id,
                UserCollection.form_id.in_(form_ids),
                UserCollection.owned.is_(True),
                UserCollection.quantity > 0,
            ).all()
        }

    return render_template(
        "collection/catalogar_regiao.html",
        rows=rows,
        owned_set=owned_set,
        region=region,
        regions=REGIONS,
    )


@bp.route("/regiao", methods=["POST"])
@login_required
def regiao():
    data = request.get_json(force=True) or {}
    start = int(data.get("start", 0))
    end = int(data.get("end", 0))
    modo = data.get("modo", "falta")
    ids_marcados = set(int(i) for i in data.get("ids", []))

    all_form_ids = [
        row[0]
        for row in db.session.query(Form.id)
        .join(Species, Species.id == Form.species_id)
        .filter(
            Form.form_name == "normal",
            Species.id >= start,
            Species.id <= end,
        )
        .all()
    ]

    if modo == "falta":
        ids_owned = set(all_form_ids) - ids_marcados
        ids_missing = ids_marcados
    else:
        ids_owned = ids_marcados
        ids_missing = set(all_form_ids) - ids_marcados

    existing: dict[int, UserCollection] = {
        uc.form_id: uc
        for uc in db.session.query(UserCollection).filter(
            UserCollection.user_id == current_user.id,
            UserCollection.form_id.in_(all_form_ids),
        ).all()
    }

    for fid in ids_owned:
        uc = existing.get(fid)
        if not uc:
            uc = UserCollection(user_id=current_user.id, form_id=fid)
            db.session.add(uc)
        uc.owned = True
        uc.quantity = max(getattr(uc, "quantity", 0) or 0, 1)

    for fid in ids_missing:
        uc = existing.get(fid)
        if uc:
            uc.owned = False
            uc.quantity = 0
            uc.for_trade = False
            uc.has_perfect = False

    db.session.commit()
    log_event("REGIAO_CATALOGAR", {"modo": modo, "start": start, "end": end, "count_owned": len(ids_owned)})
    return jsonify({"ok": True, "owned": len(ids_owned), "missing": len(ids_missing)})


@bp.route("/upsert", methods=["POST"])
@login_required
def upsert():
    form_id = request.form.get("form_id", type=int)
    owned = request.form.get("owned") == "true"
    quantity = max(0, request.form.get("quantity", 0, type=int))
    for_trade = request.form.get("for_trade") == "true"
    has_shiny = request.form.get("has_shiny") == "true"
    shiny_qty = max(0, request.form.get("shiny_qty", 0, type=int))
    notes = request.form.get("notes", "")

    form = db.session.get(Form, form_id)
    if not form:
        abort(404)

    entry = db.session.query(UserCollection).filter_by(
        user_id=current_user.id, form_id=form_id
    ).first()
    if not entry:
        entry = UserCollection(user_id=current_user.id, form_id=form_id)
        db.session.add(entry)

    entry.owned = owned
    entry.quantity = quantity
    entry.notes = notes
    # Mega Evolução é temporária no GO: não existe "Mega para troca"
    entry.for_trade = for_trade if (owned and quantity > 0 and form.category != "mega") else False
    entry.has_shiny = has_shiny if owned else False
    entry.shiny_qty = shiny_qty if has_shiny else 0
    # has_perfect só muda quando enviado — telas que não conhecem o campo não o zeram
    if "has_perfect" in request.form:
        entry.has_perfect = request.form.get("has_perfect") == "true"
    if not (owned and quantity > 0):
        entry.has_perfect = False

    db.session.commit()
    return jsonify({
        "ok": True,
        "owned": entry.owned,
        "quantity": entry.quantity,
        "for_trade": entry.for_trade,
        "has_shiny": entry.has_shiny,
        "shiny_qty": entry.shiny_qty,
        "has_perfect": entry.has_perfect,
    })


def _iv(name: str) -> int | None:
    v = request.form.get(name, type=int)
    return v if v is not None and 0 <= v <= 15 else None


@bp.route("/individual", methods=["POST"])
@login_required
def individual_add():
    """Cadastro manual rápido de um exemplar (alternativa ao PokeGenie Pro). Tudo opcional."""
    form_id = request.form.get("form_id", type=int)
    if not db.session.get(Form, form_id):
        abort(404)

    atk, dfn, sta = _iv("atk_iv"), _iv("def_iv"), _iv("sta_iv")
    ind = UserPokemon(
        user_id=current_user.id,
        form_id=form_id,
        source="manual",
        cp=request.form.get("cp", type=int),
        atk_iv=atk,
        def_iv=dfn,
        sta_iv=sta,
        iv_pct=round((atk + dfn + sta) / 45 * 100, 1) if None not in (atk, dfn, sta) else None,
        is_shiny=request.form.get("is_shiny") == "true",
        is_lucky=request.form.get("is_lucky") == "true",
        is_shadow=request.form.get("is_shadow") == "true",
    )
    db.session.add(ind)

    # Mantém o resumo da coleção coerente: exemplar cadastrado = capturado
    entry = db.session.query(UserCollection).filter_by(user_id=current_user.id, form_id=form_id).first()
    if not entry:
        entry = UserCollection(user_id=current_user.id, form_id=form_id, quantity=0)
        db.session.add(entry)
    entry.owned = True
    db.session.flush()  # inclui o novo exemplar na contagem
    entry.quantity = max(entry.quantity or 0, _count_individuals(form_id))
    if ind.is_perfect:
        entry.has_perfect = True
    if ind.is_shiny:
        entry.has_shiny = True

    db.session.commit()
    return jsonify({"ok": True, "individual": ind.to_dict(), "has_perfect": entry.has_perfect,
                    "quantity": entry.quantity})


@bp.route("/individual/<int:ind_id>/delete", methods=["POST"])
@login_required
def individual_delete(ind_id: int):
    ind = db.session.get(UserPokemon, ind_id)
    if not ind or ind.user_id != current_user.id:
        abort(403)
    form_id, was_perfect = ind.form_id, ind.is_perfect
    db.session.delete(ind)
    db.session.flush()

    entry = db.session.query(UserCollection).filter_by(user_id=current_user.id, form_id=form_id).first()
    if entry and was_perfect:
        entry.has_perfect = any(
            i.is_perfect
            for i in db.session.query(UserPokemon).filter_by(user_id=current_user.id, form_id=form_id)
        )
    db.session.commit()
    return jsonify({"ok": True, "has_perfect": entry.has_perfect if entry else False})


def _count_individuals(form_id: int) -> int:
    return db.session.query(UserPokemon).filter_by(user_id=current_user.id, form_id=form_id).count()