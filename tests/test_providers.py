from unittest.mock import MagicMock, patch
from app.providers.pokeapi import PokeApiProvider


def test_get_pokemon_returns_dict():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"id": 1, "name": "bulbasaur"}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.providers.pokeapi.requests.get", return_value=mock_resp):
        provider = PokeApiProvider()
        result = provider.get_pokemon(1)
        assert result["name"] == "bulbasaur"


def test_get_pokemon_list_returns_results():
    mock_resp = MagicMock()
    mock_resp.json.return_value = {"results": [{"name": "bulbasaur"}, {"name": "ivysaur"}]}
    mock_resp.raise_for_status = MagicMock()

    with patch("app.providers.pokeapi.requests.get", return_value=mock_resp):
        provider = PokeApiProvider()
        result = provider.get_pokemon_list(limit=2)
        assert len(result) == 2
