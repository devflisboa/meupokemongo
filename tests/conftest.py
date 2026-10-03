import pytest
from app import create_app
from app.config import DevelopmentConfig, config_map
from app.extensions import db as _db


class TestingConfig(DevelopmentConfig):
    TESTING = True
    WTF_CSRF_ENABLED = False
    # Precisa estar na config ANTES do create_app: o Flask-SQLAlchemy 3 cria a engine no init_app
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"


config_map["testing"] = TestingConfig


@pytest.fixture(scope="session")
def app():
    app = create_app("testing")
    with app.app_context():
        _db.create_all()
        yield app
        _db.drop_all()


@pytest.fixture()
def client(app):
    return app.test_client()


@pytest.fixture()
def db(app):
    return _db
