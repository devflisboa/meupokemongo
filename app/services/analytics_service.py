from flask import request
from flask_login import current_user
from ..extensions import db
from ..models.event import AnalyticsEvent


def log_event(event_type: str, metadata: dict | None = None) -> None:
    """RF13, RB09: registra um evento de analytics."""
    user_id = current_user.id if current_user and current_user.is_authenticated else None
    ip = request.remote_addr if request else None

    event = AnalyticsEvent(
        event_type=event_type,
        user_id=user_id,
        metadata_json=metadata or {},
        ip_address=ip,
    )
    db.session.add(event)
    db.session.commit()
