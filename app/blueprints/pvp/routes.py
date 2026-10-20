from flask import render_template, request, jsonify
from flask_login import current_user
from . import bp
from ...extensions import db
from ...models.pokemon import Form
from ...models.collection import UserCollection
from ...data.pvp_meta import LEAGUES, TIER_ORDER, TIER_COLOR, LEAGUE_COLORS
from ...services.pvp_service import rank_of


def _form_name_from_slug(pokemon_name: str) -> str:
    """Converte slug pvp_meta → form_name armazenado no banco."""
    FORM_SUFFIXES = {"galarian", "alolan", "hisuian", "paldean",
                     "altered", "origin", "sky", "therian", "incarnate"}
    parts = pokemon_name.split("-")
    if len(parts) > 1 and parts[-1] in FORM_SUFFIXES:
        return parts[-1]
    return "normal"


def _enrich_meta(meta: list[dict], user_id: int | None) -> list[dict]:
    """
    Adiciona ao dicionário de cada Pokémon do meta:
    - sprite_url : URL da miniatura WebP via /img/t/<id>.webp
    - owned      : bool — o usuário tem este Pokémon (se logado)
    - has_perfect: bool — tem exemplar 100% IV
    """
    species_ids = [e.get("_species_id_real") or e["species_id"] for e in meta]

    all_forms = (
        db.session.query(Form)
        .filter(Form.species_id.in_(set(species_ids)))
        .all()
    ) if species_ids else []

    # {species_id: {form_name: Form}}
    forms_by_species: dict[int, dict[str, Form]] = {}
    for f in all_forms:
        forms_by_species.setdefault(f.species_id, {})[f.form_name] = f

    owned_form_ids: set[int] = set()
    perfect_form_ids: set[int] = set()
    if user_id and all_forms:
        form_ids = [f.id for f in all_forms]
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
        sid = entry.get("_species_id_real") or entry["species_id"]
        expected_fn = _form_name_from_slug(entry["name"])
        species_forms = forms_by_species.get(sid, {})
        form = species_forms.get(expected_fn) or species_forms.get("normal")

        pid = sid
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


@bp.route("/calculadora")
def calculadora():
    """Calculadora de Rank PVP: seleciona Pokémon + IVs → rank por liga."""
    # Lista de Pokémon com base stats para o seletor
    all_pokemon: list[dict] = []
    seen_ids: set[int] = set()
    for league_data in LEAGUES.values():
        for entry in league_data["meta"]:
            sid = entry["species_id"]
            if sid not in seen_ids and entry.get("base_atk"):
                seen_ids.add(sid)
                all_pokemon.append({
                    "species_id": sid,
                    "name": entry["name"],
                    "name_pt": entry["name_pt"],
                    "base_atk": entry["base_atk"],
                    "base_def": entry["base_def"],
                    "base_sta": entry["base_sta"],
                    "sprite_url": f"/img/t/{sid}.webp",
                })

    all_pokemon.sort(key=lambda x: x["name_pt"])
    return render_template("pvp/calculadora.html", pokemon_list=all_pokemon, leagues=LEAGUES)


@bp.route("/api/rank")
def api_rank():
    """
    GET /pvp/api/rank?species_id=260&iv_atk=0&iv_def=15&iv_sta=14
    Retorna rank nas ligas que o Pokémon participa.
    """
    try:
        sid = int(request.args.get("species_id", 0))
        iv_atk = int(request.args.get("iv_atk", 0))
        iv_def = int(request.args.get("iv_def", 15))
        iv_sta = int(request.args.get("iv_sta", 14))
    except (TypeError, ValueError):
        return jsonify({"error": "parâmetros inválidos"}), 400

    # Localiza o Pokémon no meta
    entry = None
    for league_data in LEAGUES.values():
        for e in league_data["meta"]:
            if e["species_id"] == sid and e.get("base_atk"):
                entry = e
                break
        if entry:
            break

    if not entry:
        return jsonify({"error": "Pokémon não encontrado"}), 404

    results = {}
    for league_key, league_data in LEAGUES.items():
        if league_key not in entry.get("leagues", []):
            continue
        cp_limit = league_data["cp_limit"]
        r = rank_of(
            entry["base_atk"], entry["base_def"], entry["base_sta"],
            iv_atk, iv_def, iv_sta, cp_limit,
        )
        results[league_key] = {
            "name": league_data["name"],
            "cp_limit": cp_limit,
            **r,
        }

    return jsonify({
        "name_pt": entry["name_pt"],
        "iv_atk": iv_atk, "iv_def": iv_def, "iv_sta": iv_sta,
        "results": results,
    })
