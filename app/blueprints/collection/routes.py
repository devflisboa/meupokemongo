from flask import render_template, request, jsonify, abort
from flask_login import login_required, current_user
from . import bp
from ...extensions import db
from ...models.collection import UserCollection
from ...models.pokemon import Form, Species


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


@bp.route("/upsert", methods=["POST"])
@login_required
def upsert():
    form_id = request.form.get("form_id", type=int)
    owned = request.form.get("owned") == "true"
    quantity = max(0, request.form.get("quantity", 0, type=int))
    for_trade = request.form.get("for_trade") == "true"
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

    db.session.commit()
    return jsonify({"ok": True, "owned": entry.owned, "quantity": entry.quantity, "for_trade": entry.for_trade})
