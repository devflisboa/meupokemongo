"""#24 proximidade + mão dupla, #18 Trade Binder, #15 progresso Shiny/100%, #20 faltantes sob demanda."""
import json
import re

import pytest

from app.extensions import db as _db
from app.models.user import User
from app.models.pokemon import Species, Form
from app.models.collection import UserCollection
from app.models.individual import UserPokemon
from app.models.wishlist import Wishlist
from app.models.trade import TradeMatch, WhatsappClick
from app.services.matching_service import (
    proximity_tier, run_matching_for_user, get_active_matches_for_user, get_reciprocal_trades,
    TIER_CITY, TIER_REMOTE, TIER_UNKNOWN,
)


def U(**kw):
    kw.setdefault("visibility", "public")
    name = kw.pop("username", "x")
    return User(username=name, email=f"{name}@x.test", **kw)


@pytest.mark.parametrize("viewer,other,expected", [
    (dict(state="CE", city="Fortaleza"), dict(state="CE", city="Fortaleza"), TIER_CITY),
    (dict(state="CE", city="Fortaleza"), dict(state="CE", city="Caucaia"), None),       # cidade vizinha, sem distância
    (dict(state="CE", city="Fortaleza"), dict(state="SP", city="São Paulo", can_trade_remote=True), TIER_REMOTE),
    (dict(state="CE", city="Fortaleza", can_trade_remote=True), dict(state="SP", city="São Paulo"), TIER_REMOTE),
    (dict(state="CE", city="Fortaleza"), dict(), TIER_UNKNOWN),                          # outro sem cidade
    (dict(), dict(state="SP", city="São Paulo"), TIER_UNKNOWN),                          # eu sem cidade
    (dict(state="CE", city="Fortaleza"), dict(state="CE", city="Fortaleza", visibility="private"), None),
])
def test_proximity_tier(viewer, other, expected):
    assert proximity_tier(U(**viewer), U(**other)) == expected


@pytest.fixture()
def town(app):
    """ash (Fortaleza) quer 9201/9202, oferece 9203.
    misty (Fortaleza) oferece 9201 e não tem 9203 → mão dupla.
    gary (São Paulo, sem distância) oferece 9202 → fora do alcance.
    brock (Recife, troca à distância) oferece 9202 e já tem 9203 → só oferta."""
    with app.app_context():
        for model in (WhatsappClick, TradeMatch, UserPokemon, Wishlist, UserCollection, Form, Species, User):
            _db.session.query(model).delete()
        for sid in (9201, 9202, 9203):
            _db.session.add(Species(id=sid, name=f"poke{sid}", name_pt=f"Poke{sid}", generation=1))
        _db.session.flush()
        forms = {sid: Form(species_id=sid, form_name="normal", sprite_url=f"https://x/{sid}.png") for sid in (9201, 9202, 9203)}
        _db.session.add_all(forms.values())
        people = {
            "ash": U(username="ash", state="CE", city="Fortaleza", trainer_code="1111 2222 3333"),
            "misty": U(username="misty", state="CE", city="Fortaleza"),
            "gary": U(username="gary", state="SP", city="São Paulo"),
            "brock": U(username="brock", state="PE", city="Recife", can_trade_remote=True),
        }
        for p in people.values():
            p.set_password("x")
        _db.session.add_all(people.values())
        _db.session.flush()
        f = {sid: forms[sid].id for sid in forms}

        def own(user, sid, trade=False, **kw):
            _db.session.add(UserCollection(user_id=people[user].id, form_id=f[sid], owned=True,
                                           quantity=2, for_trade=trade, **kw))
        own("ash", 9203, trade=True, has_shiny=True, has_perfect=True)
        own("misty", 9201, trade=True)
        own("gary", 9202, trade=True)
        own("brock", 9202, trade=True)
        own("brock", 9203)
        _db.session.add(Wishlist(user_id=people["ash"].id, form_id=f[9202], priority="high"))
        _db.session.commit()
        yield {"ids": {k: v.id for k, v in people.items()}, "f": f}
        _db.session.rollback()


def _login(client, uid):
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_matching_respects_proximity_and_orders(town):
    ash = town["ids"]["ash"]
    assert run_matching_for_user(ash) == 2  # misty (cidade) + brock (distância); gary fica de fora
    owners = [m.owner.username for m in get_active_matches_for_user(ash)]
    assert owners == ["misty", "brock"]


def test_reciprocal_trades(town):
    rec = get_reciprocal_trades(town["ids"]["ash"])
    assert [r["user"].username for r in rec] == ["misty"]
    r = rec[0]
    assert r["tier"] == TIER_CITY
    assert [f.species_id for f in r["they_have"]] == [9201]
    assert [f.species_id for f in r["i_have"]] == [9203]
    assert r["they_names"] == "Poke9201"


def test_trades_page_shows_reciprocal_first(client, town):
    _login(client, town["ids"]["ash"])
    html = client.get("/trades/").get_data(as_text=True)
    assert "Trocas de mão dupla" in html
    assert html.index("Trocas de mão dupla") < html.index("Quem tem o que te falta")
    assert "📍 Mesma cidade" in html and "🌐 Troca à distância" in html
    assert "gary" not in html


def test_trade_binder_public(client, town):
    html = client.get("/trade/ash").get_data(as_text=True)          # sem login
    assert "Tenho para troca" in html and "Poke9203" in html
    assert "Poke9202" in html                                       # ⭐ prioridade em "Procuro"
    assert 'property="og:title"' in html
    assert "Criar conta para trocar" in html


def test_trade_binder_shows_what_visitor_can_offer(client, town):
    _login(client, town["ids"]["misty"])
    html = client.get("/trade/ash").get_data(as_text=True)
    assert "Você tem 1 que ash procura" in html and "Poke9201" in html


def test_trade_binder_private_is_404(client, town):
    gary = _db.session.get(User, town["ids"]["gary"])
    gary.visibility = "private"
    _db.session.commit()
    assert client.get("/trade/gary").status_code == 404
    assert client.get("/trade/ninguem").status_code == 404


def test_collection_progress_and_filters(client, town):
    _login(client, town["ids"]["ash"])
    html = client.get("/collection/").get_data(as_text=True)
    for key in ("shiny", "perfect", "shundo"):
        block = re.search(rf'data-progress="{key}".*?</(a|div)>', html, re.S).group(0)
        assert re.search(r"\b1<span", block), key   # ash tem 1 shiny, 1 100%, 1 shundo
    shiny_html = client.get("/collection/?show=shiny").get_data(as_text=True)
    assert 'data-poke-id="9203"' in shiny_html and 'data-poke-id="9201"' not in shiny_html


def test_estoque_missing_as_json_not_html(client, town):
    html = client.get("/estoque/ash").get_data(as_text=True)
    assert "missing-card" not in html.split("const MISSING")[0].split("tab-content-faltantes")[1]
    data = json.loads(re.search(r"const MISSING = (\[.*?\]);", html, re.S).group(1))
    assert {p["id"] for p in data} == {9201, 9202}
    assert set(data[0]) == {"id", "n", "t", "s", "b"}
