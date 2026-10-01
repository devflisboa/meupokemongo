import pytest
from app.models.user import User
from app.models.collection import UserCollection


def test_user_password_hash(app, db):
    with app.app_context():
        u = User(username="ash", email="ash@example.com")
        u.set_password("pikachu123")
        assert u.check_password("pikachu123")
        assert not u.check_password("errada")


def test_collection_is_owned(app, db):
    entry = UserCollection(user_id=1, form_id=1, owned=True, quantity=2)
    assert entry.is_owned()

    entry.quantity = 0
    assert not entry.is_owned()

    entry.owned = False
    entry.quantity = 3
    assert not entry.is_owned()


def test_collection_set_for_trade_rejects_unowned(app, db):
    entry = UserCollection(user_id=1, form_id=1, owned=False, quantity=0)
    with pytest.raises(ValueError):
        entry.set_for_trade(True)
