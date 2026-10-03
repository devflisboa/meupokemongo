"""Rate limit: uso normal não pode ser bloqueado; login sim (força bruta)."""


def test_normal_usage_not_blocked(client):
    # 80 requisições seguidas (> antigo limite de 50/h) devem passar
    codes = {client.get("/pokedex/").status_code for _ in range(80)}
    assert codes == {200}


def test_login_post_is_limited(client):
    codes = [
        client.post("/auth/login", data={"username": "ninguem", "password": "x"},
                    environ_base={"REMOTE_ADDR": "10.9.9.9"}).status_code
        for _ in range(11)
    ]
    assert codes[:10] == [200] * 10
    assert codes[10] == 429


def test_proxyfix_uses_forwarded_ip(client):
    # cada IP real (X-Forwarded-For) tem a própria cota — usuários não dividem o IP do proxy
    for ip in ("1.1.1.1", "2.2.2.2"):
        codes = [
            client.post("/auth/login", data={"username": "a", "password": "x"},
                        headers={"X-Forwarded-For": ip}).status_code
            for _ in range(3)
        ]
        assert 429 not in codes
