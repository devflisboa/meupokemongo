"""Motor de regras da Jornada (#27) — ver docs/SPEC-JORNADA.md §5.

Princípios:
- Todo sorteio acontece aqui, no servidor (secrets.SystemRandom). O front só anima.
- Toda ação trava a linha do jogador (SELECT ... FOR UPDATE) — evita rolagem dupla.
- Uma ação só é aceita se combinar com a `acao_pendente` atual.
- Toda ação gera uma linha em game_turns.
- Nenhum nome de criatura/casa no código: tudo vem de conteudo.carregar().

`rng` é injetável para os testes (qualquer objeto com randint/choice/choices/shuffle).
"""
from __future__ import annotations

import secrets
from datetime import date

from sqlalchemy.exc import IntegrityError

from ...config import now_br
from ...extensions import db
from ...models.jornada import (
    GameCreature, GameDiscovery, GameEscape, GameItem, GamePlayer, GameTurn,
)
from .conteudo import carregar

ITENS_DE_CAPTURA = {"isca", "rede", "amuleto"}
TAMANHO_TIME = 6


class JogoErro(Exception):
    """Ação inválida no estado atual. `status` vira o HTTP status da API."""

    def __init__(self, mensagem: str, status: int = 400):
        super().__init__(mensagem)
        self.mensagem = mensagem
        self.status = status


def _rng(rng):
    return rng or secrets.SystemRandom()


def _hoje() -> date:
    return now_br().date()


# ── jogador ────────────────────────────────────────────────────────────────

def _novo_jogador(user_id: int) -> GamePlayer:
    c = carregar()
    p = GamePlayer(
        user_id=user_id, fase=1, posicao=0, volta=1, pp=0,
        energia=c.jogo["inicio"]["energia"], energia_dia=_hoje(),
        sequencia_dias=0, insignias=[], efeitos={}, baralho_eventos=[],
        last_seen=now_br(),
    )
    db.session.add(p)
    for key, qtd in c.jogo["inicio"].get("itens", {}).items():
        db.session.add(GameItem(user_id=user_id, item_key=key, qtd=qtd))
    return p


def obter_jogador(user_id: int, travar: bool = False) -> GamePlayer:
    """Busca (e cria na primeira vez) o jogador. `travar` = SELECT ... FOR UPDATE."""
    q = db.session.query(GamePlayer).filter_by(user_id=user_id)
    if travar:
        q = q.with_for_update()
    p = q.one_or_none()
    if p is None:
        try:
            p = _novo_jogador(user_id)
            db.session.flush()
        except IntegrityError:          # outra thread criou ao mesmo tempo
            db.session.rollback()
            p = q.one()
    return p


def _recarregar_energia(p: GamePlayer, dia: date) -> None:
    cfg = carregar().jogo["energia"]
    if p.energia_dia is None or p.energia_dia < dia:
        dias = (dia - p.energia_dia).days if p.energia_dia else 1
        p.energia = min(cfg["maximo"], p.energia + cfg["por_dia"] * dias)
        p.energia_dia = dia


def _atualizar_sequencia(p: GamePlayer, dia: date, res: dict) -> None:
    if p.ultimo_dia_jogado == dia:
        return
    if p.ultimo_dia_jogado is not None and (dia - p.ultimo_dia_jogado).days == 1:
        p.sequencia_dias += 1
    else:
        p.sequencia_dias = 1
    p.ultimo_dia_jogado = dia
    regras = carregar().jogo["regras"]
    if p.sequencia_dias % regras["sequencia_premio_dias"] == 0:
        item = regras["sequencia_premio_item"]
        if _dar_item(p.user_id, item):
            res["premio_sequencia"] = {"dias": p.sequencia_dias, "item": item}


# ── itens ──────────────────────────────────────────────────────────────────

def _itens(user_id: int) -> dict[str, GameItem]:
    return {i.item_key: i for i in db.session.query(GameItem).filter_by(user_id=user_id)}


def _qtd(user_id: int, key: str) -> int:
    i = db.session.get(GameItem, (user_id, key))
    return i.qtd if i else 0


def _dar_item(user_id: int, key: str) -> bool:
    """Adiciona 1 item respeitando o limite da mão. Devolve False se descartou."""
    total = sum(i.qtd for i in _itens(user_id).values())
    if total >= carregar().limite_mao:
        return False
    i = db.session.get(GameItem, (user_id, key))
    if i is None:
        db.session.add(GameItem(user_id=user_id, item_key=key, qtd=1))
    else:
        i.qtd += 1
    db.session.flush()
    return True


def _gastar_item(user_id: int, key: str) -> None:
    i = db.session.get(GameItem, (user_id, key))
    if not i or i.qtd <= 0:
        raise JogoErro("Você não tem esse item.")
    i.qtd -= 1


def _sortear_itens(user_id: int, n: int, rng) -> dict:
    c = carregar()
    keys = list(c.itens)
    pesos = [c.itens[k]["peso"] for k in keys]
    ganhos, descartados = [], []
    for key in rng.choices(keys, weights=pesos, k=n):
        (ganhos if _dar_item(user_id, key) else descartados).append(key)
    return {"ganhos": ganhos, "descartados": descartados}


# ── criaturas ──────────────────────────────────────────────────────────────

def _minhas_criaturas(user_id: int) -> list[GameCreature]:
    return db.session.query(GameCreature).filter_by(user_id=user_id).order_by(GameCreature.id).all()


def _time(user_id: int) -> list[GameCreature]:
    return sorted((c for c in _minhas_criaturas(user_id) if c.slot), key=lambda c: c.slot)


def _proximo_slot(user_id: int) -> int | None:
    usados = {c.slot for c in _time(user_id)}
    return next((s for s in range(1, TAMANHO_TIME + 1) if s not in usados), None)


def _curar_todas(user_id: int) -> int:
    n = 0
    for c in _minhas_criaturas(user_id):
        if c.desmaiada:
            c.desmaiada = False
            n += 1
    return n


def _ataque(fase, gc: GameCreature) -> int:
    return fase.criaturas[gc.creature_key]["ataque"]


def criatura_publica(cr: dict) -> dict:
    tipos = carregar().jogo["tipos"]
    t = tipos.get(cr["tipo"], {})
    return {
        "key": cr["key"], "nome": cr["nome"], "tipo": cr["tipo"], "estagio": cr["estagio"],
        "ataque": cr["ataque"], "pp": cr["pp"], "captura": cr["captura"],
        "cor": t.get("cor", "#999"), "emoji": t.get("emoji", "❔"),
    }


# ── log ────────────────────────────────────────────────────────────────────

def _log(p: GamePlayer, tipo: str, res: dict, pp_antes: int,
         dado: int | None = None, de: int | None = None, para: int | None = None) -> None:
    db.session.add(GameTurn(
        user_id=p.user_id, fase=p.fase, tipo=tipo, dado=dado, de=de, para=para,
        resultado=res, pp_delta=p.pp - pp_antes,
    ))


# ── casas ──────────────────────────────────────────────────────────────────

def _escolher_criatura(p: GamePlayer, fase, casa: dict, rng) -> dict | None:
    """Regra de ouro: nunca sorteia criatura que o jogador já tem nem que fugiu nesta volta."""
    tem = {c.creature_key for c in _minhas_criaturas(p.user_id)}
    fugiu = {e.creature_key for e in db.session.query(GameEscape).filter_by(user_id=p.user_id, volta=p.volta)}
    for estagio in range(min(p.volta, 3), 4):
        cands = sorted(
            (c for c in fase.criaturas.values()
             if c["estagio"] == estagio and c["key"] not in tem and c["key"] not in fugiu),
            key=lambda c: c["key"],
        )
        if not cands:
            continue
        # preferência: mesma linha do habitat da casa → mesmo local → qualquer
        linha = [c for c in cands if c["linha"] == casa["habitat"]]
        if linha:
            return linha[0]
        local = [c for c in cands if c["habitat"] == casa["local"]]
        return rng.choice(local or cands)
    return None


def _casa_captura(p, fase, casa, rng, res) -> None:
    cr = _escolher_criatura(p, fase, casa, rng)
    if cr is None:
        p.pp += carregar().jogo["regras"]["sem_criatura_pp"]
        res["sem_criatura"] = True
        return
    if db.session.get(GameDiscovery, cr["key"]) is None:
        db.session.add(GameDiscovery(creature_key=cr["key"], discovered_by=p.user_id))
        res["descoberta"] = True
    p.acao_pendente = {"tipo": "captura", "criatura": cr["key"], "casa": casa["casa"]}
    res["criatura"] = criatura_publica(cr)


def _casa_cidade(p, fase, casa, rng, res) -> None:
    res["itens"] = _sortear_itens(p.user_id, carregar().jogo["regras"]["cidade_itens"], rng)
    res["curadas"] = _curar_todas(p.user_id)


def _casa_ginasio(p, fase, casa, rng, res) -> None:
    g = fase.ginasios[casa["ginasio"]]
    info = {"key": g["key"], "nome": g["nome"], "lider": g["lider"], "nivel": g["nivel"]}
    if g["key"] in (p.insignias or []):
        info["ja_vencido"] = True
        res["ginasio"] = info
        _casa_cidade(p, fase, casa, rng, res)
        return
    saudaveis = [c for c in _time(p.user_id) if not c.desmaiada]
    if not saudaveis:
        info.update(venceu=False, sem_time=True)
        res["ginasio"] = info
        return
    melhor = max(saudaveis, key=lambda c: _ataque(fase, c))
    d_jog, d_lid = rng.randint(1, 6), rng.randint(1, 6)
    total_jog = d_jog + _ataque(fase, melhor)
    total_lid = d_lid + g["nivel"]
    venceu = total_jog >= total_lid          # empate = vitória do jogador
    info.update(
        criatura=fase.criaturas[melhor.creature_key]["nome"],
        dado_jogador=d_jog, total_jogador=total_jog, dado_lider=d_lid, total_lider=total_lid,
        venceu=venceu,
    )
    if venceu:
        regras = carregar().jogo["regras"]
        p.insignias = [*(p.insignias or []), g["key"]]
        p.pp += regras["ginasio_pp"]
        info["itens"] = _sortear_itens(p.user_id, regras["ginasio_itens"], rng)
    res["ginasio"] = info


def _casa_evento(p, fase, casa, rng, res) -> None:
    baralho = list(p.baralho_eventos or [])
    if not baralho:
        baralho = [e["key"] for e in fase.eventos]
        rng.shuffle(baralho)
    key, p.baralho_eventos = baralho[0], baralho[1:]
    ev = next(e for e in fase.eventos if e["key"] == key)
    info = {"key": ev["key"], "nome": ev["nome"], "efeito": ev["efeito"], "valor": ev["valor"]}
    efeito, v = ev["efeito"], ev["valor"]
    if efeito == "mover":
        # destino NÃO é resolvido (evita cadeias) e nunca pula o Desafio
        limite = fase.regiao["casa_desafio"] - 1
        info["de"] = p.posicao
        p.posicao = max(0, min(limite, p.posicao + v))
        info["para"] = p.posicao
    elif efeito == "pp":
        p.pp = max(0, p.pp + v)
    elif efeito == "item":
        info["itens"] = _sortear_itens(p.user_id, v, rng)
    elif efeito == "energia":
        p.energia = min(carregar().jogo["energia"]["maximo"], p.energia + v)
    elif efeito == "curar":
        info["curadas"] = _curar_todas(p.user_id)
    elif efeito == "sorte":
        p.efeitos = {**(p.efeitos or {}), "sorte": 1}
    elif efeito == "perde_item":
        unidades = [k for k, i in sorted(_itens(p.user_id).items()) for _ in range(i.qtd)]
        if unidades:
            perdido = rng.choice(unidades)
            _gastar_item(p.user_id, perdido)
            info["perdeu"] = perdido
    res["evento"] = info


def requisitos(p: GamePlayer, fase) -> dict:
    req = fase.regiao["requisitos"]
    no_time = len(_time(p.user_id))
    return {
        "pp": req["pp"], "time": req["time"], "pp_atual": p.pp, "time_atual": no_time,
        "ok": p.pp >= req["pp"] and no_time >= req["time"],
    }


def _casa_desafio(p, fase, casa, rng, res) -> None:
    r = requisitos(p, fase)
    res["requisitos"] = r
    if r["ok"]:
        _curar_todas(p.user_id)               # Centro do Pico: ninguém trava com time desmaiado
        p.acao_pendente = {"tipo": "desafio"}
        res["desafio"] = "disponivel"
    else:
        p.volta += 1
        p.posicao = 0
        res["nova_volta"] = p.volta


_HANDLERS = {
    "captura": _casa_captura, "cidade": _casa_cidade, "ginasio": _casa_ginasio,
    "evento": _casa_evento, "desafio": _casa_desafio,
}


def _resolver_casa(p, fase, rng, res) -> None:
    casa = fase.casas[p.posicao]
    res["casa"] = {"casa": casa["casa"], "tipo": casa["tipo"], "local": fase.local_da_casa(p.posicao)["nome"]}
    if casa["tipo"] == "bonus":
        p.pp += casa["pp"]
        res["bonus"] = casa["pp"]
    elif casa["tipo"] in _HANDLERS:
        _HANDLERS[casa["tipo"]](p, fase, casa, rng, res)


# ── ações (API) ────────────────────────────────────────────────────────────

def rolar(user_id: int, rng=None) -> dict:
    rng = _rng(rng)
    p = obter_jogador(user_id, travar=True)
    fase = carregar().fase(p.fase)
    dia = _hoje()
    _recarregar_energia(p, dia)
    if p.acao_pendente:
        raise JogoErro("Resolva a ação pendente antes de rolar o dado.", 409)
    if p.posicao >= fase.regiao["casa_final"]:
        raise JogoErro("Você já concluiu esta fase. A próxima região chega em breve!", 409)
    if p.energia <= 0:
        raise JogoErro("Sem energia por hoje. A recarga acontece à meia-noite.", 409)

    pp_antes, de = p.pp, p.posicao
    p.energia -= 1
    res: dict = {}
    _atualizar_sequencia(p, dia, res)
    dado = rng.randint(1, 6)
    p.posicao = min(de + dado, fase.regiao["casa_desafio"])   # parada obrigatória no Desafio
    res.update(dado=dado, de=de, para=p.posicao)
    _resolver_casa(p, fase, rng, res)
    res["posicao_final"] = p.posicao     # difere de "para" após evento de mover ou nova volta
    from .social import no_mesmo_lugar
    res["oponentes"] = [o["username"] for o in no_mesmo_lugar(p)] if p.posicao < fase.regiao["casa_final"] else []
    res["pp_ganho"] = p.pp - pp_antes
    _log(p, "movimento", res, pp_antes, dado=dado, de=de, para=p.posicao)
    db.session.commit()
    return res


def capturar(user_id: int, item: str | None = None, rng=None) -> dict:
    rng = _rng(rng)
    p = obter_jogador(user_id, travar=True)
    pend = p.acao_pendente or {}
    if pend.get("tipo") != "captura":
        raise JogoErro("Não há criatura para capturar agora.", 409)
    if item and item not in ITENS_DE_CAPTURA:
        raise JogoErro("Esse item não ajuda na captura.")
    if item and _qtd(user_id, item) <= 0:
        raise JogoErro("Você não tem esse item.")

    fase = carregar().fase(p.fase)
    cr = fase.criaturas[pend["criatura"]]
    nums = cr["captura"]
    pp_antes = p.pp
    res: dict = {"criatura": criatura_publica(cr), "item_usado": None, "ajuste": None}

    sorte = (p.efeitos or {}).get("sorte", 0) > 0
    if sorte:                                   # vale só para a próxima tentativa
        p.efeitos = {**p.efeitos, "sorte": 0}

    if item == "amuleto":
        _gastar_item(user_id, "amuleto")
        ok, dado = True, None
        res["item_usado"] = "amuleto"
    else:
        dado = rng.randint(1, 6)
        ok = dado in nums
        if not ok and sorte and dado + 1 in nums:
            ok, res["ajuste"] = True, "+1 (dia de sorte)"
        if not ok and item == "isca" and dado + 1 in nums:
            _gastar_item(user_id, "isca")
            ok, res["ajuste"], res["item_usado"] = True, "+1 (isca)", "isca"
        if not ok and item == "rede" and (dado + 1 in nums or dado - 1 in nums):
            _gastar_item(user_id, "rede")
            ajuste = "+1" if dado + 1 in nums else "−1"
            ok, res["ajuste"], res["item_usado"] = True, f"{ajuste} (rede)", "rede"
    res["dado"] = dado

    if ok:
        slot = _proximo_slot(user_id)
        db.session.add(GameCreature(
            user_id=user_id, creature_key=cr["key"], fase=p.fase, estagio=cr["estagio"],
            volta=p.volta, slot=slot,
        ))
        p.pp += cr["pp"]
        res.update(capturou=True, foi_para="time" if slot else "reserva")
    else:
        db.session.merge(GameEscape(user_id=user_id, creature_key=cr["key"], volta=p.volta))
        res["capturou"] = False
    p.acao_pendente = None
    res["pp_ganho"] = p.pp - pp_antes
    _log(p, "captura", res, pp_antes, dado=dado)
    db.session.commit()
    return res


def pular(user_id: int) -> dict:
    """Desiste da ação pendente. Captura: a criatura foge. Desafio: volta para a casa de derrota."""
    p = obter_jogador(user_id, travar=True)
    pend = p.acao_pendente or {}
    fase = carregar().fase(p.fase)
    res: dict = {}
    if pend.get("tipo") == "captura":
        db.session.merge(GameEscape(user_id=user_id, creature_key=pend["criatura"], volta=p.volta))
        res["fugiu"] = pend["criatura"]
    elif pend.get("tipo") == "desafio":
        p.posicao = fase.regiao["desafio"]["casa_derrota"]
        res["recuou_para"] = p.posicao
    else:
        raise JogoErro("Não há nada para pular.", 409)
    p.acao_pendente = None
    _log(p, "pular", res, p.pp)
    db.session.commit()
    return res


def usar_item(user_id: int, item: str, criatura_id: int | None = None) -> dict:
    p = obter_jogador(user_id, travar=True)
    if item in ITENS_DE_CAPTURA:
        raise JogoErro("Esse item é usado no momento da captura.")
    if item not in carregar().itens:
        raise JogoErro("Item desconhecido.")
    if _qtd(user_id, item) <= 0:
        raise JogoErro("Você não tem esse item.")
    res: dict = {"item": item}
    if item == "tonico":
        gc = db.session.get(GameCreature, criatura_id) if criatura_id else None
        if not gc or gc.user_id != user_id:
            raise JogoErro("Escolha uma criatura sua.")
        if not gc.desmaiada:
            raise JogoErro("Essa criatura não está desmaiada.")
        gc.desmaiada = False
        res["curadas"] = 1
    elif item == "elixir":
        if not any(c.desmaiada for c in _minhas_criaturas(user_id)):
            raise JogoErro("Nenhuma criatura desmaiada.")
        res["curadas"] = _curar_todas(user_id)
    _gastar_item(user_id, item)
    _log(p, "item", res, p.pp)
    db.session.commit()
    return res


def definir_time(user_id: int, ids: list[int]) -> dict:
    p = obter_jogador(user_id, travar=True)
    if len(ids) > TAMANHO_TIME or len(set(ids)) != len(ids):
        raise JogoErro(f"O time tem até {TAMANHO_TIME} criaturas, sem repetir.")
    minhas = {c.id: c for c in _minhas_criaturas(user_id)}
    if any(i not in minhas for i in ids):
        raise JogoErro("Só criaturas suas podem entrar no time.")
    for c in minhas.values():
        c.slot = None
    db.session.flush()
    for slot, i in enumerate(ids, start=1):
        minhas[i].slot = slot
    _log(p, "time", {"time": ids}, p.pp)
    db.session.commit()
    return {"time": ids}


def desafio(user_id: int, criatura_ids: list[int], rng=None) -> dict:
    """Batalha final: melhor de 3, uma criatura diferente por rodada."""
    rng = _rng(rng)
    p = obter_jogador(user_id, travar=True)
    if (p.acao_pendente or {}).get("tipo") != "desafio":
        raise JogoErro("O desafio só acontece no topo da trilha.", 409)
    fase = carregar().fase(p.fase)
    cfg = fase.regiao["desafio"]
    rodadas = cfg["rodadas"]
    time = {c.id: c for c in _time(user_id) if not c.desmaiada}
    if len(criatura_ids) != rodadas or len(set(criatura_ids)) != rodadas or any(i not in time for i in criatura_ids):
        raise JogoErro(f"Escolha {rodadas} criaturas diferentes e saudáveis do seu time.")

    pp_antes = p.pp
    placar = {"jogador": 0, "chefe": 0}
    precisa = rodadas // 2 + 1
    historico = []
    for i in criatura_ids:
        gc = time[i]
        dj, dc = rng.randint(1, 6), rng.randint(1, 6)
        tj, tc = dj + _ataque(fase, gc), dc + cfg["nivel"]
        venceu = tj >= tc
        placar["jogador" if venceu else "chefe"] += 1
        historico.append({
            "criatura": fase.criaturas[gc.creature_key]["nome"], "dado_jogador": dj, "total_jogador": tj,
            "dado_chefe": dc, "total_chefe": tc, "venceu": venceu,
        })
        if max(placar.values()) >= precisa:
            break
    venceu = placar["jogador"] >= precisa
    p.acao_pendente = None
    if venceu:
        p.posicao = fase.regiao["casa_final"]
        p.titulo_fase1_em = now_br()
    else:
        p.posicao = cfg["casa_derrota"]
    res = {"rodadas": historico, "placar": placar, "venceu": venceu, "chefe": cfg["chefe"], "para": p.posicao}
    _log(p, "desafio", res, pp_antes)
    db.session.commit()
    return res


# ── leitura ────────────────────────────────────────────────────────────────

def estado(user_id: int) -> dict:
    """Snapshot completo para a tela. Também aplica a recarga diária e marca last_seen."""
    from .pvp import expirar_pendentes, minhas_batalhas
    from .social import no_mesmo_lugar
    expirar_pendentes()
    c = carregar()
    p = obter_jogador(user_id, travar=True)
    fase = c.fase(p.fase)
    _recarregar_energia(p, _hoje())
    p.last_seen = now_br()

    def gc_publica(gc: GameCreature) -> dict:
        d = criatura_publica(fase.criaturas[gc.creature_key])
        d.update(id=gc.id, slot=gc.slot, desmaiada=gc.desmaiada)
        return d

    criaturas = _minhas_criaturas(user_id)
    pend = p.acao_pendente
    if pend and pend.get("tipo") == "captura":
        pend = {**pend, "dados": criatura_publica(fase.criaturas[pend["criatura"]])}
    local = fase.local_da_casa(p.posicao)
    out = {
        "fase": p.fase, "regiao": fase.regiao["nome"], "posicao": p.posicao, "volta": p.volta,
        "local": local["nome"], "local_indice": fase.indice_local(p.posicao),
        "locais_total": len(fase.regiao["locais"]),
        "pp": p.pp, "energia": p.energia, "energia_max": c.jogo["energia"]["maximo"],
        "sequencia_dias": p.sequencia_dias, "insignias": p.insignias or [],
        "ginasios_total": len(fase.ginasios), "sorte": (p.efeitos or {}).get("sorte", 0) > 0,
        "acao_pendente": pend,
        "itens": {k: i.qtd for k, i in _itens(user_id).items() if i.qtd > 0},
        "time": [gc_publica(g) for g in sorted((g for g in criaturas if g.slot), key=lambda g: g.slot)],
        "reserva": [gc_publica(g) for g in criaturas if not g.slot],
        "capturadas": len(criaturas), "criaturas_total": len(fase.criaturas),
        "requisitos": requisitos(p, fase),
        "concluiu": p.posicao >= fase.regiao["casa_final"],
        "batalhas": minhas_batalhas(user_id),
        "aqui": [] if p.posicao >= fase.regiao["casa_final"] else no_mesmo_lugar(p),
    }
    db.session.commit()
    return out
