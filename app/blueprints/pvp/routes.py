import json
import math
from flask import render_template, request, jsonify
from flask_login import current_user, login_required
from sqlalchemy import and_

from . import bp
from ...extensions import db
from ...models.pokemon import Form
from ...models.collection import UserCollection
from ...models.individual import UserPokemon
from ...data.pvp_meta import LEAGUES, TIER_ORDER, TIER_COLOR, LEAGUE_COLORS
from ...services.pvp_service import rank_of, best_level_for_cp_limit, LEVEL_CPM
from ...data.pvp_moves import FAST_MOVES, CHARGED_MOVES, simulate_battle


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
            sid = _real_sid(entry)
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
            if _real_sid(e) == sid and e.get("base_atk"):
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


# ── helpers ───────────────────────────────────────────────────────────────────

def _real_sid(entry: dict) -> int:
    return entry.get("_species_id_real") or entry["species_id"]


def _species_to_meta() -> dict[int, list[tuple[str, dict]]]:
    """Monta mapa species_id → [(league_key, entry)] para todos os meta válidos."""
    result: dict[int, list] = {}
    for lk, ld in LEAGUES.items():
        for e in ld["meta"]:
            sid = _real_sid(e)
            if not e.get("base_atk") or sid == 9999:
                continue
            for lg in e.get("leagues", []):
                if lg == lk:
                    result.setdefault(sid, []).append((lk, e))
    return result


# ── Nível 3 — Minha Coleção PVP ──────────────────────────────────────────────

@bp.route("/minha-colecao")
@login_required
def minha_colecao():
    s2m = _species_to_meta()
    meta_sids = set(s2m.keys())

    pairs = (
        db.session.query(UserPokemon, Form)
        .join(Form, UserPokemon.form_id == Form.id)
        .filter(
            UserPokemon.user_id == current_user.id,
            Form.species_id.in_(meta_sids),
        )
        .order_by(UserPokemon.cp.desc())
        .all()
    )

    results_by_league: dict[str, list] = {k: [] for k in LEAGUES}

    for poke, form in pairs:
        sid = form.species_id
        for league_key, entry in s2m.get(sid, []):
            row = {
                "poke_id": poke.id,
                "nickname": poke.nickname,
                "name_pt": entry["name_pt"],
                "sprite_url": f"/img/t/{sid}.webp",
                "tier": entry["tier"],
                "tier_color": TIER_COLOR.get(entry["tier"], "bg-gray-400 text-white"),
                "cp": poke.cp,
                "iv_atk": poke.atk_iv,
                "iv_def": poke.def_iv,
                "iv_sta": poke.sta_iv,
                "iv_pct": poke.iv_pct,
                "quick_move": poke.quick_move or "",
                "charge_move": poke.charge_move or "",
                "charge_move2": poke.charge_move2 or "",
                "meta_fast": entry["fast"],
                "meta_charged": entry["charged"],
                "legacy": entry.get("legacy", []),
                "has_meta_fast": (poke.quick_move or "") == entry["fast"],
                "has_meta_charged": bool(
                    {poke.charge_move, poke.charge_move2} & set(entry["charged"])
                ),
                "rank": None, "sp_pct": None, "pvp_level": None, "pvp_cp": None,
            }
            if poke.atk_iv is not None and poke.def_iv is not None and poke.sta_iv is not None:
                r = rank_of(
                    entry["base_atk"], entry["base_def"], entry["base_sta"],
                    poke.atk_iv, poke.def_iv, poke.sta_iv,
                    LEAGUES[league_key]["cp_limit"],
                )
                row.update({"rank": r.get("rank"), "sp_pct": r.get("sp_pct"),
                             "pvp_level": r.get("level"), "pvp_cp": r.get("cp")})
            results_by_league[league_key].append(row)

    for k in results_by_league:
        results_by_league[k].sort(key=lambda x: x.get("rank") or 9999)

    return render_template("pvp/minha_colecao.html",
                           results_by_league=results_by_league, leagues=LEAGUES)


# ── Nível 4 — Time Builder ────────────────────────────────────────────────────

@bp.route("/time-builder")
def time_builder():
    meta_by_league: dict[str, dict] = {}
    for lk, ld in LEAGUES.items():
        entries = []
        for e in ld["meta"]:
            sid = _real_sid(e)
            entries.append({
                "species_id": sid,
                "name_pt": e["name_pt"],
                "types": e["types"],
                "tier": e["tier"],
                "fast": e["fast"],
                "charged": e["charged"],
                "legacy": e.get("legacy", []),
                "sprite_url": f"/img/t/{sid}.webp",
            })
        meta_by_league[lk] = {
            "name": ld["name"], "icon": ld["icon"], "cp_limit": ld["cp_limit"],
            "meta": entries,
        }
    return render_template("pvp/time_builder.html",
                           meta_json=json.dumps(meta_by_league, ensure_ascii=False),
                           leagues=LEAGUES)


# ── Nível 5 — Simulador ───────────────────────────────────────────────────────

@bp.route("/simulador")
def simulador():
    all_meta: list[dict] = []
    seen: set[tuple] = set()
    for lk, ld in LEAGUES.items():
        for e in ld["meta"]:
            sid = _real_sid(e)
            key = (sid, lk)
            if key in seen or not e.get("base_atk"):
                continue
            seen.add(key)
            all_meta.append({
                "species_id": sid,
                "name_pt": e["name_pt"],
                "types": e["types"],
                "base_atk": e["base_atk"],
                "base_def": e["base_def"],
                "base_sta": e["base_sta"],
                "fast": e["fast"],
                "charged": e["charged"],
                "league_key": lk,
                "league_name": ld["name"],
                "sprite_url": f"/img/t/{sid}.webp",
            })
    all_meta.sort(key=lambda x: x["name_pt"])
    return render_template("pvp/simulador.html",
                           meta_json=json.dumps(all_meta, ensure_ascii=False),
                           fast_moves=sorted(FAST_MOVES.keys()),
                           charged_moves=sorted(CHARGED_MOVES.keys()),
                           leagues=LEAGUES)


@bp.route("/api/simular", methods=["POST"])
def api_simular():
    data = request.get_json(silent=True) or {}

    def build_pkm(key: str) -> dict | None:
        p = data.get(key, {})
        try:
            ba = int(p["base_atk"]); bd = int(p["base_def"]); bs = int(p["base_sta"])
            ia = int(p.get("iv_atk", 15)); id_ = int(p.get("iv_def", 15)); is_ = int(p.get("iv_sta", 15))
            cp_limit = int(p["cp_limit"]) if p.get("cp_limit") else None
        except (KeyError, TypeError, ValueError):
            return None
        lv   = best_level_for_cp_limit(ba, bd, bs, ia, id_, is_, cp_limit)
        cpm  = LEVEL_CPM[lv]
        return {
            "atk_eff": (ba + ia) * cpm,
            "def_eff": (bd + id_) * cpm,
            "hp_max":  max(10, int((bs + is_) * cpm)),
            "types":       p.get("types", ["normal"]),
            "fast_move":   p.get("fast_move", ""),
            "charged_move": p.get("charged_move", ""),
        }

    pkm_a = build_pkm("pkm_a")
    pkm_b = build_pkm("pkm_b")
    if not pkm_a or not pkm_b:
        return jsonify({"error": "dados inválidos"}), 400

    shields_a = max(0, min(2, int(data.get("shields_a", 2))))
    shields_b = max(0, min(2, int(data.get("shields_b", 2))))
    result = simulate_battle(pkm_a, pkm_b, shields_a, shields_b)
    return jsonify(result)


# ── API: sinal PVP para o Scan ────────────────────────────────────────────────

@bp.route("/api/scan-check")
def api_scan_check():
    try:
        sid = int(request.args.get("species_id", 0))
    except (TypeError, ValueError):
        return jsonify({"is_meta": False})

    iv_atk = request.args.get("iv_atk", type=int)
    iv_def = request.args.get("iv_def", type=int)
    iv_sta = request.args.get("iv_sta", type=int)

    matches = []
    seen_leagues: set[str] = set()
    for lk, ld in LEAGUES.items():
        for e in ld["meta"]:
            if _real_sid(e) != sid or lk not in e.get("leagues", []):
                continue
            if lk in seen_leagues:
                continue
            seen_leagues.add(lk)
            row: dict = {
                "league_key": lk, "league_name": ld["name"], "icon": ld["icon"],
                "tier": e["tier"], "fast": e["fast"], "charged": e["charged"],
                "legacy": e.get("legacy", []),
                "rank": None, "sp_pct": None, "level": None, "pvp_cp": None,
            }
            if (iv_atk is not None and iv_def is not None and iv_sta is not None
                    and e.get("base_atk")):
                r = rank_of(e["base_atk"], e["base_def"], e["base_sta"],
                            iv_atk, iv_def, iv_sta, ld["cp_limit"])
                row.update({"rank": r.get("rank"), "sp_pct": r.get("sp_pct"),
                            "level": r.get("level"), "pvp_cp": r.get("cp")})
            matches.append(row)

    return jsonify({"is_meta": bool(matches), "leagues": matches})
