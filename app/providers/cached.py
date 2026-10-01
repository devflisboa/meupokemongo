import json
from datetime import datetime, timedelta
from .base import PokemonDataProvider
from ..extensions import db
from ..models.pokemon import PokemonCache

CACHE_TTL_HOURS = 24


class CachedProvider(PokemonDataProvider):
    """
    Wrapper sobre qualquer PokemonDataProvider que persiste no MySQL.
    Se o provider externo falhar, retorna o cache local (RB12).
    """

    def __init__(self, upstream: PokemonDataProvider):
        self._upstream = upstream

    def _get_cache(self, key: str) -> dict | None:
        entry = db.session.get(PokemonCache, key)
        if not entry:
            return None
        if datetime.utcnow() - entry.cached_at > timedelta(hours=CACHE_TTL_HOURS):
            return None
        return entry.payload

    def _set_cache(self, key: str, payload: dict) -> None:
        entry = db.session.get(PokemonCache, key)
        if entry:
            entry.payload = payload
            entry.cached_at = datetime.utcnow()
        else:
            db.session.add(PokemonCache(cache_key=key, payload=payload))
        db.session.commit()

    def _fetch_with_fallback(self, key: str, fetch_fn):
        cached = self._get_cache(key)
        if cached:
            return cached
        try:
            data = fetch_fn()
            self._set_cache(key, data)
            return data
        except Exception:
            stale = db.session.get(PokemonCache, key)
            if stale:
                return stale.payload
            raise

    def get_pokemon_list(self, limit: int = 151, offset: int = 0) -> list[dict]:
        key = f"list:{limit}:{offset}"
        return self._fetch_with_fallback(key, lambda: self._upstream.get_pokemon_list(limit, offset))

    def get_pokemon(self, pokemon_id: int | str) -> dict:
        key = f"pokemon:{pokemon_id}"
        return self._fetch_with_fallback(key, lambda: self._upstream.get_pokemon(pokemon_id))

    def get_evolution_chain(self, chain_id: int) -> dict:
        key = f"evolution:{chain_id}"
        return self._fetch_with_fallback(key, lambda: self._upstream.get_evolution_chain(chain_id))
