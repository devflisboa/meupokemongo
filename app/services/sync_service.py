"""
Sincronização de dados da PokeAPI → MySQL.
Popula: species, forms, evolution_chains, pokemon_cache.
"""
import time
import requests

from ..extensions import db
from ..models.pokemon import Species, Form, EvolutionChain, PokemonCache

POKEAPI = "https://pokeapi.co/api/v2"
DELAY = 0.15  # segundos entre requests (respeito à PokeAPI pública)

GENERATION_MAP = {
    "generation-i": 1, "generation-ii": 2, "generation-iii": 3,
    "generation-iv": 4, "generation-v": 5, "generation-vi": 6,
    "generation-vii": 7, "generation-viii": 8, "generation-ix": 9,
}


def _get(url: str) -> dict:
    resp = requests.get(url, timeout=15)
    resp.raise_for_status()
    return resp.json()


def _sprite_url(species_id: int) -> str:
    return (
        f"https://raw.githubusercontent.com/PokeAPI/sprites/master"
        f"/sprites/pokemon/other/official-artwork/{species_id}.png"
    )


def _pt_name(names: list) -> str | None:
    for n in names:
        if n["language"]["name"] in ("pt-BR", "pt"):
            return n["name"]
    return None


def _chain_id_from_url(url: str) -> int:
    return int(url.rstrip("/").split("/")[-1])


def _walk_chain(node: dict) -> list[tuple[int, int]]:
    """Retorna lista de (from_species_id, to_species_id) percorrendo a árvore."""
    pairs = []
    from_url = node["species"]["url"]
    from_id = int(from_url.rstrip("/").split("/")[-1])
    for child in node.get("evolves_to", []):
        to_url = child["species"]["url"]
        to_id = int(to_url.rstrip("/").split("/")[-1])
        pairs.append((from_id, to_id))
        pairs.extend(_walk_chain(child))
    return pairs


def sync_pokemon(limit: int = 151, offset: int = 0, log=print) -> dict:
    """
    Sincroniza `limit` Pokémon a partir de `offset`.
    Retorna relatório: {"species": N, "forms": N, "evolutions": N, "errors": [...]}
    """
    report = {"species": 0, "forms": 0, "evolutions": 0, "errors": []}
    evolution_chain_ids: set[int] = set()

    log(f"[sync] Buscando lista de {limit} Pokémon (offset={offset})...")
    try:
        data = _get(f"{POKEAPI}/pokemon-species?limit={limit}&offset={offset}")
    except Exception as e:
        report["errors"].append(f"Falha ao buscar lista: {e}")
        return report

    results = data.get("results", [])
    total = len(results)
    log(f"[sync] {total} espécies encontradas. Iniciando sincronização...\n")

    for i, item in enumerate(results, start=1):
        species_url = item["url"]
        species_id = int(species_url.rstrip("/").split("/")[-1])
        name_en = item["name"]

        try:
            # 1 — dados da espécie (nome PT, geração, lendário, cadeia)
            sp_data = _get(species_url)
            time.sleep(DELAY)

            name_pt = _pt_name(sp_data.get("names", []))
            generation = GENERATION_MAP.get(sp_data["generation"]["name"], 0)
            is_legendary = sp_data.get("is_legendary", False)
            is_mythical = sp_data.get("is_mythical", False)
            chain_url = sp_data.get("evolution_chain", {}).get("url", "")
            if chain_url:
                evolution_chain_ids.add(_chain_id_from_url(chain_url))

            # 2 — dados do Pokémon principal (tipos)
            pk_data = _get(f"{POKEAPI}/pokemon/{species_id}")
            time.sleep(DELAY)

            types = [t["type"]["name"] for t in pk_data.get("types", [])]
            type1 = types[0] if len(types) > 0 else None
            type2 = types[1] if len(types) > 1 else None

            # 3 — gravar/atualizar Species
            species = db.session.get(Species, species_id)
            if not species:
                species = Species(id=species_id)
                db.session.add(species)
            species.name = name_en
            species.name_pt = name_pt
            species.generation = generation
            species.is_legendary = is_legendary
            species.is_mythical = is_mythical

            # 4 — gravar/atualizar Form principal (normal)
            form = db.session.query(Form).filter_by(
                species_id=species_id, form_name="normal"
            ).first()
            if not form:
                form = Form(species_id=species_id, form_name="normal")
                db.session.add(form)
            form.type1 = type1
            form.type2 = type2
            form.sprite_url = _sprite_url(species_id)
            shiny_artwork = (
                pk_data.get("sprites", {})
                .get("other", {})
                .get("official-artwork", {})
                .get("front_shiny")
            )
            form.is_shiny_available = bool(shiny_artwork)

            db.session.commit()
            report["species"] += 1
            report["forms"] += 1

            pct = round(i / total * 100)
            bar = "█" * (pct // 5) + "░" * (20 - pct // 5)
            log(f"[{bar}] {pct:3d}%  #{species_id:03d} {name_en}")

        except Exception as e:
            db.session.rollback()
            msg = f"Erro em species #{species_id} ({name_en}): {e}"
            report["errors"].append(msg)
            log(f"\n[ERRO] {msg}")
            continue

    log(f"\n\n[sync] Espécies: {report['species']} | Formas: {report['forms']}")
    log(f"[sync] Sincronizando {len(evolution_chain_ids)} cadeias evolutivas...")

    for chain_id in sorted(evolution_chain_ids):
        try:
            chain_data = _get(f"{POKEAPI}/evolution-chain/{chain_id}")
            time.sleep(DELAY)

            pairs = _walk_chain(chain_data["chain"])
            for from_species_id, to_species_id in pairs:
                from_form = db.session.query(Form).filter_by(
                    species_id=from_species_id, form_name="normal"
                ).first()
                to_form = db.session.query(Form).filter_by(
                    species_id=to_species_id, form_name="normal"
                ).first()
                if not from_form or not to_form:
                    continue

                existing = db.session.query(EvolutionChain).filter_by(
                    from_form_id=from_form.id, to_form_id=to_form.id
                ).first()
                if not existing:
                    db.session.add(EvolutionChain(
                        from_form_id=from_form.id,
                        to_form_id=to_form.id,
                    ))
                    report["evolutions"] += 1

            db.session.commit()
            log(f"  cadeia #{chain_id} → {len(pairs)} par(es)")

        except Exception as e:
            db.session.rollback()
            msg = f"Erro na cadeia #{chain_id}: {e}"
            report["errors"].append(msg)
            log(f"[ERRO] {msg}")

    log(f"\n[sync] Concluído! Espécies={report['species']} Formas={report['forms']} Evoluções={report['evolutions']} Erros={len(report['errors'])}")

    # Custos de doces do GO (pogoapi) — falha aqui não invalida o sync principal
    try:
        from .candy_service import sync_candy_costs
        sync_candy_costs(log=log)
    except Exception as e:
        report["errors"].append(f"Doces (pogoapi): {e}")
        log(f"[ERRO] Doces (pogoapi): {e}")
    return report
