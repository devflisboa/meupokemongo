"""
Matching de trocas (RF10 + #24).

Troca no Pokémon GO é presencial, então a proximidade define quem entra e em que ordem:
  TIER_CITY    mesma cidade
  TIER_REMOTE  outra cidade, mas um dos dois troca à distância
  TIER_UNKNOWN algum dos dois ainda não informou a cidade (aparece por último, com aviso)
  None         cidades diferentes e ninguém troca à distância → fica de fora
"""
from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models.collection import UserCollection
from ..models.pokemon import Form
from ..models.trade import TradeMatch
from ..models.user import User

TIER_CITY, TIER_REMOTE, TIER_UNKNOWN = 0, 1, 2
TIER_LABEL = {
    TIER_CITY: "📍 Mesma cidade",
    TIER_REMOTE: "🌐 Troca à distância",
    TIER_UNKNOWN: "❔ Cidade não informada",
}


def proximity_tier(viewer: User, other: User) -> int | None:
    """Faixa de proximidade entre dois treinadores (menor = melhor) ou None se não dá para trocar."""
    if not other.show_in_trades:
        return None
    if viewer.city and other.city and viewer.state == other.state and viewer.city == other.city:
        return TIER_CITY
    if viewer.can_trade_remote or other.can_trade_remote:
        return TIER_REMOTE
    if not (viewer.city and other.city):
        return TIER_UNKNOWN
    return None


def _interaction_allowed(wisher: User, owner: User) -> bool:
    """Todos se enxergam (D1), limitado pela proximidade (#24)."""
    return proximity_tier(wisher, owner) is not None


def _owned_subq(user_id: int):
    return (
        db.session.query(UserCollection.form_id)
        .filter(
            UserCollection.user_id == user_id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        )
        .scalar_subquery()
    )


def run_matching_for_user(user_id: int) -> int:
    """
    RF10: gera matches para o treinador a partir da wishlist automática
    (toda forma normal que ele ainda não possui). Retorna o número de novos matches criados.
    """
    wisher = db.session.get(User, user_id)
    created = 0

    offers = (
        db.session.query(UserCollection)
        .join(Form, Form.id == UserCollection.form_id)
        .filter(
            Form.form_name == "normal",
            UserCollection.form_id.notin_(_owned_subq(user_id)),
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
            UserCollection.for_trade.is_(True),
            UserCollection.user_id != user_id,
        )
        .all()
    )

    owners: dict[int, User] = {}
    for offer in offers:
        owner = owners.setdefault(offer.user_id, db.session.get(User, offer.user_id))
        if not _interaction_allowed(wisher, owner):
            continue

        match = TradeMatch(
            wisher_id=user_id,
            owner_id=owner.id,
            form_id=offer.form_id,
            status="active",
        )
        db.session.add(match)
        try:
            db.session.commit()
            created += 1
        except IntegrityError:
            # RB08: já existe match ativo para essa combinação
            db.session.rollback()

    return created


def get_active_matches_for_user(user_id: int) -> list[TradeMatch]:
    """Matches ativos ordenados por proximidade; quem saiu do alcance (ex.: ficou privado) some."""
    viewer = db.session.get(User, user_id)
    matches = db.session.query(TradeMatch).filter(
        TradeMatch.wisher_id == user_id,
        TradeMatch.status == "active",
    ).all()
    ranked = []
    for m in matches:
        tier = proximity_tier(viewer, m.owner)
        if tier is not None:
            m.tier = tier
            m.tier_label = TIER_LABEL[tier]
            ranked.append(m)
    ranked.sort(key=lambda m: (m.tier, m.owner.username.lower(), m.form.species_id))
    return ranked


def _names(forms: list[Form], limit: int = 3) -> str:
    """'Lapras, Eevee e mais 2' — nomes em PT para mensagens."""
    names = [
        (f.species.name_pt or f.species.name).removesuffix("-normal").replace("-", " ").title()
        for f in forms[:limit]
    ]
    extra = len(forms) - limit
    return ", ".join(names) + (f" e mais {extra}" if extra > 0 else "")


def get_reciprocal_trades(user_id: int, limit: int = 20) -> list[dict]:
    """
    Trocas de mão dupla (#24): treinadores que têm para troca algo que me falta
    E que não têm algo que eu tenho para troca.
    Retorna [{user, tier, tier_label, they_have: [Form], i_have: [Form]}] — melhores primeiro.
    """
    me = db.session.get(User, user_id)

    # O que os outros oferecem e eu não tenho
    their_offers = (
        db.session.query(UserCollection.user_id, Form)
        .join(Form, Form.id == UserCollection.form_id)
        .filter(
            Form.form_name == "normal",
            UserCollection.form_id.notin_(_owned_subq(user_id)),
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
            UserCollection.for_trade.is_(True),
            UserCollection.user_id != user_id,
        )
        .all()
    )
    they_have: dict[int, list[Form]] = {}
    for uid, form in their_offers:
        they_have.setdefault(uid, []).append(form)
    if not they_have:
        return []

    # O que eu ofereço
    my_offers = (
        db.session.query(Form)
        .join(UserCollection, UserCollection.form_id == Form.id)
        .filter(
            UserCollection.user_id == user_id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
            UserCollection.for_trade.is_(True),
        )
        .all()
    )
    if not my_offers:
        return []
    my_offer_ids = {f.id for f in my_offers}

    # Quais das minhas ofertas cada candidato já tem
    owned_by: dict[int, set[int]] = {}
    for uid, fid in (
        db.session.query(UserCollection.user_id, UserCollection.form_id)
        .filter(
            UserCollection.user_id.in_(list(they_have)),
            UserCollection.form_id.in_(my_offer_ids),
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        )
        .all()
    ):
        owned_by.setdefault(uid, set()).add(fid)

    result = []
    for uid, forms in they_have.items():
        other = db.session.get(User, uid)
        tier = proximity_tier(me, other)
        if tier is None:
            continue
        i_have = [f for f in my_offers if f.id not in owned_by.get(uid, set())]
        if not i_have:
            continue
        they = sorted(forms, key=lambda f: f.species_id)
        mine = sorted(i_have, key=lambda f: f.species_id)
        result.append({
            "user": other,
            "tier": tier,
            "tier_label": TIER_LABEL[tier],
            "they_have": they,
            "i_have": mine,
            # resumo para a mensagem do WhatsApp
            "they_names": _names(they),
            "i_names": _names(mine),
        })

    # mais perto primeiro; depois quem fecha mais trocas (o menor dos dois lados)
    result.sort(key=lambda r: (r["tier"], -min(len(r["they_have"]), len(r["i_have"])),
                               -(len(r["they_have"]) + len(r["i_have"]))))
    return result[:limit]
