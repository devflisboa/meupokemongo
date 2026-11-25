"""Jornada — parte social (J2): Mapa Global, Hall da Fama, ranking, card, feed, descobertas.

Só leitura. Quem aparece: usuários com visibilidade != "private" (o mesmo toggle das trocas,
decisão D9) e que não sejam contas de teste (username começando com "e2e").
"""
from __future__ import annotations

import time
from datetime import timedelta

from flask import url_for
from sqlalchemy import func

from ...config import now_br
from ...extensions import db
from ...models.jornada import GameCreature, GameDiscovery, GamePlayer, GameTurn
from ...models.user import User
from .conteudo import carregar

_CACHE: dict = {}
CACHE_SEGUNDOS = 15


def _cache(chave, fn):
    agora = time.monotonic()
    hit = _CACHE.get(chave)
    if hit and agora - hit[0] < CACHE_SEGUNDOS:
        return hit[1]
    valor = fn()
    _CACHE[chave] = (agora, valor)
    return valor


def limpar_cache() -> None:
    _CACHE.clear()


def _visiveis():
    """GamePlayer + User de quem aparece para os outros."""
    return (
        db.session.query(GamePlayer, User)
        .join(User, User.id == GamePlayer.user_id)
        .filter(User.visibility != "private", ~func.lower(User.username).like("e2e%"))
    )


def visivel(user: User) -> bool:
    return user.visibility != "private" and not user.username.lower().startswith("e2e")


def online(p: GamePlayer) -> bool:
    minutos = carregar().jogo["pvp"]["online_minutos"]
    return bool(p.last_seen and now_br() - p.last_seen < timedelta(minutes=minutos))


def avatar_url(u: User) -> str | None:
    return url_for("auth.avatar", user_id=u.id) if u.avatar else None


def resumo(p: GamePlayer, u: User) -> dict:
    fase = carregar().fase(p.fase)
    local = fase.local_da_casa(p.posicao)
    return {
        "user_id": u.id, "username": u.username, "avatar": avatar_url(u),
        "inicial": (u.username[:1] or "?").upper(), "online": online(p),
        "fase": p.fase, "posicao": p.posicao, "volta": p.volta, "pp": p.pp,
        "local": local["nome"], "local_key": local["key"], "local_emoji": local.get("emoji", ""),
        "local_indice": fase.indice_local(p.posicao), "locais_total": len(fase.regiao["locais"]),
        "campeao": p.posicao >= fase.regiao["casa_final"],
        "titulo_em": p.titulo_fase1_em.strftime("%d/%m/%Y") if p.titulo_fase1_em else None,
        "card_url": url_for("jornada.treinador", username=u.username),
    }


# ── Mapa Global ────────────────────────────────────────────────────────────

def mapa(numero_fase: int = 1) -> dict:
    def calc():
        fase = carregar().fase(numero_fase)
        final = fase.regiao["casa_final"]
        nos = {loc["key"]: {**loc, "jogadores": []} for loc in fase.regiao["locais"]}
        for p, u in _visiveis().filter(GamePlayer.fase == numero_fase):
            r = resumo(p, u)
            nos[r["local_key"]]["jogadores"].append(r)
        for no in nos.values():
            if no["de"] == final:      # Hall da Fama: ordem de conquista
                no["jogadores"].sort(key=lambda r: (r["titulo_em"] is None, _titulo_ordem(r)))
            else:                      # online primeiro, depois quem está mais à frente
                no["jogadores"].sort(key=lambda r: (not r["online"], -r["posicao"], -r["pp"]))
            no["total"] = len(no["jogadores"])
            no["online_total"] = sum(1 for r in no["jogadores"] if r["online"])
        return {"fase": numero_fase, "regiao": fase.regiao["nome"], "nos": list(nos.values()),
                "total": sum(n["total"] for n in nos.values())}
    return _cache(("mapa", numero_fase), calc)


def _titulo_ordem(r: dict) -> str:
    if not r["titulo_em"]:
        return ""
    d, m, a = r["titulo_em"].split("/")
    return f"{a}{m}{d}"


def hall_da_fama(numero_fase: int = 1) -> list[dict]:
    fase = carregar().fase(numero_fase)
    rows = (
        _visiveis()
        .filter(GamePlayer.fase == numero_fase, GamePlayer.posicao >= fase.regiao["casa_final"])
        .order_by(GamePlayer.titulo_fase1_em.asc())
        .all()
    )
    out = []
    for i, (p, u) in enumerate(rows, start=1):
        r = resumo(p, u)
        r["ordem"] = i
        r["capturadas"] = db.session.query(GameCreature).filter_by(user_id=u.id).count()
        out.append(r)
    return out


# ── Ranking ────────────────────────────────────────────────────────────────

def ranking(numero_fase: int | None, user_id: int | None = None) -> dict:
    """numero_fase=None → Global. Ordem da spec: fase DESC, posição DESC, PP DESC."""
    q = _visiveis()
    if numero_fase is not None:
        q = q.filter(GamePlayer.fase == numero_fase)
    rows = q.order_by(GamePlayer.fase.desc(), GamePlayer.posicao.desc(), GamePlayer.pp.desc(),
                      GamePlayer.user_id.asc()).all()
    lista = []
    eu = None
    for i, (p, u) in enumerate(rows, start=1):
        r = resumo(p, u)
        r["rank"] = i
        lista.append(r)
        if u.id == user_id:
            eu = r
    if user_id and eu is None:         # eu não apareço (privado/teste), mas mostro minha situação
        p = db.session.get(GamePlayer, user_id)
        u = db.session.get(User, user_id)
        if p and u:
            eu = resumo(p, u)
            eu["rank"] = None
    return {"lista": lista, "eu": eu}


# ── Card do jogador ────────────────────────────────────────────────────────

def card(username: str, viewer_id: int | None = None) -> dict | None:
    u = db.session.query(User).filter(func.lower(User.username) == username.lower()).one_or_none()
    if not u:
        return None
    p = db.session.get(GamePlayer, u.id)
    if not p:
        return None
    if u.id != viewer_id and not visivel(u):
        return None
    c = carregar()
    fase = c.fase(p.fase)
    r = resumo(p, u)
    from .motor import criatura_publica
    criaturas = db.session.query(GameCreature).filter_by(user_id=u.id).all()
    time_ = []
    for gc in sorted((g for g in criaturas if g.slot), key=lambda g: g.slot):
        d = criatura_publica(fase.criaturas[gc.creature_key])
        d.update(id=gc.id, desmaiada=gc.desmaiada)
        time_.append(d)
    ult = (db.session.query(GameTurn.created_at).filter_by(user_id=u.id)
           .order_by(GameTurn.id.desc()).limit(1).scalar())
    r.update(
        capturadas=len(criaturas), criaturas_total=len(fase.criaturas),
        sequencia_dias=p.sequencia_dias, insignias=[fase.ginasios[k] for k in (p.insignias or []) if k in fase.ginasios],
        ginasios_total=len(fase.ginasios), time=time_,
        ultima_atividade=ult.strftime("%d/%m %H:%M") if ult else None,
        eu=(u.id == viewer_id),
    )
    if viewer_id and viewer_id != u.id:
        from .pvp import pode_desafiar
        r["pode_desafiar"], r["motivo_desafio"] = pode_desafiar(viewer_id, u.id)
    return r


# ── Feed e vizinhos (polling) ──────────────────────────────────────────────

def _texto_turno(t: GameTurn) -> str | None:
    r = t.resultado or {}
    if t.tipo == "movimento":
        if r.get("nova_volta"):
            return f"começou a volta {r['nova_volta']}"
        if r.get("ginasio", {}).get("venceu") and not r["ginasio"].get("ja_vencido"):
            return f"venceu o {r['ginasio']['nome']}"
        if r.get("desafio") == "disponivel":
            return "chegou ao Desafio do Pico"
        return f"tirou {t.dado} e foi para a casa {r.get('posicao_final', t.para)}"
    if t.tipo == "captura" and r.get("capturou"):
        return f"capturou {r['criatura']['nome']}"
    if t.tipo == "desafio":
        return "entrou para o Hall da Fama! 🏛️" if r.get("venceu") else "perdeu o Desafio do Pico"
    if t.tipo == "pvp" and r.get("vencedor"):
        return r.get("texto")
    return None


def feed(numero_fase: int, desde: int = 0, excluir_user: int | None = None, limite: int = 30) -> list[dict]:
    q = (
        db.session.query(GameTurn, User)
        .join(User, User.id == GameTurn.user_id)
        .filter(GameTurn.fase == numero_fase, GameTurn.id > desde,
                GameTurn.tipo.in_(("movimento", "captura", "desafio", "pvp")),
                User.visibility != "private", ~func.lower(User.username).like("e2e%"))
    )
    if excluir_user:
        q = q.filter(GameTurn.user_id != excluir_user)
    rows = q.order_by(GameTurn.id.desc()).limit(limite).all()
    out = []
    for t, u in rows:
        txt = _texto_turno(t)
        if txt:
            out.append({"id": t.id, "username": u.username, "texto": txt,
                        "quando": t.created_at.strftime("%H:%M")})
    return out


def ultimo_turno_id() -> int:
    return db.session.query(func.max(GameTurn.id)).scalar() or 0


def vizinhos(numero_fase: int, excluir_user: int | None = None) -> list[dict]:
    """Posição de todos os visíveis — peões dos outros na trilha."""
    out = []
    for p, u in _visiveis().filter(GamePlayer.fase == numero_fase):
        if u.id == excluir_user:
            continue
        out.append({"username": u.username, "posicao": p.posicao, "avatar": avatar_url(u),
                    "inicial": (u.username[:1] or "?").upper(), "online": online(p)})
    return out


def no_mesmo_lugar(p: GamePlayer) -> list[dict]:
    """Jogadores visíveis parados na mesma casa (candidatos a PvP)."""
    out = []
    rows = _visiveis().filter(GamePlayer.fase == p.fase, GamePlayer.posicao == p.posicao,
                              GamePlayer.user_id != p.user_id)
    for q, u in rows:
        out.append({"username": u.username, "user_id": u.id, "online": online(q), "avatar": avatar_url(u),
                    "inicial": (u.username[:1] or "?").upper()})
    return out


# ── Descobertas ────────────────────────────────────────────────────────────

def descobertas(numero_fase: int = 1, user_id: int | None = None) -> dict:
    from .motor import criatura_publica
    fase = carregar().fase(numero_fase)
    achadas = {d.creature_key: (d, u) for d, u in
               db.session.query(GameDiscovery, User).join(User, User.id == GameDiscovery.discovered_by)}
    minhas = set()
    if user_id:
        minhas = {k for (k,) in db.session.query(GameCreature.creature_key).filter_by(user_id=user_id)}
    lista = []
    for cr in sorted(fase.criaturas.values(), key=lambda c: (c["estagio"], c["habitat"], c["key"])):
        item = {"estagio": cr["estagio"], "tenho": cr["key"] in minhas}
        if cr["key"] in achadas:
            d, u = achadas[cr["key"]]
            item.update(criatura_publica(cr), revelada=True,
                        por=u.username if visivel(u) or u.id == user_id else "treinador anônimo",
                        em=d.discovered_at.strftime("%d/%m/%Y"))
        else:
            item.update(revelada=False)          # sem nome nem key: não estraga a surpresa
        lista.append(item)
    return {"lista": lista, "reveladas": len(achadas), "total": len(fase.criaturas), "minhas": len(minhas)}
