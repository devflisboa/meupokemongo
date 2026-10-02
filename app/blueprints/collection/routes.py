from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.collection import UserCollection
from ...models.pokemon import Form, Species
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

    if show == "owned":
        query = query.filter(Species.id.in_(owned_species_ids))
    elif show == "missing":
        query = query.filter(Species.id.notin_(owned_species_ids))

    pagination = query.order_by(Species.id).paginate(page=page, per_page=24, error_out=False)

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
    entry.for_trade = for_trade if (owned and quantity > 0) else False
    entry.has_shiny = has_shiny if owned else False
    entry.shiny_qty = shiny_qty if has_shiny else 0

    db.session.commit()
    return jsonify({
        "ok": True,
        "owned": entry.owned,
        "quantity": entry.quantity,
        "for_trade": entry.for_trade,
        "has_shiny": entry.has_shiny,
        "shiny_qty": entry.shiny_qty,
    })
