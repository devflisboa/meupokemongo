"""Acesso de admin ("ver como" cada treinador) e regra de imagens (sprite pequeno × GIF)."""
import pytest

from app.extensions import db as _db
from app.models.user import User
from app.models.pokemon import Species, Form
from app.models.collection import UserCollection
from app.models.individual import UserPokemon
from app.models.wishlist import Wishlist
from app.models.trade import TradeMatch, WhatsappClick
from app.data.sprites import sprite_small, sprite_anim

ART = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/25.png"
BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"


def test_sprite_helpers():
    assert sprite_small(ART) == f"{BASE}/25.png"
    assert sprite_anim(ART) == f"{BASE}/other/showdown/25.gif"
    assert sprite_anim(ART, shiny=True) == f"{BASE}/other/showdown/shiny/25.gif"
    form_art = ART.replace("/25.png", "/10100.png")  # forma alternativa (id 10xxx)
    assert sprite_small(form_art) == f"{BASE}/10100.png"
    assert sprite_small(None) == "" and sprite_small("https://x/sem-id.jpg") == "https://x/sem-id.jpg"


@pytest.fixture()
def people(app):
    with app.app_context():
        for model in (WhatsappClick, TradeMatch, UserPokemon, Wishlist, UserCollection, Form, Species, User):
            _db.session.query(model).delete()
        _db.session.add(Species(id=25, name="pikachu", name_pt="Pikachu", generation=1))
        _db.session.flush()
        pika = Form(species_id=25, form_name="normal", type1="electric", sprite_url=ART)
        admin = User(username="boss", email="boss@x.test", is_admin=True)
        ash = User(username="ash", email="ash@x.test")
        brock = User(username="brock", email="brock@x.test", visibility="private")
        for u in (admin, ash, brock):
            u.set_password("x")
        _db.session.add_all([pika, admin, ash, brock])
        _db.session.flush()
        _db.session.add(UserCollection(user_id=ash.id, form_id=pika.id, owned=True, quantity=1,
                                       for_trade=True, has_shiny=True))
        _db.session.commit()
        yield {"admin": admin.id, "ash": ash.id, "brock": brock.id}
        _db.session.rollback()


def _login(client, uid):
    from flask import g
    # o app de teste mantém um app context aberto a sessão toda; o Flask-Login guarda o usuário em g
    g.pop("_login_user", None)
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_admin_link_only_for_admin(client, people):
    _login(client, people["admin"])
    html = client.get("/").get_data(as_text=True)
    assert 'id="admin-gear"' in html                      # engrenagem = admin
    assert "Administração" in client.get("/auth/perfil").get_data(as_text=True)
    _login(client, people["ash"])
    html = client.get("/").get_data(as_text=True)
    assert 'id="admin-gear"' not in html and 'href="/admin/usuarios"' not in html
    client.get("/auth/logout")
    _login(client, 0)
    assert 'id="admin-gear"' not in client.get("/").get_data(as_text=True)  # deslogado


def test_admin_view_as_on_estoque_and_binder(client, people):
    _login(client, people["admin"])
    estoque = client.get("/estoque/ash").get_data(as_text=True)
    assert "Admin — visualizando somente leitura" in estoque and "const IS_OWNER = false" in estoque
    binder = client.get("/trade/ash").get_data(as_text=True)
    assert 'id="admin-bar"' in binder and "brock (oculto)" in binder
    # admin enxerga até quem está oculto nas trocas
    assert client.get("/estoque/brock").status_code == 200
    assert client.get("/trade/brock").status_code == 200
    assert client.get("/admin/usuarios").status_code == 200


def test_non_admin_has_no_view_as(client, people):
    _login(client, people["ash"])
    assert 'id="admin-bar"' not in client.get("/trade/ash").get_data(as_text=True)
    assert client.get("/estoque/brock").status_code == 404
    assert client.get("/admin/usuarios").status_code == 403


def test_grids_use_small_sprites_and_modal_api_has_gifs(client, people):
    _login(client, people["ash"])
    coll = client.get("/collection/").get_data(as_text=True)
    assert f'src="{BASE}/25.png"' in coll and f'data-art="{ART}"' in coll
    data = client.get("/pokedex/api/25").get_json()["form"]
    assert data["sprite_anim"].endswith("/showdown/25.gif")
    assert data["sprite_anim_shiny"].endswith("/showdown/shiny/25.gif")
