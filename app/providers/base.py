from abc import ABC, abstractmethod


class PokemonDataProvider(ABC):
    """Interface obrigatória para todo provider de dados Pokémon (RF03)."""

    @abstractmethod
    def get_pokemon_list(self, limit: int = 151, offset: int = 0) -> list[dict]:
        """Retorna lista resumida de Pokémon."""

    @abstractmethod
    def get_pokemon(self, pokemon_id: int | str) -> dict:
        """Retorna dados completos de um Pokémon por ID ou nome."""

    @abstractmethod
    def get_evolution_chain(self, chain_id: int) -> dict:
        """Retorna cadeia evolutiva completa."""
