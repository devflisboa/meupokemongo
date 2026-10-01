from ..config import now_br
from ..extensions import db

EVENT_TYPES = (
    "PAGE_VIEW",
    "SEARCH",
    "FILTER",
    "POKEMON_VIEW",
    "TRADE_CLICK",
    "WHATSAPP_CLICK",
    "IMPORT",
    "ERROR",
)


class AnalyticsEvent(db.Model):
    """Tabela única de eventos de analytics (RF13, RB09)."""
    __tablename__ = "events"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    event_type = db.Column(db.String(30), nullable=False, index=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True, index=True)
    metadata_json = db.Column(db.JSON, nullable=True)
    ip_address = db.Column(db.String(45), nullable=True)
    created_at = db.Column(db.DateTime, default=now_br, nullable=False, index=True)

    user = db.relationship("User", back_populates="events")

    def __repr__(self) -> str:
        return f"<AnalyticsEvent {self.event_type} user={self.user_id}>"
