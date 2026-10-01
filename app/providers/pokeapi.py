import requests
from .base import PokemonDataProvider

POKEAPI_BASE = "https://pokeapi.co/api/v2"
TIMEOUT = 10


class PokeApiProvider(PokemonDataProvider):
    """Busca dados diretamente na PokeAPI v2."""

    def get_pokemon_list(self, limit: int = 151, offset: int = 0) -> list[dict]:
        resp = requests.get(f"{POKEAPI_BASE}/pokemon", params={"limit": limit, "offset": offset}, timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json().get("results", [])

    def get_pokemon(self, pokemon_id: int | str) -> dict:
        resp = requests.get(f"{POKEAPI_BASE}/pokemon/{pokemon_id}", timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()

    def get_evolution_chain(self, chain_id: int) -> dict:
        resp = requests.get(f"{POKEAPI_BASE}/evolution-chain/{chain_id}", timeout=TIMEOUT)
        resp.raise_for_status()
        return resp.json()
