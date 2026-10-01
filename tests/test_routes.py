def test_home_returns_200(client):
    resp = client.get("/")
    assert resp.status_code == 200


def test_login_page_returns_200(client):
    resp = client.get("/auth/login")
    assert resp.status_code == 200


def test_registro_page_returns_200(client):
    resp = client.get("/auth/registro")
    assert resp.status_code == 200


def test_pokedex_returns_200(client):
    resp = client.get("/pokedex/")
    assert resp.status_code == 200


def test_collection_redirects_unauthenticated(client):
    resp = client.get("/collection/")
    assert resp.status_code == 302
