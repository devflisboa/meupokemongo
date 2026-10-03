from flask import render_template, request, abort, jsonify
from flask_login import current_user
from . import bp
from ...extensions import db
from ...models.pokemon import Species, Form, EvolutionChain
from ...models.collection import UserCollection
from ...models.individual import UserPokemon
from ...services.analytics_service import log_event

PER_PAGE = 24

TYPES = [
    "bug", "dark", "dragon", "electric", "fairy", "fighting",
    "fire", "flying", "ghost", "grass", "ground", "ice",
    "normal", "poison", "psychic", "rock", "steel", "water",
]


@bp.route("/api/<int:species_id>")
def api_detail(species_id: int):
    species = db.session.get(Species, species_id)
    if not species:
        abort(404)

    default_form = (
        db.session.query(Form)
        .filter_by(species_id=species_id, form_name="normal")
        .first()
        or db.session.query(Form).filter_by(species_id=species_id).first()
    )

    form_ids = [
        row[0]
        for row in db.session.query(Form.id).filter_by(species_id=species_id).all()
    ]
    evolutions = (
        db.session.query(EvolutionChain)
        .filter(
            db.or_(
                EvolutionChain.from_form_id.in_(form_ids),
                EvolutionChain.to_form_id.in_(form_ids),
            )
        )
        .all()
        if form_ids
        else []
    )

    collection_data = None
    if current_user.is_authenticated and default_form:
        entry = db.session.query(UserCollection).filter_by(
            user_id=current_user.id, form_id=default_form.id
        ).first()
        collection_data = {
            "form_id": default_form.id,
            "owned": entry.owned if entry else False,
            "quantity": entry.quantity if entry else 0,
            "for_trade": entry.for_trade if entry else False,
            "has_shiny": entry.has_shiny if entry else False,
            "has_perfect": entry.has_perfect if entry else False,
            "individuals": [
                ind.to_dict()
                for ind in db.session.query(UserPokemon)
                .filter_by(user_id=current_user.id, form_id=default_form.id)
                .order_by(UserPokemon.iv_pct.desc(), UserPokemon.cp.desc())
                .all()
            ],
        }

    # Formas regionais da espécie (#14) com o status do treinador logado
    from ...data.regional import exclusive_info
    regional = (
        db.session.query(Form)
        .filter(Form.species_id == species_id, Form.form_name != "normal")
        .order_by(Form.form_name)
        .all()
    )
    reg_owned = {}
    if current_user.is_authenticated and regional:
        reg_owned = {
            uc.form_id: uc for uc in db.session.query(UserCollection).filter(
                UserCollection.user_id == current_user.id,
                UserCollection.form_id.in_([f.id for f in regional]),
            )
        }
    excl = exclusive_info(species_id)

    return jsonify({
        "id": species.id,
        "regional_forms": [
            {
                "form_id": f.id,
                "label": f.label,
                "type1": f.type1,
                "type2": f.type2,
                "sprite_url": f.sprite_url,
                "owned": bool(reg_owned.get(f.id) and reg_owned[f.id].owned and reg_owned[f.id].quantity > 0),
            }
            for f in regional
        ],
        "exclusive": {"where": excl[0], "in_brazil": excl[1]} if excl else None,
        "name": species.name,
        "name_pt": species.name_pt,
        "generation": species.generation,
        "is_legendary": species.is_legendary,
        "is_mythical": species.is_mythical,
        "capture_rate": species.capture_rate,
        "form": {
            "id": default_form.id,
            "type1": default_form.type1,
            "type2": default_form.type2,
            "sprite_url": default_form.sprite_url,
            "is_shiny_available": default_form.is_shiny_available,
        } if default_form else None,
        "collection": collection_data,
        "evolutions": [
            {
                "from_id": e.from_form.species_id,
                "from_name": e.from_form.species.name_pt or e.from_form.species.name,
                "from_sprite": e.from_form.sprite_url,
                "to_id": e.to_form.species_id,
                "to_name": e.to_form.species.name_pt or e.to_form.species.name,
                "to_sprite": e.to_form.sprite_url,
                "candy_cost": e.candy_cost,
            }
            for e in evolutions
        ],
    })


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    generation = request.args.get("generation", type=int)
    type_filter = request.args.get("type", "").strip().lower()
    captured = request.args.get("captured", "")

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

    if type_filter:
        type_subq = (
            db.session.query(Form.species_id)
            .filter(
                Form.form_name == "normal",
                db.or_(Form.type1 == type_filter, Form.type2 == type_filter),
            )
            .scalar_subquery()
        )
        query = query.filter(Species.id.in_(type_subq))

    if captured and current_user.is_authenticated:
        owned_subq = (
            db.session.query(Form.species_id)
            .join(UserCollection, UserCollection.form_id == Form.id)
            .filter(
                UserCollection.user_id == current_user.id,
                UserCollection.owned.is_(True),
                UserCollection.quantity > 0,
            )
            .scalar_subquery()
        )
        if captured == "yes":
            query = query.filter(Species.id.in_(owned_subq))
        elif captured == "no":
            query = query.filter(Species.id.not_in(owned_subq))

    pagination = query.order_by(Species.id).paginate(page=page, per_page=PER_PAGE, error_out=False)

    owned_form_ids: set[int] = set()
    if current_user.is_authenticated and pagination.items:
        species_ids = [s.id for s in pagination.items]
        owned_rows = (
            db.session.query(UserCollection.form_id)
            .join(Form, Form.id == UserCollection.form_id)
            .filter(
                Form.species_id.in_(species_ids),
                UserCollection.user_id == current_user.id,
                UserCollection.owned.is_(True),
                UserCollection.quantity > 0,
            )
            .all()
        )
        owned_form_ids = {row[0] for row in owned_rows}

    log_event("PAGE_VIEW", {"page": "pokedex", "q": q, "generation": generation})
    return render_template(
        "pokedex/index.html",
        pagination=pagination,
        q=q,
        generation=generation,
        type_filter=type_filter,
        captured=captured,
        owned_form_ids=owned_form_ids,
        types=TYPES,
    )


@bp.route("/<int:species_id>")
def detail(species_id: int):
    species = db.session.get(Species, species_id)
    if not species:
        abort(404)

    form_ids = [f.id for f in species.forms]
    evolutions = db.session.query(EvolutionChain).filter(
        db.or_(
            EvolutionChain.from_form_id.in_(form_ids),
            EvolutionChain.to_form_id.in_(form_ids),
        )
    ).all()

    collection_entry = None
    if current_user.is_authenticated:
        default_form = species.forms.filter_by(form_name="normal").first()
        if default_form:
            collection_entry = db.session.query(UserCollection).filter_by(
                user_id=current_user.id, form_id=default_form.id
            ).first()

    log_event("POKEMON_VIEW", {"species_id": species_id})
    return render_template(
        "pokedex/detail.html",
        species=species,
        evolutions=evolutions,
        collection_entry=collection_entry,
    )
