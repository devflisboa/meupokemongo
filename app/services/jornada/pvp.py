"""Jornada — Batalha PvP assíncrona (J3). Regras: SPEC-JORNADA.md §5.8.

Fluxo:
1. desafiar(): os dois parados na mesma casa; o desafiante escolhe a criatura (e se usa Isca).
2. responder(): o desafiado escolhe a dele quando entrar → resolve.
3. Sem resposta em 24 h → expirar_pendentes() resolve sozinho com a criatura mais forte dele.

Resolução: dado + ataque (+1 com Isca). Empate = defensor vence.
Vencedor: +30 PP e rouba até 2 itens aleatórios. Perdedor: a criatura usada desmaia.
"""
from __future__ import annotations

import secrets
from datetime import timedelta

from sqlalchemy import or_, and_

from ...config import now_br
from ...extensions import db
from ...models.jornada import GameBattle, GameCreature, GameItem, GamePlayer, GameTurn
from ...models.user import User
from .conteudo import carregar
from .motor import JogoErro, _dar_item, _gastar_item, _qtd, criatura_publica


def _cfg() -> dict:
    return carregar().jogo["pvp"]


def _travar(*user_ids: int) -> dict[int, GamePlayer]:
    """Trava as linhas dos jogadores sempre na mesma ordem (evita deadlock)."""
    out = {}
    for uid in sorted(set(user_ids)):
        p = db.session.query(GamePlayer).filter_by(user_id=uid).with_for_update().one_or_none()
        if p is None:
            raise JogoErro("Esse treinador ainda não começou a jornada.", 404)
        out[uid] = p
    return out


def _saudaveis(user_id: int) -> list[GameCreature]:
    return db.session.query(GameCreature).filter_by(user_id=user_id, desmaiada=False).all()


def _ataque(gc: GameCreature) -> int:
    return carregar().fase(gc.fase).criaturas[gc.creature_key]["ataque"]


def _mais_forte(user_id: int) -> GameCreature | None:
    s = _saudaveis(user_id)
    return max(s, key=lambda c: (_ataque(c), -c.id)) if s else None


def _batalha_recente(a: int, b: int):
    janela = now_br() - timedelta(hours=_cfg()["janela_horas"])
    par = or_(and_(GameBattle.desafiante_id == a, GameBattle.desafiado_id == b),
              and_(GameBattle.desafiante_id == b, GameBattle.desafiado_id == a))
    return (db.session.query(GameBattle)
            .filter(par, or_(GameBattle.status == "pendente", GameBattle.created_at >= janela))
            .first())


def pode_desafiar(desafiante_id: int, alvo_id: int) -> tuple[bool, str]:
    """(pode, motivo). Usado pelo card do jogador para mostrar/esconder o botão."""
    from .social import visivel
    if desafiante_id == alvo_id:
        return False, "Você não pode desafiar a si mesmo."
    eu = db.session.get(GamePlayer, desafiante_id)
    alvo = db.session.get(GamePlayer, alvo_id)
    alvo_user = db.session.get(User, alvo_id)
    if not eu or not alvo or not alvo_user:
        return False, "Os dois precisam ter começado a jornada."
    if not visivel(alvo_user):
        return False, "Esse treinador não aparece para batalhas."
    final = carregar().fase(eu.fase).regiao["casa_final"]
    if eu.fase != alvo.fase or eu.posicao != alvo.posicao:
        return False, "Só dá para desafiar quem está parado na mesma casa que você."
    if eu.posicao >= final:
        return False, "No Hall da Fama não há batalhas."
    if not _saudaveis(desafiante_id):
        return False, "Você não tem criatura saudável."
    if not _saudaveis(alvo_id):
        return False, "Esse treinador não tem criatura saudável."
    if _batalha_recente(desafiante_id, alvo_id):
        return False, "Vocês já batalharam nas últimas 24 h."
    return True, ""


def desafiar(desafiante_id: int, alvo_username: str, criatura_id: int, usar_isca: bool = False) -> dict:
    alvo_user = db.session.query(User).filter_by(username=alvo_username).one_or_none()
    if not alvo_user:
        raise JogoErro("Treinador não encontrado.", 404)
    jogadores = _travar(desafiante_id, alvo_user.id)
    ok, motivo = pode_desafiar(desafiante_id, alvo_user.id)
    if not ok:
        raise JogoErro(motivo, 409)
    gc = db.session.get(GameCreature, criatura_id)
    if not gc or gc.user_id != desafiante_id or gc.desmaiada:
        raise JogoErro("Escolha uma criatura sua e saudável.")
    if usar_isca:
        _gastar_item(desafiante_id, "isca")
    eu = jogadores[desafiante_id]
    b = GameBattle(fase=eu.fase, casa=eu.posicao, desafiante_id=desafiante_id, desafiado_id=alvo_user.id,
                   criatura_desafiante=gc.id, isca_desafiante=bool(usar_isca), status="pendente")
    db.session.add(b)
    db.session.flush()
    db.session.add(GameTurn(user_id=desafiante_id, fase=eu.fase, tipo="pvp", para=eu.posicao,
                            resultado={"batalha": b.id, "acao": "desafiou", "alvo": alvo_user.username}))
    db.session.commit()
    return {"batalha": b.id, "alvo": alvo_user.username, "status": "pendente"}


def responder(desafiado_id: int, batalha_id: int, criatura_id: int, usar_isca: bool = False, rng=None) -> dict:
    b = db.session.get(GameBattle, batalha_id)
    if not b or b.desafiado_id != desafiado_id:
        raise JogoErro("Desafio não encontrado.", 404)
    _travar(b.desafiante_id, b.desafiado_id)
    db.session.refresh(b)
    if b.status != "pendente":
        raise JogoErro("Esse desafio já foi resolvido.", 409)
    gc = db.session.get(GameCreature, criatura_id)
    if not gc or gc.user_id != desafiado_id or gc.desmaiada:
        raise JogoErro("Escolha uma criatura sua e saudável.")
    if usar_isca:
        _gastar_item(desafiado_id, "isca")
    b.criatura_desafiado = gc.id
    b.isca_desafiado = bool(usar_isca)
    res = _resolver(b, rng or secrets.SystemRandom())
    db.session.commit()
    return res


def _resolver(b: GameBattle, rng, expirada: bool = False) -> dict:
    cfg = _cfg()
    fase = carregar().fase(b.fase)

    def escolhida(cid, uid):
        gc = db.session.get(GameCreature, cid) if cid else None
        if gc is None or gc.user_id != uid or gc.desmaiada:
            gc = _mais_forte(uid)                 # desmaiou nesse meio-tempo → a mais forte
        return gc

    ca = escolhida(b.criatura_desafiante, b.desafiante_id)
    cd = escolhida(b.criatura_desafiado, b.desafiado_id)
    b.criatura_desafiante = ca.id if ca else None
    b.criatura_desafiado = cd.id if cd else None

    if ca is None and cd is None:
        vencedor, perdedor, gc_perdedor = b.desafiado_id, b.desafiante_id, None
        b.detalhe = "Ninguém tinha criatura saudável — vitória do defensor"
    elif ca is None:
        vencedor, perdedor, gc_perdedor = b.desafiado_id, b.desafiante_id, None
        b.detalhe = "W.O. — desafiante sem criatura saudável"
    elif cd is None:
        vencedor, perdedor, gc_perdedor = b.desafiante_id, b.desafiado_id, None
        b.detalhe = "W.O. — defensor sem criatura saudável"
    else:
        b.dado_desafiante, b.dado_desafiado = rng.randint(1, 6), rng.randint(1, 6)
        b.total_desafiante = b.dado_desafiante + _ataque(ca) + (1 if b.isca_desafiante else 0)
        b.total_desafiado = b.dado_desafiado + _ataque(cd) + (1 if b.isca_desafiado else 0)
        if b.total_desafiante > b.total_desafiado:          # empate = defensor vence
            vencedor, perdedor, gc_perdedor = b.desafiante_id, b.desafiado_id, cd
        else:
            vencedor, perdedor, gc_perdedor = b.desafiado_id, b.desafiante_id, ca

    if gc_perdedor is not None:
        gc_perdedor.desmaiada = True
    pv = db.session.get(GamePlayer, vencedor)
    pv.pp += cfg["pp_vitoria"]

    roubados = []
    unidades = [i.item_key for i in sorted(db.session.query(GameItem).filter_by(user_id=perdedor),
                                           key=lambda i: i.item_key) for _ in range(i.qtd)]
    for _ in range(min(cfg["itens_roubados"], len(unidades))):
        key = rng.choice(unidades)
        unidades.remove(key)
        if _dar_item(vencedor, key):          # vencedor com mão cheia: o item fica com o perdedor
            _gastar_item(perdedor, key)
            roubados.append(key)

    b.vencedor_id = vencedor
    b.itens_roubados = roubados
    b.status = "expirada" if expirada else "resolvida"
    b.resolved_at = now_br()

    nomes = {u.id: u.username for u in db.session.query(User).filter(User.id.in_((b.desafiante_id, b.desafiado_id)))}
    res = publica(b, nomes)
    res["texto"] = f"venceu {nomes[perdedor]} numa batalha"
    for uid in (b.desafiante_id, b.desafiado_id):
        db.session.add(GameTurn(user_id=uid, fase=b.fase, tipo="pvp", para=b.casa,
                                pp_delta=cfg["pp_vitoria"] if uid == vencedor else 0,
                                resultado={**res, "vencedor": uid == vencedor}))
    return res


def publica(b: GameBattle, nomes: dict | None = None) -> dict:
    fase = carregar().fase(b.fase)
    if nomes is None:
        nomes = {u.id: u.username for u in
                 db.session.query(User).filter(User.id.in_((b.desafiante_id, b.desafiado_id)))}

    def cr(cid):
        gc = db.session.get(GameCreature, cid) if cid else None
        return criatura_publica(fase.criaturas[gc.creature_key]) if gc else None

    return {
        "id": b.id, "status": b.status, "casa": b.casa,
        "desafiante": nomes.get(b.desafiante_id), "desafiado": nomes.get(b.desafiado_id),
        "criatura_desafiante": cr(b.criatura_desafiante), "criatura_desafiado": cr(b.criatura_desafiado),
        "isca_desafiante": b.isca_desafiante, "isca_desafiado": b.isca_desafiado,
        "dado_desafiante": b.dado_desafiante, "dado_desafiado": b.dado_desafiado,
        "total_desafiante": b.total_desafiante, "total_desafiado": b.total_desafiado,
        "vencedor": nomes.get(b.vencedor_id), "itens_roubados": b.itens_roubados or [],
        "detalhe": b.detalhe, "criada": b.created_at.strftime("%d/%m %H:%M") if b.created_at else None,
    }


def expirar_pendentes(rng=None) -> int:
    """Resolve desafios sem resposta há mais de 24 h. Chamado nas leituras (barato)."""
    limite = now_br() - timedelta(hours=_cfg()["janela_horas"])
    pend = (db.session.query(GameBattle)
            .filter(GameBattle.status == "pendente", GameBattle.created_at < limite).all())
    if not pend:
        return 0
    rng = rng or secrets.SystemRandom()
    for b in pend:
        _travar(b.desafiante_id, b.desafiado_id)
        db.session.refresh(b)
        if b.status == "pendente":
            _resolver(b, rng, expirada=True)
    db.session.commit()
    return len(pend)


def minhas_batalhas(user_id: int, limite: int = 10) -> dict:
    recebidos = (db.session.query(GameBattle)
                 .filter_by(desafiado_id=user_id, status="pendente").order_by(GameBattle.id).all())
    enviados = (db.session.query(GameBattle)
                .filter_by(desafiante_id=user_id, status="pendente").order_by(GameBattle.id).all())
    recentes = (db.session.query(GameBattle)
                .filter(or_(GameBattle.desafiante_id == user_id, GameBattle.desafiado_id == user_id),
                        GameBattle.status != "pendente")
                .order_by(GameBattle.id.desc()).limit(limite).all())
    return {
        # o defensor não vê a criatura do desafiante antes de escolher a dele
        "recebidos": [{**publica(b), "criatura_desafiante": None, "isca_desafiante": None} for b in recebidos],
        "enviados": [publica(b) for b in enviados],
        "recentes": [publica(b) for b in recentes],
    }
