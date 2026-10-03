"""Wishlist automática, flag 100% IV, exemplares individuais e import PokeGenie."""
import pytest

from app.extensions import db as _db
from app.models.user import User
from app.models.pokemon import Species, Form
from app.models.collection import UserCollection
from app.models.individual import UserPokemon
from app.models.wishlist import Wishlist
from app.models.trade import TradeMatch
from app.services import import_service
from app.services.matching_service import run_matching_for_user

POKEGENIE_CSV = (
    "Index,Name,Form,Pokemon Number,Gender,CP,HP,Atk IV,Def IV,Sta IV,IV Avg,Level Min,Level Max,"
    "Quick Move,Charge Move,Charge Move 2,Scan Date,Original Scan Date,Catch Date,Weight,Height,"
    "Lucky,Shadow/Purified,Favorite,Dust,Rank % (G),Rank # (G),Rank % (U),Rank % (L),Marked for Trade\n"
    "1,Bulbasaur,,9001,♂,1100,120,15,15,15,100,30,30,Vine Whip,Sludge Bomb,,1/10/26,1/10/26,1/9/26,"
    "6.9,0.7,1,0,1,4000,85.3,612,70.1,,0\n"
    "2,Bulbasaur,,9001,♀,900,100,10,12,5,60,25,25,Tackle,Power Whip,,1/10/26,1/10/26,1/9/26,"
    "7.1,0.71,0,1,0,4000,40,1200,30,,1\n"
)


@pytest.fixture()
def world(app):
    """Cria 2 espécies fictícias (ids altos para não colidir) e 2 treinadores."""
    with app.app_context():
        for model in (TradeMatch, UserPokemon, Wishlist, UserCollection, Form, Species, User):
            _db.session.query(model).delete()
        s1 = Species(id=9001, name="bulbasaur", name_pt="Bulbasaur", generation=1)
        s2 = Species(id=9002, name="ivysaur", name_pt="Ivysaur", generation=1)
        _db.session.add_all([s1, s2])
        _db.session.flush()
        f1 = Form(species_id=9001, form_name="normal", type1="grass", type2="poison")
        f2 = Form(species_id=9002, form_name="normal", type1="grass", type2="poison")
        u1 = User(username="ash", email="ash@x.com", visibility="public")
        u2 = User(username="misty", email="misty@x.com", visibility="public")
        u1.set_password("x"); u2.set_password("x")
        _db.session.add_all([f1, f2, u1, u2])
        _db.session.commit()
        yield {"f1": f1.id, "f2": f2.id, "u1": u1.id, "u2": u2.id}
        _db.session.rollback()


def _login(client, user_id):
    with client.session_transaction() as s:
        s["_user_id"] = str(user_id)
        s["_fresh"] = True


def test_wishlist_lists_all_missing_without_input(client, world):
    _login(client, world["u1"])
    _db.session.add(UserCollection(user_id=world["u1"], form_id=world["f1"], owned=True, quantity=1))
    _db.session.commit()

    html = client.get("/wishlist/").get_data(as_text=True)
    assert "#9002" in html          # faltante aparece sozinho
    assert "#9001" not in html      # possuído não aparece
    assert "Adicionar à wishlist" not in html


def test_wishlist_auto_priority_by_evolution(client, world):
    from app.models.pokemon import EvolutionChain
    from app.blueprints.wishlist.routes import get_evolve_sources

    # cadeia 9001 -> 9002 -> 9003; espécie 9004 sem família
    _db.session.add_all([Species(id=9003, name="venusaur", generation=1),
                         Species(id=9004, name="pidgey", generation=1)])
    _db.session.flush()
    f3 = Form(species_id=9003, form_name="normal"); f4 = Form(species_id=9004, form_name="normal")
    _db.session.add_all([f3, f4]); _db.session.flush()
    _db.session.add_all([
        EvolutionChain(from_form_id=world["f1"], to_form_id=world["f2"]),
        EvolutionChain(from_form_id=world["f2"], to_form_id=f3.id),
        UserCollection(user_id=world["u1"], form_id=world["f1"], owned=True, quantity=1),
    ])
    _db.session.commit()

    src = get_evolve_sources(world["u1"], [world["f2"], f3.id, f4.id])
    assert src == {world["f2"]: "Bulbasaur", f3.id: "Bulbasaur"}  # 2 etapas também conta
    assert f4.id not in src                                        # nada da família -> Alta

    _login(client, world["u1"])
    html = client.get("/wishlist/").get_data(as_text=True)
    assert "Evoluir de Bulbasaur" in html and "🔥 Alta" in html
    _db.session.query(EvolutionChain).delete(); _db.session.commit()


def test_wishlist_priority_toggle(client, world):
    _login(client, world["u1"])
    r = client.post(f"/wishlist/priority/{world['f2']}").get_json()
    assert r == {"ok": True, "priority": True}
    r = client.post(f"/wishlist/priority/{world['f2']}").get_json()
    assert r["priority"] is False


def test_matching_uses_missing_automatically(client, world):
    _db.session.add(UserCollection(user_id=world["u2"], form_id=world["f2"], owned=True, quantity=2, for_trade=True))
    _db.session.commit()
    assert run_matching_for_user(world["u1"]) == 1


def test_upsert_perfect_flag_preserved_when_not_sent(client, world):
    _login(client, world["u1"])
    base = {"form_id": world["f1"], "owned": "true", "quantity": "1", "for_trade": "false", "has_shiny": "false"}
    r = client.post("/collection/upsert", data={**base, "has_perfect": "true"}).get_json()
    assert r["has_perfect"] is True
    # telas antigas não enviam has_perfect -> mantém
    r = client.post("/collection/upsert", data=base).get_json()
    assert r["has_perfect"] is True
    # deixou de possuir -> zera
    r = client.post("/collection/upsert", data={**base, "owned": "false", "quantity": "0"}).get_json()
    assert r["has_perfect"] is False


def test_manual_individual_sets_perfect_and_detail_api(client, world):
    _login(client, world["u1"])
    r = client.post("/collection/individual", data={
        "form_id": world["f1"], "cp": "1500", "atk_iv": "15", "def_iv": "15", "sta_iv": "15",
    }).get_json()
    assert r["ok"] and r["has_perfect"] is True and r["quantity"] == 1
    assert r["individual"]["iv_pct"] == 100.0

    col = client.get("/pokedex/api/9001").get_json()["collection"]
    assert col["has_perfect"] is True
    assert len(col["individuals"]) == 1 and col["individuals"][0]["cp"] == 1500

    r = client.post(f"/collection/individual/{col['individuals'][0]['id']}/delete").get_json()
    assert r == {"ok": True, "has_perfect": False}


def test_pokegenie_parse_and_apply(app, world):
    rows, errors = import_service.parse_pokegenie(POKEGENIE_CSV.encode("utf-8"))
    assert errors == []
    assert len(rows) == 1
    row = rows[0]
    assert row["quantity"] == 2 and row["has_perfect"] is True and row["for_trade"] is True

    best, other = row["_individuals"]
    assert (best["cp"], best["atk_iv"], best["level"], best["is_lucky"], best["is_favorite"]) == (1100, 15, 30.0, True, True)
    assert best["quick_move"] == "Vine Whip" and best["rank_great"] == 85.3
    assert other["is_shadow"] is True and other["for_trade"] is True
    assert "Dust" in best["raw"]  # coluna não mapeada preservada

    result = import_service.apply_import(world["u1"], rows)
    assert result["individuals"] == 2
    uc = _db.session.query(UserCollection).filter_by(user_id=world["u1"], form_id=world["f1"]).one()
    assert uc.has_perfect and uc.quantity == 2

    # reimportar substitui (não duplica) os exemplares do PokeGenie
    import_service.apply_import(world["u1"], rows)
    assert _db.session.query(UserPokemon).filter_by(user_id=world["u1"]).count() == 2
