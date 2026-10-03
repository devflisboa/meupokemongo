"""Página de Treinadores e revisão PT-BR."""
import pytest

from app.extensions import db as _db
from app.models.user import User
from app.models.pokemon import Species, Form
from app.models.collection import UserCollection
from app.models.individual import UserPokemon
from app.models.wishlist import Wishlist
from app.models.trade import TradeMatch, WhatsappClick
from app.data.i18n import tipo, TYPE_PT


def test_tipo_filter():
    assert tipo("grass") == "Planta" and tipo("fire") == "Fogo" and tipo("ground") == "Terrestre"
    assert tipo(None) == "" and tipo("unknown") == "Unknown"
    assert len(TYPE_PT) == 18


@pytest.fixture()
def town(app):
    with app.app_context():
        for model in (WhatsappClick, TradeMatch, UserPokemon, Wishlist, UserCollection, Form, Species, User):
            _db.session.query(model).delete()
        _db.session.add_all([Species(id=1, name="bulbasaur", name_pt="Bulbasaur", generation=1),
                             Species(id=4, name="charmander", name_pt="Charmander", generation=1)])
        _db.session.flush()
        bulba = Form(species_id=1, form_name="normal", type1="grass", type2="poison")
        char = Form(species_id=4, form_name="normal", type1="fire")
        ash = User(username="ash", email="ash@x.test", state="CE", city="Fortaleza")
        misty = User(username="misty", email="misty@x.test", state="CE", city="Fortaleza", favorite_species_id=4)
        gary = User(username="gary", email="gary@x.test", state="SP", city="São Paulo")
        hidden = User(username="oculto", email="o@x.test", visibility="private")
        for u in (ash, misty, gary, hidden):
            u.set_password("x")
        _db.session.add_all([bulba, char, ash, misty, gary, hidden])
        _db.session.flush()
        _db.session.add_all([
            UserCollection(user_id=ash.id, form_id=bulba.id, owned=True, quantity=2, for_trade=True),
            UserCollection(user_id=misty.id, form_id=char.id, owned=True, quantity=2, for_trade=True),
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


def test_treinadores_public_list(client, town):
    from flask import g
    g.pop("_login_user", None)
    html = client.get("/treinadores").get_data(as_text=True)
    for name in ("ash", "misty", "gary"):
        assert f'href="/trade/{name}"' in html
    assert "oculto" not in html                     # privado não aparece
    assert "3 treinadores" in html


def test_treinadores_logged_order_and_badges(client, town):
    _login(client, town["ash"])
    html = client.get("/treinadores").get_data(as_text=True)
    order = [html.index(f'href="/trade/{n}"') for n in ("ash", "misty", "gary")]
    assert order == sorted(order)                   # você → mão dupla/cidade → fora do alcance
    assert "(você)" in html
    assert "1 troca de mão dupla" in html            # misty: Charmander ⇄ Bulbasaur
    assert "Outra cidade — sem troca à distância" in html
    assert "showdown" not in html.split('id="tr-grid"')[1]  # lista leve: favorito estático


def test_dashboard_card_links_to_treinadores(client, town):
    _login(client, town["ash"])
    html = client.get("/").get_data(as_text=True)
    assert 'id="card-treinadores"' in html and 'href="/treinadores"' in html


def test_ptbr_texts(client, town):
    _login(client, town["ash"])
    coll = client.get("/collection/").get_data(as_text=True)
    assert "Planta" in coll and "Venenoso" in coll and ">Grass<" not in coll
    assert "Brilhante" in coll and "Shiny?" not in coll
    wish = client.get("/wishlist/").get_data(as_text=True)
    assert "Minha Lista de Desejos" in wish and "Wishlist" not in wish.split("<body")[1].replace("wishlist", "")
    assert "Vitrine de Trocas" in client.get("/trade/ash").get_data(as_text=True)
    home = client.get("/").get_data(as_text=True)
    assert "Início" in home and ">Dashboard<" not in home
