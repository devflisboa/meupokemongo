from ..extensions import db
from ..models.collection import UserCollection
from ..models.pokemon import Form, EvolutionChain, Species


def get_missing_pokemon(user_id: int) -> list[Form]:
    """RF05: retorna formas que o treinador ainda não possui (owned=True AND quantity>0)."""
    owned_form_ids = db.session.query(UserCollection.form_id).filter(
        UserCollection.user_id == user_id,
        UserCollection.owned.is_(True),
        UserCollection.quantity > 0,
    ).scalar_subquery()

    return db.session.query(Form).filter(Form.id.notin_(owned_form_ids)).all()


def get_pending_evolutions(user_id: int) -> list[dict]:
    """
    RF06: retorna pares (from_form, to_form) onde o treinador possui a etapa anterior
    mas não possui a etapa posterior.
    """
    owned_form_ids = set(
        row[0]
        for row in db.session.query(UserCollection.form_id).filter(
            UserCollection.user_id == user_id,
            UserCollection.owned.is_(True),
            UserCollection.quantity > 0,
        ).all()
    )

    chains = db.session.query(EvolutionChain).all()
    pending = []
    for chain in chains:
        if chain.from_form_id in owned_form_ids and chain.to_form_id not in owned_form_ids:
            pending.append({
                "from_form": chain.from_form,
                "to_form": chain.to_form,
                "candy_cost": chain.candy_cost,
                "candy_name": chain.candy_name,
            })
    return pending


def get_collection_stats(user_id: int) -> dict:
    total_species = db.session.query(Species).count()
    owned_count = db.session.query(UserCollection).filter(
        UserCollection.user_id == user_id,
        UserCollection.owned.is_(True),
        UserCollection.quantity > 0,
    ).count()

    return {
        "total": total_species,
        "owned": owned_count,
        "missing": total_species - owned_count,
        "percent": round(owned_count / total_species * 100, 1) if total_species else 0,
    }
