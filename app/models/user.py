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
    avatar = db.Column(db.LargeBinary, nullable=True)
    avatar_mime = db.Column(db.String(30), nullable=True)
    # "Aparecer para outros treinadores nas trocas": public = sim, private = não.
    # "friends" não é mais oferecido (D1/D2 do backlog) — mantido no enum só por reversibilidade.
    visibility = db.Column(db.Enum("public", "friends", "private"), default="public", nullable=False)

    # Perfil de troca (#23) — troca no GO exige proximidade, por isso cidade importa
    state = db.Column(db.String(2), nullable=True)            # UF (IBGE)
    city = db.Column(db.String(80), nullable=True)            # município (lista IBGE)
    can_trade_remote = db.Column(db.Boolean, default=False, nullable=False)  # "Topo trocar à distância"
    whatsapp = db.Column(db.String(20), nullable=True)        # só dígitos, com DDI 55
    allow_whatsapp = db.Column(db.Boolean, default=False, nullable=False)    # consentimento explícito (LGPD)

    # Pokémon favorito — vira "adesivo" animado no Trade Binder
    favorite_species_id = db.Column(db.Integer, db.ForeignKey("species.id"), nullable=True)
    favorite_species = db.relationship("Species")
    created_at = db.Column(db.DateTime, default=now_br, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_br, onupdate=now_br)

    collection = db.relationship("UserCollection", back_populates="user", lazy="dynamic")
    wishlist = db.relationship("Wishlist", back_populates="user", lazy="dynamic")
    events = db.relationship("AnalyticsEvent", back_populates="user", lazy="dynamic")

    def set_password(self, password: str) -> None:
        self.password_hash = generate_password_hash(password)

    def check_password(self, password: str) -> bool:
        return check_password_hash(self.password_hash, password)

    @property
    def show_in_trades(self) -> bool:
        return self.visibility != "private"

    @property
    def location_label(self) -> str:
        if self.city and self.state:
            return f"{self.city}/{self.state}"
        return self.state or ""

    @property
    def favorite_gif_url(self) -> str | None:
        """GIF animado (sprites estilo Showdown da PokeAPI); a página cai na arte oficial se não existir."""
        if not self.favorite_species_id:
            return None
        return ("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/showdown/"
                f"{self.favorite_species_id}.gif")

    @property
    def favorite_art_url(self) -> str | None:
        if not self.favorite_species_id:
            return None
        return ("https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/"
                f"{self.favorite_species_id}.png")

    @property
    def needs_onboarding(self) -> bool:
        """Perfil de troca incompleto: sem código de amigo ou sem cidade."""
        return not (self.trainer_code and self.city)

    def whatsapp_url(self, text: str = "") -> str | None:
        """Link wa.me só com consentimento e número válido."""
        if not (self.allow_whatsapp and self.whatsapp):
            return None
        from urllib.parse import quote
        return f"https://wa.me/{self.whatsapp}" + (f"?text={quote(text)}" if text else "")

    def __repr__(self) -> str:
        return f"<User {self.username}>"


@login_manager.user_loader
def load_user(user_id: str) -> User | None:
    return db.session.get(User, int(user_id))
