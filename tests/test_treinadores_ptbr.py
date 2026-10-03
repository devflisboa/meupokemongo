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
    # Início novo: "Treinadores perto de você" com link para todos
    assert 'id="home-trocas"' in html and 'href="/treinadores"' in html


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


# ── Personalização pela cor do tipo do favorito ─────────────────────────────
def test_theme_from_favorite_type(town):
    misty = _db.session.query(User).filter_by(username="misty").one()   # favorito: Charmander (fogo)
    assert misty.favorite_type == "fire"
    assert misty.theme == {"grad": "from-orange-700 to-red-700", "dark_text": False, "type": "fire"}
    ash = _db.session.query(User).filter_by(username="ash").one()        # sem favorito → azul padrão
    assert ash.theme["type"] is None and "1B2A4A" in ash.theme["grad"]


def test_treinadores_cards_colored_by_favorite(client, town):
    _login(client, town["ash"])
    html = client.get("/treinadores").get_data(as_text=True)
    assert 'data-theme="fire"' in html and "from-orange-700 to-red-700" in html
    assert 'data-theme="padrao"' in html
    binder = client.get("/trade/misty").get_data(as_text=True)
    assert 'id="binder-header"' in binder and 'data-theme="fire"' in binder


def test_favorite_nudge_only_without_favorite(client, town):
    ash = _db.session.query(User).filter_by(username="ash").one()
    ash.trainer_code = "1111 2222 3333"   # perfil de troca completo → aviso do favorito
    _db.session.commit()
    _login(client, town["ash"])
    assert 'id="fav-nudge"' in client.get("/treinadores").get_data(as_text=True)
    ash.favorite_species_id = 1
    _db.session.commit()
    _login(client, town["ash"])
    assert 'id="fav-nudge"' not in client.get("/treinadores").get_data(as_text=True)


def test_theme_palette_covers_all_types():
    from app.data.i18n import TYPE_THEME, LIGHT_TYPES
    assert set(TYPE_THEME) == set(TYPE_PT)          # os 18 tipos têm tema
    assert LIGHT_TYPES <= set(TYPE_PT)
    # contraste ≥ 4,5:1 medido no navegador (Playwright) em 03/10/2026; tons escuros para texto branco
    for t in set(TYPE_PT) - LIGHT_TYPES:
        assert any(f"-{n}" in TYPE_THEME[t] for n in ("600", "700", "800", "900")), t


def test_single_entrar_link_when_logged_out(client):
    from flask import g
    g.pop("_login_user", None)
    html = client.get("/").get_data(as_text=True)
    assert html.split("</header>")[0].count('href="/auth/login"') == 1


def test_footer_themed_and_signed(client, town):
    from flask import g
    g.pop("_login_user", None)
    html = client.get("/treinadores").get_data(as_text=True)
    foot = html.split('id="site-footer"')[1]
    assert "Desenvolvido por Felipe Lisboa" in foot and 'data-theme="padrao"' in html
    assert "Feito com Flask" not in html and "v1.0" not in foot
    misty = _db.session.query(User).filter_by(username="misty").one()  # favorito: fogo
    _login(client, misty.id)
    html = client.get("/treinadores").get_data(as_text=True)
    assert 'id="site-footer" data-theme="fire"' in html


# ── Menu de 5 itens (03/10/2026) ─────────────────────────────────────────────
def _bottom_nav(html):
    return html.split("Bottom Nav global")[1].split("</nav>")[0] if "Bottom Nav global" in html \
        else html.split('grid grid-cols-5 sm:hidden')[1].split("</nav>")[0]


def test_menu_cinco_itens_logado(client, town):
    import re
    _login(client, town["ash"])
    html = client.get("/").get_data(as_text=True)
    nav = html.split('grid grid-cols-5 sm:hidden')[1].split("</nav>")[0]
    assert re.findall(r"<span>([^<]+)</span>", nav) == ["Início", "Coleção", "Desejos", "Trocas", "Treinadores"]
    desktop = html.split('<div class="hidden md:flex')[1].split("Direita: Bell")[0]
    for label in ("Coleção", "Desejos", "Trocas", "Treinadores"):
        assert f"\n            {label}\n" in desktop
    assert "Catalogar\n" not in desktop and "Pokédex\n" not in desktop.split("{% else %}")[0]


def test_menu_visitante(client, town):
    import re
    from flask import g
    g.pop("_login_user", None)
    html = client.get("/treinadores").get_data(as_text=True)
    desktop = html.split("Início")[1].split("Cadastrar")[0]
    assert "Pokédex" in desktop and "Treinadores" in desktop and "Desejos" not in desktop


def test_colecao_tem_catalogar_e_convite(client, town):
    _login(client, town["ash"])                       # ash tem 1 capturado: botão, sem convite
    html = client.get("/collection/").get_data(as_text=True)
    assert 'id="btn-catalogar"' in html and 'id="catalogar-convite"' not in html
    novato = User(username="novato", email="n@x.test")
    novato.set_password("x"); _db.session.add(novato); _db.session.commit()
    _login(client, novato.id)                         # nada marcado: convite para catalogar
    assert 'id="catalogar-convite"' in client.get("/collection/").get_data(as_text=True)
    # Pokédex continua existindo e acende "Coleção" no menu
    pk = client.get("/pokedex/").get_data(as_text=True)
    nav = pk.split('grid grid-cols-5 sm:hidden')[1].split("</nav>")[0]
    assert 'id="bnav-colecao"' in nav and "border-[#CC0000]" in nav.split('id="bnav-colecao"')[1].split("</a>")[0]
