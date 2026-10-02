from ..config import now_br
from ..extensions import db


class UserCollection(db.Model):
    """Registro de posse de um Pokémon pelo treinador (RF04, RB01-RB03, RB05)."""
    __tablename__ = "user_collections"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False, index=True)
    owned = db.Column(db.Boolean, default=False, nullable=False)
    quantity = db.Column(db.Integer, default=0, nullable=False)
    for_trade = db.Column(db.Boolean, default=False, nullable=False)
    has_shiny = db.Column(db.Boolean, default=False, nullable=False)
    shiny_qty = db.Column(db.Integer, default=0, nullable=False)
    notes = db.Column(db.String(500), nullable=True)
    created_at = db.Column(db.DateTime, default=now_br)
    updated_at = db.Column(db.DateTime, default=now_br, onupdate=now_br)

    user = db.relationship("User", back_populates="collection")
    form = db.relationship("Form", back_populates="collection_entries")

    __table_args__ = (
        db.UniqueConstraint("user_id", "form_id", name="uq_user_form"),
        db.CheckConstraint("quantity >= 0", name="chk_quantity_non_negative"),
    )

    def is_owned(self) -> bool:
        """RB01: possuído = owned=True AND quantity>0."""
        return self.owned and self.quantity > 0

    def set_for_trade(self, value: bool) -> None:
        """RB03: for_trade só pode ser True se o Pokémon for possuído."""
        if value and not self.is_owned():
            raise ValueError("Não é possível marcar para troca um Pokémon não possuído.")
        self.for_trade = value

    def __repr__(self) -> str:
        return f"<UserCollection user={self.user_id} form={self.form_id} owned={self.owned}>"
