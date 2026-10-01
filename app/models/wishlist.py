from ..config import now_br
from ..extensions import db


class Wishlist(db.Model):
    """Pokémon desejados pelo treinador (RF07, RB06)."""
    __tablename__ = "wishlists"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False)
    priority = db.Column(db.Enum("low", "medium", "high"), default="medium", nullable=False)
    created_at = db.Column(db.DateTime, default=now_br)

    user = db.relationship("User", back_populates="wishlist")
    form = db.relationship("Form")

    __table_args__ = (
        db.UniqueConstraint("user_id", "form_id", name="uq_wish_user_form"),
    )

    def __repr__(self) -> str:
        return f"<Wishlist user={self.user_id} form={self.form_id} priority={self.priority}>"
