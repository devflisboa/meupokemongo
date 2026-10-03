"""Início redesenhado: Painel → Central de Trocas → Feed (logado) e apresentação (sem login)."""
from datetime import timedelta

import pytest

from app.config import now_br
from app.extensions import db as _db
from app.models.user import User
from app.models.pokemon import Species, Form
from app.models.collection import UserCollection
from app.models.individual import UserPokemon
from app.models.wishlist import Wishlist
from app.models.trade import TradeMatch, WhatsappClick
from app.services.home_service import ha_quanto, region_progress


@pytest.mark.parametrize("delta,expected", [
    (timedelta(seconds=10), "agora"), (timedelta(minutes=5), "há 5 min"), (timedelta(hours=3), "há 3 h"),
    (timedelta(days=1, hours=2), "ontem"), (timedelta(days=4), "há 4 dias"),
])
def test_ha_quanto(delta, expected):
    agora = now_br()
    assert ha_quanto(agora - delta, agora) == expected


@pytest.fixture()
def town(app):
    with app.app_context():
        for model in (WhatsappClick, TradeMatch, UserPokemon, Wishlist, UserCollection, Form, Species, User):
            _db.session.query(model).delete()
        _db.session.add_all([Species(id=1, name="bulbasaur", name_pt="Bulbasaur", generation=1),
                             Species(id=4, name="charmander", name_pt="Charmander", generation=1),
                             Species(id=152, name="chikorita", name_pt="Chikorita", generation=2)])
        _db.session.flush()
        f = {sid: Form(species_id=sid, form_name="normal", type1="grass") for sid in (1, 4, 152)}
        _db.session.add_all(f.values())
        ash = User(username="ash", email="ash@x.test", state="CE", city="Fortaleza", trainer_code="1111 2222 3333")
        misty = User(username="misty", email="misty@x.test", state="CE", city="Fortaleza", favorite_species_id=4)
        for u in (ash, misty):
            u.set_password("x")
        _db.session.add_all([ash, misty])
        _db.session.flush()
        _db.session.add_all([
            UserCollection(user_id=ash.id, form_id=f[1].id, owned=True, quantity=2, for_trade=True, has_shiny=True),
            UserCollection(user_id=misty.id, form_id=f[4].id, owned=True, quantity=2, for_trade=True),
        ])
        _db.session.commit()
        yield {"ash": ash.id}
        _db.session.rollback()


def _login(client, uid):
    from flask import g
    g.pop("_login_user", None)
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_region_progress(town):
    regions = {r["name"]: r for r in region_progress(town["ash"])}
    assert regions["Kanto"]["owned"] == 1 and regions["Kanto"]["total"] == 151
    assert regions["Johto"]["owned"] == 0 and len(regions) == 10


def test_home_logged_three_blocks_in_order(client, town):
    _login(client, town["ash"])
    html = client.get("/").get_data(as_text=True)
    pos = [html.index(f'id="home-{s}"') for s in ("painel", "trocas", "feed")]
    assert pos == sorted(pos)                                  # Painel → Central de Trocas → Feed
    assert "Olá, ash!" in html and "Progresso por região" in html
    assert "⭐ 1 Brilhantes" in html
    assert 'class="bg-white rounded-2xl shadow-sm border border-green-200 overflow-hidden home-reciprocal"' in html  # mão dupla com misty
    assert "é só evoluir" in html and "só por troca" in html
    assert 'id="home-perto"' in html and "misty" in html
    # feed: misty tem Charmander (que ash procura) + misty é treinadora nova ao alcance
    assert "tem <b>Charmander</b> para troca" in html and "você procura!" in html
    assert 'data-kind="new_trainer"' in html
    assert 'id="home-eventos"' in html


def test_home_anonymous_landing(client, town):
    from flask import g
    g.pop("_login_user", None)
    html = client.get("/").get_data(as_text=True)
    assert 'id="landing"' in html and "Ache quem tem o Pokémon que falta" in html
    assert "Como funciona" in html and 'id="landing-showcase"' in html
    assert 'href="/trade/misty"' in html and 'id="home-eventos"' in html
    assert 'id="home-painel"' not in html
