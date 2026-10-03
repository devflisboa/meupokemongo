"""#23 — perfil de troca, visibilidade aberta, contato com consentimento e exclusão de conta."""
import pytest

from app.extensions import db as _db
from app.models.user import User
from app.models.pokemon import Species, Form
from app.models.collection import UserCollection
from app.models.individual import UserPokemon
from app.models.wishlist import Wishlist
from app.models.trade import TradeMatch, WhatsappClick
from app.services.profile_service import resolve_city, normalize_whatsapp, format_whatsapp
from app.services.matching_service import run_matching_for_user


# ── helpers puros ────────────────────────────────────────────────────────────
@pytest.mark.parametrize("state,city,expected", [
    ("CE", "Fortaleza", ("CE", "Fortaleza")),
    ("ce", "fortaleza", ("CE", "Fortaleza")),
    ("SP", "sao paulo", ("SP", "São Paulo")),        # sem acento
    ("CE", "São Paulo", (None, None)),               # cidade de outra UF
    ("XX", "Fortaleza", (None, None)),
])
def test_resolve_city(state, city, expected):
    assert resolve_city(state, city) == expected


@pytest.mark.parametrize("raw,expected", [
    ("(85) 99999-1234", "5585999991234"),
    ("+55 85 99999-1234", "5585999991234"),
    ("8533334444", "558533334444"),
    ("99999-1234", None),          # sem DDD
    ("abc", None),
])
def test_normalize_whatsapp(raw, expected):
    assert normalize_whatsapp(raw) == expected


def test_format_whatsapp():
    assert format_whatsapp("5585999991234") == "(85) 99999-1234"


# ── fluxo ────────────────────────────────────────────────────────────────────
@pytest.fixture()
def people(app):
    with app.app_context():
        for model in (WhatsappClick, TradeMatch, UserPokemon, Wishlist, UserCollection, Form, Species, User):
            _db.session.query(model).delete()
        _db.session.add(Species(id=9101, name="lapras", generation=1))
        _db.session.flush()
        form = Form(species_id=9101, form_name="normal")
        ash = User(username="ash", email="ash@x.com")
        misty = User(username="misty", email="misty@x.com", trainer_code="4444 5555 6666",
                     state="CE", city="Fortaleza", whatsapp="5585999991234", allow_whatsapp=True)
        brock = User(username="brock", email="brock@x.com", visibility="private")
        for u in (ash, misty, brock):
            u.set_password("x")
        _db.session.add_all([form, ash, misty, brock])
        _db.session.flush()
        for owner in (misty, brock):
            _db.session.add(UserCollection(user_id=owner.id, form_id=form.id, owned=True, quantity=1, for_trade=True))
        _db.session.commit()
        yield {"form": form.id, "ash": ash.id, "misty": misty.id, "brock": brock.id}
        _db.session.rollback()


def _login(client, uid):
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_register_goes_to_onboarding(client, people):
    r = client.post("/auth/registro", data={"username": "gary", "email": "gary@x.com", "password": "12345678"},
                    environ_base={"REMOTE_ADDR": "10.1.1.1"})
    assert r.status_code == 302 and r.headers["Location"].endswith("/auth/onboarding")


def test_onboarding_saves_profile(client, people):
    _login(client, people["ash"])
    r = client.post("/auth/onboarding", data={
        "trade_profile": "1", "trainer_code": "123456789012", "state": "CE", "city": "fortaleza",
        "show_in_trades": "on", "can_trade_remote": "on", "allow_whatsapp": "on", "whatsapp": "(85) 98888-7777",
    })
    assert r.status_code == 302
    ash = _db.session.get(User, people["ash"])
    assert (ash.trainer_code, ash.state, ash.city) == ("1234 5678 9012", "CE", "Fortaleza")
    assert ash.can_trade_remote and ash.allow_whatsapp and ash.whatsapp == "5585988887777"
    assert not ash.needs_onboarding


@pytest.mark.parametrize("data,msg", [
    ({"trainer_code": "1234"}, "12 números"),
    ({"state": "CE", "city": "Cidade Inventada"}, "Cidade não encontrada"),
    ({"allow_whatsapp": "on", "whatsapp": ""}, "Informe o número"),
])
def test_onboarding_validation(client, people, data, msg):
    _login(client, people["ash"])
    r = client.post("/auth/onboarding", data={"trade_profile": "1", **data})
    assert r.status_code == 200 and msg in r.get_data(as_text=True)


def test_private_user_hidden_everywhere(client, people):
    _login(client, people["ash"])
    assert client.get("/estoque/brock").status_code == 404
    assert client.get("/auth/treinador/brock").status_code == 404
    assert client.get("/estoque/misty").status_code == 200
    # matching só cria com quem aparece nas trocas
    assert run_matching_for_user(people["ash"]) == 1
    owners = {m.owner_id for m in _db.session.query(TradeMatch).filter_by(wisher_id=people["ash"])}
    assert owners == {people["misty"]}


def test_private_user_sees_own_estoque(client, people):
    _login(client, people["brock"])
    assert client.get("/estoque/brock").status_code == 200


def test_whatsapp_only_with_consent(client, people):
    _login(client, people["ash"])
    run_matching_for_user(people["ash"])
    match = _db.session.query(TradeMatch).filter_by(wisher_id=people["ash"]).one()
    r = client.get(f"/trades/whatsapp/{match.id}")
    assert r.status_code == 302 and r.headers["Location"].startswith("https://wa.me/5585999991234?text=")

    misty = _db.session.get(User, people["misty"])
    misty.allow_whatsapp = False
    _db.session.commit()
    r = client.get(f"/trades/whatsapp/{match.id}")
    assert r.status_code == 302 and "/trades" in r.headers["Location"]  # sem número: volta com aviso


def test_trades_page_shows_location_and_code(client, people):
    _login(client, people["ash"])
    html = client.get("/trades/").get_data(as_text=True)
    assert "Fortaleza/CE" in html and "Propor troca" in html and "4444 5555 6666" in html


def test_delete_account_removes_everything(client, people):
    _login(client, people["ash"])
    run_matching_for_user(people["ash"])
    _db.session.add(UserCollection(user_id=people["ash"], form_id=people["form"], owned=False, quantity=0))
    _db.session.commit()

    r = client.post("/auth/perfil", data={"action": "excluir", "confirm_username": "errado"})
    assert _db.session.get(User, people["ash"]) is not None   # confirmação errada não apaga

    r = client.post("/auth/perfil", data={"action": "excluir", "confirm_username": "ash"})
    assert r.status_code == 302
    _db.session.expire_all()
    assert _db.session.get(User, people["ash"]) is None
    assert _db.session.query(UserCollection).filter_by(user_id=people["ash"]).count() == 0
    assert _db.session.query(TradeMatch).filter_by(wisher_id=people["ash"]).count() == 0
