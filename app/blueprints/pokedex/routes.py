from flask import render_template, request, abort
from flask_login import current_user
from . import bp
from ...extensions import db
from ...models.pokemon import Species, Form, EvolutionChain
from ...models.collection import UserCollection
from ...services.analytics_service import log_event

PER_PAGE = 24

TYPES = [
    "bug", "dark", "dragon", "electric", "fairy", "fighting",
    "fire", "flying", "ghost", "grass", "ground", "ice",
    "normal", "poison", "psychic", "rock", "steel", "water",
]


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
