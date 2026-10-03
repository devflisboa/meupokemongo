"""#14 — formas regionais + exclusivos de região."""
import pytest

from app.extensions import db as _db
from app.models.user import User
from app.models.pokemon import Species, Form, EvolutionChain
from app.models.collection import UserCollection
from app.models.individual import UserPokemon
from app.models.wishlist import Wishlist
from app.models.trade import TradeMatch, WhatsappClick
from app.data.regional import (
    form_label, form_category, form_display_name, variety_category, trade_only_in_brazil, exclusive_info,
)
from app.services import sync_service
from app.services.collection_service import get_collection_stats
from app.services.matching_service import run_matching_for_user


@pytest.mark.parametrize("name,label,category", [
    ("normal", "", None), ("alola", "Alola", "regional"), ("galar-standard", "Galar", "regional"),
    ("paldea-combat-breed", "Paldea (Combate)", "regional"), ("hisui", "Hisui", "regional"),
    ("mega", "Mega", "mega"), ("mega-x", "Mega X", "mega"),
    ("gmax", "Gigantamax", "gmax"), ("amped-gmax", "Gigantamax (Amped)", "gmax"),
    ("original-cap", "Boné Original", "especial"), ("alola-cap", "Boné de Alola", "especial"),
    ("totem-alola", "Totem (Alola)", "especial"), ("totem-disguised", "Totem (Disfarçado)", "especial"),
    ("galar-zen", "Galar (Zen)", "especial"), ("zen", "Zen", "especial"),
])
def test_form_label_and_category(name, label, category):
    assert form_label(name) == label
    assert form_category(name) == category


@pytest.mark.parametrize("species,form_name,expected", [
    ("Rattata", "alola", "Rattata de Alola"),
    ("Darmanitan", "galar-zen", "Darmanitan de Galar (Zen)"),
    ("Charizard", "mega-x", "Mega Charizard X"),
    ("Venusaur", "mega", "Mega Venusaur"),
    ("Charizard", "gmax", "Charizard Gigantamax"),
    ("Pikachu", "original-cap", "Pikachu Boné Original"),
    ("Raticate", "totem-alola", "Raticate Totem (Alola)"),
])
def test_form_display_name(species, form_name, expected):
    assert form_display_name(species, form_name) == expected


@pytest.mark.parametrize("variety,category", [
    ("charizard-mega-x", "mega"), ("meganium-mega", "mega"), ("charizard-gmax", "gmax"),
    ("toxtricity-low-key-gmax", "gmax"), ("pikachu-world-cap", "especial"), ("kommo-o-totem", "especial"),
    ("darmanitan-zen", "especial"), ("rattata-alola", "regional"), ("tauros-paldea-aqua-breed", "regional"),
    ("zamazenta-crowned", None), ("deoxys-attack", None), ("meganium", None),
])
def test_variety_category(variety, category):
    assert variety_category(variety) == category


def test_exclusives():
    assert trade_only_in_brazil(122)       # Mr. Mime — Europa
    assert not trade_only_in_brazil(214)   # Heracross aparece no Brasil
    assert not trade_only_in_brazil(25)    # Pikachu não é exclusivo
    assert exclusive_info(214) == ("América Latina", True)


@pytest.fixture()
def dex(app):
    with app.app_context():
        for model in (WhatsappClick, TradeMatch, UserPokemon, Wishlist, UserCollection,
                      EvolutionChain, Form, Species, User):
            _db.session.query(model).delete()
        _db.session.add_all([
            Species(id=37, name="vulpix", name_pt="Vulpix", generation=1),
            Species(id=122, name="mr-mime", name_pt="Mr. Mime", generation=1),
            Species(id=128, name="tauros", name_pt="Tauros", generation=1),
        ])
        _db.session.flush()
        forms = {
            "vulpix": Form(species_id=37, form_name="normal", type1="fire"),
            "vulpix-alola": Form(species_id=37, form_name="alola", type1="ice"),
            "mime": Form(species_id=122, form_name="normal", type1="psychic"),
            "tauros": Form(species_id=128, form_name="normal", type1="normal"),
        }
        _db.session.add_all(forms.values())
        ash = User(username="ash", email="ash@x.test", state="CE", city="Fortaleza")
        misty = User(username="misty", email="misty@x.test", state="CE", city="Fortaleza")
        for u in (ash, misty):
            u.set_password("x")
        _db.session.add_all([ash, misty])
        _db.session.flush()
        _db.session.add(UserCollection(user_id=ash.id, form_id=forms["vulpix"].id, owned=True, quantity=1))
        _db.session.add(UserCollection(user_id=misty.id, form_id=forms["vulpix-alola"].id,
                                       owned=True, quantity=1, for_trade=True))
        _db.session.commit()
        yield {"ash": ash.id, "misty": misty.id, "f": {k: v.id for k, v in forms.items()}}
        _db.session.rollback()


def _login(client, uid):
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_sync_regional_forms(dex, monkeypatch):
    fake = {
        "/pokemon?limit=2000&offset=1025": {"results": [
            {"name": "vulpix-alola"}, {"name": "tauros-paldea-aqua-breed"},
            {"name": "deoxys-attack"},  # fora das categorias → ignorado
        ]},
        "/pokemon/vulpix-alola": {"id": 10103, "species": {"name": "vulpix", "url": "https://x/pokemon-species/37/"},
                                  "types": [{"type": {"name": "ice"}}], "sprites": {}},
        "/pokemon/tauros-paldea-aqua-breed": {"id": 10252, "species": {"name": "tauros", "url": "https://x/pokemon-species/128/"},
                                              "types": [{"type": {"name": "fighting"}}, {"type": {"name": "water"}}], "sprites": {}},
    }
    monkeypatch.setattr(sync_service, "_get", lambda url: fake[url.replace(sync_service.POKEAPI, "")])
    monkeypatch.setattr(sync_service.time, "sleep", lambda s: None)

    report = sync_service.sync_regional_forms(log=lambda *_: None)
    assert report["forms"] == 2 and not report["errors"]
    assert report["by_category"] == {"regional": 2}
    tauros = _db.session.query(Form).filter_by(species_id=128, form_name="paldea-aqua-breed").one()
    assert (tauros.type1, tauros.type2, tauros.label) == ("fighting", "water", "Paldea (Aquática)")
    assert tauros.sprite_url.endswith("/10252.png")
    assert tauros.display_name == "Tauros de Paldea (Aquática)"


def test_wishlist_regional_toggle_and_exclusive(client, dex):
    _login(client, dex["ash"])
    html = client.get("/wishlist/").get_data(as_text=True)
    assert "de Alola" not in html                                 # padrão: só formas normais
    assert 'data-category="regional"' in html                     # mas oferece o liga/desliga
    assert "🌍 Europa" in html and "🌍 América do Norte" in html   # Mr. Mime e Tauros
    # exclusivos sobem para o topo da Alta
    first_cards = [c for c in html.split('class="wish-card')[1:3]]
    assert all('data-exclusive="true"' in c for c in first_cards)

    html = client.get("/wishlist/?formas=1").get_data(as_text=True)
    assert "de Alola" in html


def test_matching_includes_regional_offers(dex):
    assert run_matching_for_user(dex["ash"]) == 1
    m = _db.session.query(TradeMatch).filter_by(wisher_id=dex["ash"]).one()
    assert m.form.display_name == "Vulpix de Alola"


def test_stats_ignore_regional_forms(dex):
    _db.session.add(UserCollection(user_id=dex["ash"], form_id=dex["f"]["vulpix-alola"], owned=True, quantity=1))
    _db.session.commit()
    stats = get_collection_stats(dex["ash"])
    assert stats["owned"] == 1 and stats["total"] == 3   # Vulpix normal; Alola não infla


def test_api_lists_regional_forms_with_status(client, dex):
    _login(client, dex["ash"])
    data = client.get("/pokedex/api/37").get_json()
    assert [(f["label"], f["owned"]) for f in data["regional_forms"]] == [("Alola", False)]
    assert data["exclusive"] is None
    assert client.get("/pokedex/api/122").get_json()["exclusive"] == {"where": "Europa", "in_brazil": False}
    # marcar a forma regional pelo upsert do modal
    r = client.post("/collection/upsert", data={"form_id": dex["f"]["vulpix-alola"], "owned": "true", "quantity": "1",
                                                "for_trade": "false", "has_shiny": "false"}).get_json()
    assert r["owned"]
    assert client.get("/pokedex/api/37").get_json()["regional_forms"][0]["owned"] is True


def _add_form(species_id, form_name):
    f = Form(species_id=species_id, form_name=form_name, type1="fire")
    _db.session.add(f)
    _db.session.commit()
    return f.id


def test_mega_never_for_trade_nor_matched(client, dex):
    mega = _add_form(37, "mega")  # forma fictícia só para o teste
    _db.session.add(UserCollection(user_id=dex["misty"], form_id=mega, owned=True, quantity=1, for_trade=True))
    _db.session.commit()
    assert run_matching_for_user(dex["ash"]) == 1          # só a Vulpix de Alola, não a Mega
    _login(client, dex["misty"])
    r = client.post("/collection/upsert", data={"form_id": mega, "owned": "true", "quantity": "1",
                                                "for_trade": "true", "has_shiny": "false"}).get_json()
    assert r["for_trade"] is False                          # servidor recusa Mega para troca


def test_wishlist_categories(client, dex):
    _add_form(37, "mega")
    _add_form(37, "gmax")
    _login(client, dex["ash"])

    def grid(url):
        html = client.get(url).get_data(as_text=True)
        return html.split('id="wish-grid"')[1].split('id="wish-empty"')[0]

    g = grid("/wishlist/?formas=mega")
    assert "Mega" in g and "de Alola" not in g and "Gigantamax" not in g
    g = grid("/wishlist/?formas=regional,gmax")
    assert "de Alola" in g and "Gigantamax" in g and ">\n        Mega\n" not in g
    assert "de Alola" in grid("/wishlist/?formas=1")  # link antigo continua valendo


def test_binder_wanted_lists_all_missing_in_priority_order(client, dex):
    import json, re
    html = client.get("/trade/ash").get_data(as_text=True)
    wanted = json.loads(re.search(r"const WANTED = (\[.*?\]);", html, re.S).group(1))
    # ash não tem Mr. Mime e Tauros (exclusivos, ambos Alta) — todos os faltantes, sem botão para outra rota
    assert [w["id"] for w in wanted] == [122, 128]
    assert all(w["x"] for w in wanted)
    assert "Ver todos os faltantes" not in html