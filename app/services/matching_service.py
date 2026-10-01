from sqlalchemy.exc import IntegrityError
from ..extensions import db
from ..models.collection import UserCollection
from ..models.wishlist import Wishlist
from ..models.friendship import Friendship
from ..models.trade import TradeMatch
from ..models.user import User


def _interaction_allowed(wisher: User, owner: User) -> bool:
    """Verifica se wisher pode ver a coleção do owner (visibilidade + amizade)."""
    if owner.visibility == "public":
        return True
    if owner.visibility == "private":
        return False
    # friends
    friendship = db.session.query(Friendship).filter(
        db.or_(
            db.and_(Friendship.requester_id == wisher.id, Friendship.addressee_id == owner.id),
            db.and_(Friendship.requester_id == owner.id, Friendship.addressee_id == wisher.id),
        ),
        Friendship.status == "accepted",
    ).first()
    return friendship is not None


def run_matching_for_user(user_id: int) -> int:
    """
    RF10: gera matches para o treinador a partir de seus desejos.
    Retorna o número de novos matches criados.
    """
    wishes = db.session.query(Wishlist).filter_by(user_id=user_id).all()
    wisher = db.session.get(User, user_id)
    created = 0

    for wish in wishes:
        offers = db.session.query(UserCollection).filter(
            UserCollection.form_id == wish.form_id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
            UserCollection.for_trade.is_(True),
            UserCollection.user_id != user_id,
        ).all()

        for offer in offers:
            owner = db.session.get(User, offer.user_id)
            if not _interaction_allowed(wisher, owner):
                continue

            match = TradeMatch(
                wisher_id=user_id,
                owner_id=owner.id,
                form_id=wish.form_id,
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
    return db.session.query(TradeMatch).filter(
        TradeMatch.wisher_id == user_id,
        TradeMatch.status == "active",
    ).all()
