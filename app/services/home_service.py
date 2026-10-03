"""
Dados da tela de Início (redesenho de 03/10/2026).

Logado, em três blocos, nesta ordem (decisão do usuário):
  1. Painel — saudação com a cor do favorito, progresso, Brilhante/100%, barras por região
  2. Central de Trocas — trocas de mão dupla, "o que fazer agora", treinadores perto
  3. Feed — quem tem para troca o que você procura, treinadores novos, eventos do GO
Sem login: página de apresentação com vitrine de treinadores reais.

O feed não usa tabela nova: deriva de UserCollection.updated_at e User.created_at.
"""
from datetime import datetime

from ..config import now_br
from ..extensions import db
from ..models.collection import UserCollection
from ..models.pokemon import Form
from ..models.user import User


def ha_quanto(dt: datetime | None, agora: datetime | None = None) -> str:
    """'agora' · 'há 5 min' · 'há 3 h' · 'ontem' · 'há 4 dias' · '12/09'."""
    if not dt:
        return ""
    s = ((agora or now_br()) - dt).total_seconds()
    if s < 60:
        return "agora"
    if s < 3600:
        return f"há {int(s // 60)} min"
    if s < 86400:
        return f"há {int(s // 3600)} h"
    d = int(s // 86400)
    if d == 1:
        return "ontem"
    if d < 7:
        return f"há {d} dias"
    return dt.strftime("%d/%m")


def _normal_ids():
    return db.session.query(Form.id).filter(Form.form_name == "normal").scalar_subquery()


def region_progress(user_id: int) -> list[dict]:
    """[{name, owned, total, pct}] por região da Pokédex (só formas normais)."""
    from ..blueprints.collection.routes import REGIONS
    owned_species = {
        sid for (sid,) in db.session.query(Form.species_id)
        .join(UserCollection, UserCollection.form_id == Form.id)
        .filter(UserCollection.user_id == user_id, UserCollection.owned.is_(True),
                UserCollection.quantity > 0, Form.form_name == "normal")
    }
    out = []
    for r in REGIONS:
        owned = sum(1 for s in owned_species if r["start"] <= s <= r["end"])
        out.append({"name": r["name"], "owned": owned, "total": r["count"],
                    "pct": round(owned / r["count"] * 100) if r["count"] else 0})
    return out


def special_progress(user_id: int) -> dict:
    rows = db.session.query(UserCollection.has_shiny, UserCollection.has_perfect).filter(
        UserCollection.user_id == user_id, UserCollection.owned.is_(True), UserCollection.quantity > 0,
        UserCollection.form_id.in_(_normal_ids()),
    ).all()
    return {"shiny": sum(1 for sh, _ in rows if sh), "perfect": sum(1 for _, pf in rows if pf),
            "shundo": sum(1 for sh, pf in rows if sh and pf)}


def nearby_trainers(me: User, limit: int = 8) -> list[dict]:
    """Treinadores ao alcance de troca (📍 cidade primeiro, depois 🌐), com tema do favorito."""
    from .matching_service import proximity_tier, TIER_LABEL
    out = []
    for u in db.session.query(User).filter(User.visibility != "private", User.id != me.id):
        tier = proximity_tier(me, u)
        if tier is not None:
            out.append({"user": u, "tier": tier, "tier_label": TIER_LABEL[tier]})
    out.sort(key=lambda t: (t["tier"], t["user"].username.lower()))
    return out[:limit]


def build_feed(me: User, missing_ids: set[int], limit: int = 12) -> list[dict]:
    """
    Atividade recente relevante para mim:
      🟢 alguém (ao meu alcance) tem para troca um Pokémon que eu procuro
      👋 treinador novo ao meu alcance
    """
    from .matching_service import proximity_tier
    items = []
    if missing_ids:
        offers = (
            db.session.query(UserCollection, User, Form)
            .join(User, User.id == UserCollection.user_id)
            .join(Form, Form.id == UserCollection.form_id)
            .filter(User.visibility != "private", User.id != me.id,
                    UserCollection.for_trade.is_(True), UserCollection.owned.is_(True),
                    UserCollection.quantity > 0, UserCollection.form_id.in_(missing_ids),
                    ~Form.form_name.like("mega%"))
            .order_by(UserCollection.updated_at.desc())
            .limit(60).all()
        )
        for uc, owner, form in offers:
            if proximity_tier(me, owner) is None:
                continue
            items.append({"kind": "offer", "when": uc.updated_at, "user": owner, "form": form})
    for u in (db.session.query(User).filter(User.visibility != "private", User.id != me.id)
              .order_by(User.created_at.desc()).limit(20)):
        if proximity_tier(me, u) is not None:
            items.append({"kind": "new_trainer", "when": u.created_at, "user": u})
    items.sort(key=lambda i: i["when"] or datetime.min, reverse=True)
    agora = now_br()
    for i in items:
        i["ago"] = ha_quanto(i["when"], agora)
    return items[:limit]


def showcase_trainers(limit: int = 6) -> list[dict]:
    """Vitrine da página de apresentação: quem mais tem para troca (com tema do favorito)."""
    counts = dict(
        db.session.query(UserCollection.user_id, db.func.count(UserCollection.id))
        .filter(UserCollection.for_trade.is_(True), UserCollection.owned.is_(True), UserCollection.quantity > 0)
        .group_by(UserCollection.user_id).all()
    )
    users = db.session.query(User).filter(User.visibility != "private").all()
    users.sort(key=lambda u: (-counts.get(u.id, 0), u.username.lower()))
    return [{"user": u, "for_trade": counts.get(u.id, 0)} for u in users[:limit]]
