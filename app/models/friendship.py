from datetime import datetime
from ..extensions import db


class Friendship(db.Model):
    """Amizades entre treinadores (RF09, RB13)."""
    __tablename__ = "friendships"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    requester_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    addressee_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    status = db.Column(db.Enum("pending", "accepted", "blocked"), default="pending", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    requester = db.relationship("User", foreign_keys=[requester_id])
    addressee = db.relationship("User", foreign_keys=[addressee_id])

    __table_args__ = (
        db.UniqueConstraint("requester_id", "addressee_id", name="uq_friendship_pair"),
    )

    def __repr__(self) -> str:
        return f"<Friendship {self.requester_id}→{self.addressee_id} {self.status}>"
