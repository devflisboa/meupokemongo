from flask import render_template, request
from flask_login import login_required, current_user
from sqlalchemy import or_

from . import bp
from ...extensions import db
from ...models.pokemon import Species, Form
from ...models.collection import UserCollection
from ...data.pvp_meta import LEAGUES, TIER_ORDER, TIER_COLOR, LEAGUE_COLORS


def _enrich_meta(meta: list[dict], user_id: int | None) -> list[dict]:
    """
    Adiciona ao dicionário de cada Pokémon do meta:
    - sprite_url : URL da miniatura WebP via /img/t/<id>.webp
    - owned      : bool — o usuário tem este Pokémon (se logado)
    - has_perfect: bool — tem exemplar 100% IV
    """
    names = [e["name"] for e in meta]
    forms = (
        db.session.query(Form)
        .filter(or_(*[Form.pokemon_name == n for n in names]))
        .filter(Form.form_name == "normal")
        .all()
    ) if names else []

    form_by_name = {f.pokemon_name: f for f in forms}

    owned_form_ids: set[int] = set()
    perfect_form_ids: set[int] = set()
    if user_id:
        form_ids = [f.id for f in forms]
        if form_ids:
            rows = db.session.query(
                UserCollection.form_id,
                UserCollection.owned,
                UserCollection.has_perfect,
            ).filter(
                UserCollection.user_id == user_id,
                UserCollection.form_id.in_(form_ids),
                UserCollection.owned.is_(True),
            ).all()
            for fid, owned, perfect in rows:
                if owned:
                    owned_form_ids.add(fid)
                if perfect:
                    perfect_form_ids.add(fid)

    enriched = []
    for entry in meta:
        form = form_by_name.get(entry["name"])
        pid = form.species_id if form else entry.get("_species_id_real") or entry["species_id"]
        sprite_url = f"/img/t/{pid}.webp"
        fid = form.id if form else None
        enriched.append({
            **entry,
            "sprite_url": sprite_url,
            "pokemon_id": pid,
            "owned": fid in owned_form_ids if fid else False,
            "has_perfect": fid in perfect_form_ids if fid else False,
            "tier_color": TIER_COLOR.get(entry["tier"], "bg-gray-400 text-white"),
        })

    enriched.sort(key=lambda e: TIER_ORDER.get(e["tier"], 9))
    return enriched


@bp.route("/")
@bp.route("/guia")
def guia():
    league_key = request.args.get("liga", "great")
    if league_key not in LEAGUES:
        league_key = "great"

    user_id = current_user.id if current_user.is_authenticated else None

    leagues_enriched = {}
    for key, data in LEAGUES.items():
        leagues_enriched[key] = {
            **data,
            "meta": _enrich_meta(data["meta"], user_id),
            "colors": LEAGUE_COLORS[key],
        }

    active = leagues_enriched[league_key]
    return render_template(
        "pvp/guia.html",
        leagues=leagues_enriched,
        active_key=league_key,
        active=active,
    )
