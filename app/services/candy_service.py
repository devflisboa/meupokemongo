"""
Custo de doces para evoluir no Pokémon GO.

A PokeAPI não tem os custos do GO; a fonte é a pogoapi.net
(/api/v1/pokemon_evolutions.json): lista de {pokemon_id, form, evolutions:[{pokemon_id, form, candy_required}]}.
Só usamos form "Normal", que é o que existe na tabela forms.
"""
import requests

from ..extensions import db
from ..models.pokemon import EvolutionChain, Form

POGOAPI_EVOLUTIONS = "https://pogoapi.net/api/v1/pokemon_evolutions.json"


def fetch_candy_costs(timeout: int = 30) -> dict[tuple[int, int], int]:
    """Retorna {(species_origem, species_destino): doces}."""
    resp = requests.get(POGOAPI_EVOLUTIONS, timeout=timeout)
    resp.raise_for_status()
    costs: dict[tuple[int, int], int] = {}
    for item in resp.json():
        if item.get("form", "Normal") != "Normal":
            continue
        for evo in item.get("evolutions", []):
            if evo.get("form", "Normal") != "Normal" or evo.get("candy_required") is None:
                continue
            costs[(item["pokemon_id"], evo["pokemon_id"])] = int(evo["candy_required"])
    return costs


def sync_candy_costs(costs: dict[tuple[int, int], int] | None = None, log=print) -> dict:
    """Preenche EvolutionChain.candy_cost. Retorna {updated, missing}."""
    if costs is None:
        costs = fetch_candy_costs()

    species_of = dict(db.session.query(Form.id, Form.species_id).all())
    updated, missing = 0, 0
    for chain in db.session.query(EvolutionChain).all():
        key = (species_of.get(chain.from_form_id), species_of.get(chain.to_form_id))
        cost = costs.get(key)
        if cost is None:
            missing += 1
            continue
        if chain.candy_cost != cost:
            chain.candy_cost = cost
            updated += 1
    db.session.commit()
    log(f"Doces: {updated} evoluções atualizadas, {missing} sem custo na pogoapi")
    return {"updated": updated, "missing": missing}
