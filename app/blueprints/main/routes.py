from flask import render_template
from flask_login import current_user
from . import bp
from ...services.collection_service import get_collection_stats, get_missing_pokemon, get_pending_evolutions
from ...services.matching_service import get_active_matches_for_user
from ...services.analytics_service import log_event
from ...extensions import db
from ...models.user import User
from ...models.pokemon import Species, Form
from ...models.collection import UserCollection


@bp.route("/")
def index():
    log_event("PAGE_VIEW", {"page": "home"})

    stats = None
    missing = []
    pending_evolutions = []
    matches = []
    owned_species_ids = set()

    if current_user.is_authenticated:
        stats = get_collection_stats(current_user.id)
        missing = get_missing_pokemon(current_user.id)[:5]
        pending_evolutions = get_pending_evolutions(current_user.id)[:3]
        matches = get_active_matches_for_user(current_user.id)[:4]

        owned_form_rows = db.session.query(UserCollection.form_id).filter(
            UserCollection.user_id == current_user.id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        ).all()
        if owned_form_rows:
            owned_form_ids = {r[0] for r in owned_form_rows}
            owned_species_ids = {
                r[0]
                for r in db.session.query(Form.species_id)
                .filter(Form.id.in_(owned_form_ids))
                .all()
            }

    total_trainers = db.session.query(User).count()
    featured_ids = [1, 4, 7, 25, 94, 133]
    featured_species = (
        db.session.query(Species)
        .filter(Species.id.in_(featured_ids))
        .order_by(Species.id)
        .all()
    )
    if len(featured_species) < 6:
        extra = (
            db.session.query(Species)
            .filter(Species.id.notin_([s.id for s in featured_species]))
            .order_by(Species.id)
            .limit(6 - len(featured_species))
            .all()
        )
        featured_species = featured_species + extra

    return render_template(
        "main/index.html",
        stats=stats,
        missing=missing,
        pending_evolutions=pending_evolutions,
        matches=matches,
        total_trainers=total_trainers,
        featured_species=featured_species,
        owned_species_ids=owned_species_ids,
    )
