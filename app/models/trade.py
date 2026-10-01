from datetime import datetime
from ..extensions import db


class TradeMatch(db.Model):
    """Match de troca entre dois treinadores (RF10, RB07-RB08)."""
    __tablename__ = "trade_matches"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    wisher_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    owner_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False)
    status = db.Column(db.Enum("active", "contacted", "completed", "cancelled"), default="active", nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    wisher = db.relationship("User", foreign_keys=[wisher_id])
    owner = db.relationship("User", foreign_keys=[owner_id])
    form = db.relationship("Form")

    # RB08: sem duplicidade de match ativo para a mesma combinação
    __table_args__ = (
        db.UniqueConstraint("wisher_id", "owner_id", "form_id", name="uq_active_match"),
    )

    def __repr__(self) -> str:
        return f"<TradeMatch wisher={self.wisher_id} owner={self.owner_id} form={self.form_id} {self.status}>"


class WhatsappClick(db.Model):
    """Registro de clique em botão WhatsApp (RF11, RB10)."""
    __tablename__ = "whatsapp_clicks"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    match_id = db.Column(db.Integer, db.ForeignKey("trade_matches.id"), nullable=False, index=True)
    clicker_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    clicked_at = db.Column(db.DateTime, default=datetime.utcnow)

    match = db.relationship("TradeMatch")
    clicker = db.relationship("User", foreign_keys=[clicker_id])
