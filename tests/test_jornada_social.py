"""Jornada (#27) — J2 (mapa, Hall da Fama, ranking, card, feed) e J3 (PvP assíncrono)."""
import uuid
from datetime import timedelta

import pytest

from app.config import now_br
from app.extensions import db as _db
from app.models.jornada import GameBattle, GameCreature, GameItem, GamePlayer
from app.models.user import User
from app.services.jornada import motor, pvp, social
from app.services.jornada.conteudo import carregar


class Dados:
    def __init__(self, *valores):
        self.valores = list(valores)

    def randint(self, a, b):
        return self.valores.pop(0)

    def choice(self, seq):
        return seq[0]

    def choices(self, keys, weights=None, k=1):
        return [keys[0]] * k

    def shuffle(self, seq):
        pass


@pytest.fixture(autouse=True)
def _ctx(app):
    social.limpar_cache()
    with app.test_request_context():
        yield
    from flask import g
    g.pop("_login_user", None)


def _user(prefixo="tj", visibility="public"):
    nome = f"{prefixo}_{uuid.uuid4().hex[:8]}"
    u = User(username=nome, email=f"{nome}@x.com", visibility=visibility)
    u.set_password("x")
    _db.session.add(u)
    _db.session.commit()
    motor.obter_jogador(u.id)
    _db.session.commit()
    return u


def _em(u, casa, **kw):
    p = _db.session.get(GamePlayer, u.id)
    p.posicao = casa
    p.acao_pendente = None
    for k, v in kw.items():
        setattr(p, k, v)
    _db.session.commit()
    social.limpar_cache()


def _criatura(u, key="seixo", desmaiada=False):
    cr = carregar().fase(1).criaturas[key]
    gc = GameCreature(user_id=u.id, creature_key=key, fase=1, estagio=cr["estagio"], volta=1, slot=1, desmaiada=desmaiada)
    _db.session.add(gc)
    _db.session.commit()
    return gc


def _itens(u, **qtds):
    for k, q in qtds.items():
        i = _db.session.get(GameItem, (u.id, k))
        if i:
            i.qtd = q
        else:
            _db.session.add(GameItem(user_id=u.id, item_key=k, qtd=q))
    _db.session.commit()


def _no(mapa, key):
    return next(n for n in mapa["nos"] if n["key"] == key)


# ── J2: mapa e Hall da Fama ────────────────────────────────────────────────

def test_mapa_agrupa_por_local_e_esconde_privado_e_teste(app):
    a = _user()
    b = _user(visibility="private")
    c = _user(prefixo="e2e")
    for u in (a, b, c):
        _em(u, 20)                                    # Lagoa Clara (19–26)
    nomes = [j["username"] for j in _no(social.mapa(1), "lagoa-clara")["jogadores"]]
    assert a.username in nomes
    assert b.username not in nomes and c.username not in nomes


def test_hall_da_fama_no_topo_em_ordem_de_conquista(app):
    primeiro, segundo = _user(), _user()
    _em(segundo, 72, titulo_fase1_em=now_br())
    _em(primeiro, 72, titulo_fase1_em=now_br() - timedelta(days=2))
    m = social.mapa(1)
    assert m["nos"][-1]["key"] == "hall-da-fama"     # último local = topo do mapa
    hall = [r["username"] for r in social.hall_da_fama(1)]
    assert hall.index(primeiro.username) < hall.index(segundo.username)


def test_online_pelo_last_seen(app):
    u = _user()
    _em(u, 5, last_seen=now_br())
    p = _db.session.get(GamePlayer, u.id)
    assert social.online(p)
    p.last_seen = now_br() - timedelta(minutes=10)
    assert not social.online(p)


# ── J2: ranking e card ─────────────────────────────────────────────────────

def test_ranking_ordem_posicao_depois_pp(app):
    a, b, c = _user(), _user(), _user()
    _em(a, 30, pp=10)
    _em(b, 30, pp=99)
    _em(c, 31, pp=0)
    nomes = [r["username"] for r in social.ranking(1)["lista"]]
    assert nomes.index(c.username) < nomes.index(b.username) < nomes.index(a.username)


def test_ranking_mostra_eu_mesmo_privado(app):
    u = _user(visibility="private")
    r = social.ranking(1, u.id)
    assert r["eu"]["username"] == u.username and r["eu"]["rank"] is None


def test_card_privado_so_para_o_dono(app):
    u = _user(visibility="private")
    outro = _user()
    assert social.card(u.username, outro.id) is None
    assert social.card(u.username, u.id)["eu"]


# ── J3: PvP ────────────────────────────────────────────────────────────────

def _duelo(casa=20):
    a, b = _user(), _user()
    _em(a, casa)
    _em(b, casa)
    ca = _criatura(a, "seixo")       # ataque 2
    cb = _criatura(b, "breu")        # ataque 2
    return a, b, ca, cb


def test_desafiar_exige_mesma_casa(app):
    a, b, ca, _ = _duelo()
    _em(b, 21)
    with pytest.raises(motor.JogoErro):
        pvp.desafiar(a.id, b.username, ca.id)


def test_pvp_vitoria_do_desafiante(app):
    a, b, ca, cb = _duelo()
    _itens(b, isca=0, tonico=2, rede=1)
    _itens(a, isca=0)
    pvp.desafiar(a.id, b.username, ca.id)
    batalha = _db.session.query(GameBattle).filter_by(desafiante_id=a.id).one()
    res = pvp.responder(b.id, batalha.id, cb.id, rng=Dados(6, 1))   # 6+2 × 1+2
    assert res["vencedor"] == a.username
    assert _db.session.get(GamePlayer, a.id).pp == 30
    assert _db.session.get(GameCreature, cb.id).desmaiada
    assert len(res["itens_roubados"]) == 2
    total_b = sum(i.qtd for i in _db.session.query(GameItem).filter_by(user_id=b.id))
    assert total_b == 1


def test_pvp_empate_defensor_vence(app):
    a, b, ca, cb = _duelo()
    pvp.desafiar(a.id, b.username, ca.id)
    batalha = _db.session.query(GameBattle).filter_by(desafiante_id=a.id).one()
    res = pvp.responder(b.id, batalha.id, cb.id, rng=Dados(3, 3))
    assert res["vencedor"] == b.username
    assert _db.session.get(GameCreature, ca.id).desmaiada


def test_pvp_isca_soma_um(app):
    a, b, ca, cb = _duelo()
    _itens(a, isca=1)
    pvp.desafiar(a.id, b.username, ca.id, usar_isca=True)
    assert _db.session.get(GameItem, (a.id, "isca")).qtd == 0
    batalha = _db.session.query(GameBattle).filter_by(desafiante_id=a.id).one()
    res = pvp.responder(b.id, batalha.id, cb.id, rng=Dados(3, 3))    # 3+2+1 × 3+2
    assert res["vencedor"] == a.username


def test_pvp_uma_vez_por_dia_por_par(app):
    a, b, ca, cb = _duelo()
    pvp.desafiar(a.id, b.username, ca.id)
    with pytest.raises(motor.JogoErro):
        pvp.desafiar(b.id, a.username, cb.id)


def test_defensor_nao_ve_criatura_do_desafiante(app):
    a, b, ca, _ = _duelo()
    pvp.desafiar(a.id, b.username, ca.id)
    recebido = pvp.minhas_batalhas(b.id)["recebidos"][0]
    assert recebido["criatura_desafiante"] is None
    assert pvp.minhas_batalhas(a.id)["enviados"][0]["criatura_desafiante"]["key"] == "seixo"


def test_desafio_expirado_resolve_sozinho(app):
    a, b, ca, cb = _duelo()
    pvp.desafiar(a.id, b.username, ca.id)
    batalha = _db.session.query(GameBattle).filter_by(desafiante_id=a.id).one()
    batalha.created_at = now_br() - timedelta(hours=25)
    _db.session.commit()
    assert pvp.expirar_pendentes(Dados(1, 6)) == 1
    _db.session.refresh(batalha)
    assert batalha.status == "expirada" and batalha.criatura_desafiado == cb.id
    assert batalha.vencedor_id == b.id


def test_wo_quando_defensor_ficou_sem_criatura(app):
    a, b, ca, cb = _duelo()
    pvp.desafiar(a.id, b.username, ca.id)
    cb.desmaiada = True
    batalha = _db.session.query(GameBattle).filter_by(desafiante_id=a.id).one()
    batalha.created_at = now_br() - timedelta(hours=25)
    _db.session.commit()
    pvp.expirar_pendentes(Dados())
    _db.session.refresh(batalha)
    assert batalha.vencedor_id == a.id and "W.O." in batalha.detalhe


def test_rolar_avisa_oponentes_na_casa(app):
    a, b = _user(), _user()
    _em(a, 20)
    _em(b, 21)                                        # 21 = cidade (não move o peão)
    res = motor.rolar(a.id, Dados(1))
    assert b.username in res["oponentes"]


def test_feed_registra_captura(app):
    a, b = _user(), _user()
    motor.rolar(a.id, Dados(1))
    motor.capturar(a.id, rng=Dados(2))
    textos = [f["texto"] for f in social.feed(1, excluir_user=b.id) if f["username"] == a.username]
    assert any("capturou" in t for t in textos)


# ── páginas ────────────────────────────────────────────────────────────────

def _login(client, uid):
    from flask import g
    g.pop("_login_user", None)
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_paginas_publicas(client):
    assert client.get("/jornada/").status_code == 200
    assert client.get("/jornada/hall-da-fama").status_code == 200
    assert client.get("/jornada/api/mapa").json["ok"]


def test_paginas_logado(client):
    u = _user()
    outro = _user()
    _login(client, u.id)
    for url in ("/jornada/", "/jornada/jogar", "/jornada/ranking", "/jornada/ranking?aba=global",
                "/jornada/time", "/jornada/descobertas", "/jornada/hall-da-fama",
                f"/jornada/treinador/{outro.username}", f"/jornada/treinador/{u.username}"):
        assert client.get(url).status_code == 200, url
    assert client.get("/jornada/eu").status_code == 302
    est = client.get("/jornada/api/estado?desde=0").json
    assert est["ok"] and "feed" in est and "vizinhos" in est
    assert client.get("/jornada/treinador/naoexiste_xyz").status_code == 404


def test_api_pvp(client):
    a, b, ca, cb = _duelo()
    _login(client, a.id)
    r = client.post("/jornada/api/pvp/desafiar", json={"alvo": b.username, "criatura": ca.id})
    assert r.status_code == 200 and r.json["ok"]
    bid = r.json["resultado"]["batalha"]
    _login(client, b.id)
    r = client.post(f"/jornada/api/pvp/{bid}/responder", json={"criatura": cb.id})
    assert r.status_code == 200 and r.json["resultado"]["status"] == "resolvida"
    r = client.post(f"/jornada/api/pvp/{bid}/responder", json={"criatura": cb.id})
    assert r.status_code in (404, 409)
