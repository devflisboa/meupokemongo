from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from ..extensions import db, login_manager
from ..config import now_br


class User(UserMixin, db.Model):
    __tablename__ = "users"

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(255), nullable=False)
    trainer_code = db.Column(db.String(20), nullable=True)
    is_admin = db.Column(db.Boolean, default=False, nullable=False)
    # public = coleção visível a todos; friends = só amigos; private = só o dono
    visibility = db.Column(db.Enum("public", "friends", "private"), default="public", nullable=False)
    created_at = db.Column(db.DateTime, default=now_br, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_br, onupdate=now_br)

    collection = db.relationship("UserCollection", back_populates="user", lazy="dynamic")
    wishlist = db.relationship("Wishlist", back_populates="user", lazy="dynamic")
    events = db.relationship("AnalyticsEvent", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    def __repr__(self) -> str:
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))
