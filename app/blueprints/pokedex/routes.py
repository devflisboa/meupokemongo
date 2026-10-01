from flask import render_template, request, abort
from flask_login import current_user
from . import bp
from ...extensions import db
from ...models.pokemon import Species, Form, EvolutionChain
from ...services.analytics_service import log_event

PER_PAGE = 20


@bp.route("/")
def index():
    page = request.args.get("page", 1, type=int)
    q = request.args.get("q", "").strip()
    generation = request.args.get("generation", type=int)

    query = db.session.query(Species)
    if q:
        if q.isdigit():
            query = query.filter(Species.id == int(q))
        else:
            query = query.filter(Species.name.ilike(f"%{q}%"))
    if generation:
        query = query.filter(Species.generation == generation)

    pagination = query.order_by(Species.id).paginate(page=page, per_page=PER_PAGE, error_out=False)

    log_event("PAGE_VIEW", {"page": "pokedex", "q": q, "generation": generation})
    return render_template("pokedex/index.html", pagination=pagination, q=q, generation=generation)


@bp.route("/<int:species_id>")
def detail(species_id: int):
    species = db.session.get(Species, species_id)
    if not species:
        abort(404)

    # Cadeia evolutiva: pares que envolvem qualquer form desta espécie
    form_ids = [f.id for f in species.forms]
    evolutions = db.session.query(EvolutionChain).filter(
        db.or_(
            EvolutionChain.from_form_id.in_(form_ids),
            EvolutionChain.to_form_id.in_(form_ids),
        )
    ).all()

    log_event("POKEMON_VIEW", {"species_id": species_id})
    return render_template("pokedex/detail.html", species=species, evolutions=evolutions)
