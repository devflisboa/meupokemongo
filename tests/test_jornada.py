"""Jornada (#27) — regras do motor (docs/SPEC-JORNADA.md §5) e API."""
import uuid
from datetime import timedelta

import pytest

from app.config import now_br
from app.extensions import db as _db
from app.models.jornada import GameCreature, GameEscape, GameItem, GamePlayer, GameTurn
from app.models.user import User
from app.services.jornada import motor
from app.services.jornada.conteudo import carregar


class Dados:
    """RNG roteirizado: randint devolve a sequência dada; choice/choices pegam o primeiro."""

    def __init__(self, *valores, itens=None):
        self.valores = list(valores)
        self.itens = list(itens or [])

    def randint(self, a, b):
        v = self.valores.pop(0)
        assert a <= v <= b
        return v

    def choice(self, seq):
        return seq[0]

    def choices(self, keys, weights=None, k=1):
        return [self.itens.pop(0) if self.itens else keys[0] for _ in range(k)]

    def shuffle(self, seq):
        pass


@pytest.fixture(autouse=True)
def _sem_login_vazando(app):
    """O app_context da sessão de testes é compartilhado: não deixar usuário logado em `g`."""
    yield
    from flask import g
    g.pop("_login_user", None)


@pytest.fixture()
def uid(app):
    nome = "e2e_" + uuid.uuid4().hex[:8]
    u = User(username=nome, email=f"{nome}@x.com")
    u.set_password("x")
    _db.session.add(u)
    _db.session.commit()
    return u.id


def _p(uid) -> GamePlayer:
    return motor.obter_jogador(uid)


def _por_em(uid, casa, **kw):
    p = _p(uid)
    p.posicao = casa
    p.acao_pendente = None
    for k, v in kw.items():
        setattr(p, k, v)
    _db.session.commit()


def _dar(uid, item, qtd):
    _p(uid)                                          # garante o jogador (e os itens iniciais) antes
    i = _db.session.get(GameItem, (uid, item))
    if i:
        i.qtd = qtd
    else:
        _db.session.add(GameItem(user_id=uid, item_key=item, qtd=qtd))
    _db.session.commit()


def _capturar_n(uid, n, estagio=1):
    """Dá n criaturas ao jogador (time primeiro), sem passar pelo dado."""
    fase = carregar().fase(1)
    keys = [k for k, c in sorted(fase.criaturas.items()) if c["estagio"] == estagio][:n]
    for i, k in enumerate(keys, start=1):
        _db.session.add(GameCreature(user_id=uid, creature_key=k, fase=1, estagio=estagio, volta=1,
                                     slot=i if i <= 6 else None))
    _db.session.commit()
    return keys


# ── conteúdo ───────────────────────────────────────────────────────────────

def test_conteudo_fase1_valido():
    fase = carregar().fase(1)
    assert len(fase.casas) == 73
    assert len(fase.criaturas) == 99
    linhas = {}
    for c in fase.criaturas.values():
        linhas.setdefault(c["linha"], set()).add(c["estagio"])
        assert len(c["captura"]) == (2 if c["estagio"] == 1 else 1)
    assert all(v == {1, 2, 3} for v in linhas.values())
    tipos = [c["tipo"] for c in fase.casas]
    assert tipos.count("captura") == 33 and tipos.count("ginasio") == 7


# ── início, energia, sequência ─────────────────────────────────────────────

def test_novo_jogador(app, uid):
    e = motor.estado(uid)
    assert e["posicao"] == 0 and e["volta"] == 1 and e["pp"] == 0
    assert e["energia"] == 6
    assert e["itens"] == {"isca": 2}


def test_sem_energia_bloqueia(app, uid):
    _por_em(uid, 0, energia=0, energia_dia=now_br().date())
    with pytest.raises(motor.JogoErro) as exc:
        motor.rolar(uid, Dados(1))
    assert exc.value.status == 409


def test_recarga_diaria_acumula_ate_maximo(app, uid):
    _por_em(uid, 0, energia=0, energia_dia=now_br().date() - timedelta(days=1))
    assert motor.estado(uid)["energia"] == 6
    _por_em(uid, 0, energia=0, energia_dia=now_br().date() - timedelta(days=5))
    assert motor.estado(uid)["energia"] == 12


def test_sequencia_de_dias(app, uid):
    ontem = now_br().date() - timedelta(days=1)
    _por_em(uid, 4, sequencia_dias=6, ultimo_dia_jogado=ontem)
    res = motor.rolar(uid, Dados(1))                 # casa 5 = bônus
    assert _p(uid).sequencia_dias == 7
    assert res["premio_sequencia"]["item"] == "rede"


# ── movimento e casas ──────────────────────────────────────────────────────

def test_rolar_gasta_energia_e_log(app, uid):
    motor.estado(uid)
    res = motor.rolar(uid, Dados(4))                 # casa 4 = captura
    p = _p(uid)
    assert res["dado"] == 4 and p.posicao == 4 and p.energia == 5
    assert _db.session.query(GameTurn).filter_by(user_id=uid, tipo="movimento").count() == 1


def test_acao_pendente_bloqueia_rolar(app, uid):
    motor.rolar(uid, Dados(1))                       # casa 1 = captura
    with pytest.raises(motor.JogoErro):
        motor.rolar(uid, Dados(1))


def test_bonus(app, uid):
    _por_em(uid, 3)
    res = motor.rolar(uid, Dados(2))                 # casa 5
    assert res["bonus"] == 50 and _p(uid).pp == 50


def test_cidade_da_itens_e_cura(app, uid):
    _capturar_n(uid, 1)
    gc = _db.session.query(GameCreature).filter_by(user_id=uid).first()
    gc.desmaiada = True
    _db.session.commit()
    _por_em(uid, 1)
    res = motor.rolar(uid, Dados(1, itens=["tonico", "rede"]))   # casa 2 = cidade
    assert res["itens"]["ganhos"] == ["tonico", "rede"]
    assert res["curadas"] == 1
    assert motor.estado(uid)["itens"] == {"isca": 2, "tonico": 1, "rede": 1}


def test_limite_da_mao(app, uid):
    _dar(uid, "isca", 10)
    _por_em(uid, 1)
    res = motor.rolar(uid, Dados(1, itens=["rede", "rede"]))
    assert res["itens"]["descartados"] == ["rede", "rede"]


def test_parada_obrigatoria_no_desafio(app, uid):
    _por_em(uid, 69, pp=0)
    res = motor.rolar(uid, Dados(6))
    assert res["para"] == 71                         # não passa do Desafio


def test_evento_mover_nao_resolve_destino(app, uid):
    _por_em(uid, 64, baralho_eventos=["atalho"])     # atalho = +3
    res = motor.rolar(uid, Dados(2))                 # 66 = evento → 69 (cidade NÃO resolvida)
    assert res["evento"]["key"] == "atalho"
    assert res["posicao_final"] == 69 and "itens" not in res


def test_baralho_de_eventos_reembaralha(app, uid):
    _por_em(uid, 1, baralho_eventos=[])
    res = motor.rolar(uid, Dados(2))                 # casa 3 = evento, baralho vazio
    assert res["evento"]["key"] == carregar().fase(1).eventos[0]["key"]
    assert len(_p(uid).baralho_eventos) == 11


# ── captura ────────────────────────────────────────────────────────────────

def test_captura_acerta(app, uid):
    res = motor.rolar(uid, Dados(1))                 # casa 1 → Brotim [2, 5]
    assert res["criatura"]["key"] == "brotim"
    cap = motor.capturar(uid, rng=Dados(5))
    assert cap["capturou"] and cap["foi_para"] == "time"
    p = _p(uid)
    assert p.pp == 15 and p.acao_pendente is None


def test_captura_erra_foge_na_volta(app, uid):
    motor.rolar(uid, Dados(1))
    cap = motor.capturar(uid, rng=Dados(3))
    assert not cap["capturou"]
    assert _db.session.get(GameEscape, (uid, "brotim", 1))
    _por_em(uid, 0)
    res = motor.rolar(uid, Dados(1))
    assert res["criatura"]["key"] != "brotim"        # fugiu nesta volta → não reaparece


def test_nunca_repete_criatura_que_tem(app, uid):
    motor.rolar(uid, Dados(1))
    motor.capturar(uid, rng=Dados(2))
    _por_em(uid, 0)
    res = motor.rolar(uid, Dados(1))
    tem = {c.creature_key for c in _db.session.query(GameCreature).filter_by(user_id=uid)}
    assert res["criatura"]["key"] not in tem


def test_isca_so_gasta_quando_ajuda(app, uid):
    motor.rolar(uid, Dados(1))                       # Brotim [2, 5]
    cap = motor.capturar(uid, item="isca", rng=Dados(3))   # 3+1=4: não ajuda
    assert not cap["capturou"] and cap["item_usado"] is None
    assert motor.estado(uid)["itens"]["isca"] == 2
    _por_em(uid, 3)
    motor.rolar(uid, Dados(1))                       # casa 4 → Pardalito [1, 4]
    cap = motor.capturar(uid, item="isca", rng=Dados(3))   # 3+1=4 ✓
    assert cap["capturou"] and cap["item_usado"] == "isca"
    assert motor.estado(uid)["itens"]["isca"] == 1


def test_rede_menos_um(app, uid):
    _dar(uid, "rede", 1)
    motor.rolar(uid, Dados(1))                       # Brotim [2, 5]
    cap = motor.capturar(uid, item="rede", rng=Dados(6))   # 6−1=5 ✓
    assert cap["capturou"] and cap["ajuste"].startswith("−1")


def test_amuleto_garante(app, uid):
    _dar(uid, "amuleto", 1)
    motor.rolar(uid, Dados(1))
    cap = motor.capturar(uid, item="amuleto", rng=Dados())
    assert cap["capturou"] and cap["dado"] is None


def test_item_que_nao_tem(app, uid):
    motor.rolar(uid, Dados(1))
    with pytest.raises(motor.JogoErro):
        motor.capturar(uid, item="amuleto", rng=Dados(1))


def test_pular_captura_faz_fugir(app, uid):
    motor.rolar(uid, Dados(1))
    motor.pular(uid)
    assert _db.session.get(GameEscape, (uid, "brotim", 1))
    assert _p(uid).acao_pendente is None


def test_setimo_vai_para_reserva(app, uid):
    _capturar_n(uid, 6)
    motor.rolar(uid, Dados(1))
    cap = motor.capturar(uid, rng=Dados(2))
    assert cap["foi_para"] == "reserva"


def test_sem_criatura_disponivel_vira_pp(app, uid):
    fase = carregar().fase(1)
    for k, c in fase.criaturas.items():
        _db.session.add(GameCreature(user_id=uid, creature_key=k, fase=1, estagio=c["estagio"], volta=1))
    _db.session.commit()
    res = motor.rolar(uid, Dados(1))
    assert res["sem_criatura"] and _p(uid).pp == 10


# ── voltas ─────────────────────────────────────────────────────────────────

def test_fim_sem_requisitos_comeca_nova_volta(app, uid):
    _por_em(uid, 70, pp=0)
    res = motor.rolar(uid, Dados(1))
    p = _p(uid)
    assert res["nova_volta"] == 2 and p.volta == 2 and p.posicao == 0


def test_segunda_volta_sorteia_estagio_2_com_um_numero(app, uid):
    _por_em(uid, 0, volta=2)
    res = motor.rolar(uid, Dados(1))
    cr = res["criatura"]
    assert cr["estagio"] == 2 and cr["key"] == "brotim-2" and len(cr["captura"]) == 1


# ── ginásio ────────────────────────────────────────────────────────────────

def test_ginasio_vitoria_e_depois_vira_cidade(app, uid):
    _capturar_n(uid, 1)
    _por_em(uid, 16, pp=0)
    res = motor.rolar(uid, Dados(1, 6, 1))           # casa 17; jogador 6+atk vs líder 1+1
    assert res["ginasio"]["venceu"]
    p = _p(uid)
    assert "vento" in p.insignias and p.pp == 40
    _por_em(uid, 16)
    res = motor.rolar(uid, Dados(1))
    assert res["ginasio"]["ja_vencido"] and "itens" in res


def test_ginasio_sem_time(app, uid):
    _por_em(uid, 16)
    res = motor.rolar(uid, Dados(1))
    assert res["ginasio"]["sem_time"] and not res["ginasio"]["venceu"]


# ── desafio final ──────────────────────────────────────────────────────────

def _no_desafio(uid):
    _capturar_n(uid, 6)
    _por_em(uid, 70, pp=500)
    res = motor.rolar(uid, Dados(1))
    assert res["desafio"] == "disponivel"
    return [c.id for c in _db.session.query(GameCreature).filter_by(user_id=uid).order_by(GameCreature.slot)][:3]


def test_desafio_vitoria(app, uid):
    ids = _no_desafio(uid)
    res = motor.desafio(uid, ids, rng=Dados(6, 1, 6, 1))
    assert res["venceu"] and len(res["rodadas"]) == 2
    p = _p(uid)
    assert p.posicao == 72 and p.titulo_fase1_em is not None
    with pytest.raises(motor.JogoErro):
        motor.rolar(uid, Dados(1))                   # fase concluída


def test_desafio_derrota_volta_66(app, uid):
    ids = _no_desafio(uid)
    res = motor.desafio(uid, ids, rng=Dados(1, 6, 1, 6))
    assert not res["venceu"] and _p(uid).posicao == 66


def test_desafio_exige_tres_diferentes(app, uid):
    ids = _no_desafio(uid)
    with pytest.raises(motor.JogoErro):
        motor.desafio(uid, [ids[0], ids[0], ids[1]], rng=Dados())


# ── time e itens ───────────────────────────────────────────────────────────

def test_definir_time(app, uid):
    _capturar_n(uid, 7)
    ids = [c.id for c in _db.session.query(GameCreature).filter_by(user_id=uid).order_by(GameCreature.id)]
    motor.definir_time(uid, [ids[6], ids[0]])
    e = motor.estado(uid)
    assert [c["id"] for c in e["time"]] == [ids[6], ids[0]]
    assert len(e["reserva"]) == 5


def test_tonico_cura(app, uid):
    _capturar_n(uid, 1)
    gc = _db.session.query(GameCreature).filter_by(user_id=uid).first()
    gc.desmaiada = True
    _db.session.commit()
    _dar(uid, "tonico", 1)
    motor.usar_item(uid, "tonico", gc.id)
    assert not _db.session.get(GameCreature, gc.id).desmaiada


# ── API ────────────────────────────────────────────────────────────────────

def _login(client, uid):
    from flask import g
    g.pop("_login_user", None)
    with client.session_transaction() as s:
        s["_user_id"] = str(uid)
        s["_fresh"] = True


def test_api_exige_login(client):
    assert client.post("/jornada/api/rolar").status_code in (302, 401)


def test_api_fluxo(client, uid):
    _login(client, uid)
    assert client.get("/jornada/jogar").status_code == 200
    r = client.post("/jornada/api/rolar")
    assert r.status_code == 200 and r.json["ok"]
    assert r.json["estado"]["energia"] == 5
    if r.json["estado"]["acao_pendente"]:
        r2 = client.post("/jornada/api/rolar")
        assert r2.status_code == 409 and not r2.json["ok"]
    assert client.get("/jornada/time").status_code == 200
    assert client.get("/jornada/api/estado").json["ok"]
