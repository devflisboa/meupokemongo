from ..config import now_br
from ..extensions import db


class UserPokemon(db.Model):
    """Exemplar individual do treinador (uma linha do export PokeGenie).

    UserCollection continua sendo o resumo por forma (owned/quantity/flags);
    aqui fica o detalhe de cada Pokémon: CP, IVs, nível, golpes, ranks PvP etc.
    """
    __tablename__ = "user_pokemon"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False, index=True)
    source = db.Column(db.String(20), nullable=False, default="pokegenie")

    nickname = db.Column(db.String(100), nullable=True)
    form_label = db.Column(db.String(50), nullable=True)      # coluna "Form" do PokeGenie (ex.: Alola)
    gender = db.Column(db.String(10), nullable=True)
    cp = db.Column(db.Integer, nullable=True)
    hp = db.Column(db.Integer, nullable=True)
    atk_iv = db.Column(db.Integer, nullable=True)
    def_iv = db.Column(db.Integer, nullable=True)
    sta_iv = db.Column(db.Integer, nullable=True)
    iv_pct = db.Column(db.Float, nullable=True)
    level = db.Column(db.Float, nullable=True)
    quick_move = db.Column(db.String(60), nullable=True)
    charge_move = db.Column(db.String(60), nullable=True)
    charge_move2 = db.Column(db.String(60), nullable=True)
    weight = db.Column(db.Float, nullable=True)
    height = db.Column(db.Float, nullable=True)
    is_lucky = db.Column(db.Boolean, default=False, nullable=False)
    is_shadow = db.Column(db.Boolean, default=False, nullable=False)
    is_purified = db.Column(db.Boolean, default=False, nullable=False)
    is_shiny = db.Column(db.Boolean, default=False, nullable=False)
    is_favorite = db.Column(db.Boolean, default=False, nullable=False)
    for_trade = db.Column(db.Boolean, default=False, nullable=False)
    rank_great = db.Column(db.Float, nullable=True)   # Rank % Great League
    rank_ultra = db.Column(db.Float, nullable=True)   # Rank % Ultra League
    rank_little = db.Column(db.Float, nullable=True)  # Rank % Little Cup
    catch_date = db.Column(db.String(30), nullable=True)
    scan_date = db.Column(db.String(30), nullable=True)
    raw = db.Column(db.JSON, nullable=True)           # linha original completa (nenhuma coluna se perde)
    created_at = db.Column(db.DateTime, default=now_br)

    form = db.relationship("Form")

    @property
    def is_perfect(self) -> bool:
        return (self.atk_iv, self.def_iv, self.sta_iv) == (15, 15, 15)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "nickname": self.nickname,
            "form_label": self.form_label,
            "gender": self.gender,
            "cp": self.cp,
            "hp": self.hp,
            "atk_iv": self.atk_iv,
            "def_iv": self.def_iv,
            "sta_iv": self.sta_iv,
            "iv_pct": self.iv_pct,
            "level": self.level,
            "quick_move": self.quick_move,
            "charge_move": self.charge_move,
            "charge_move2": self.charge_move2,
            "weight": self.weight,
            "height": self.height,
            "is_lucky": self.is_lucky,
            "is_shadow": self.is_shadow,
            "is_purified": self.is_purified,
            "is_shiny": self.is_shiny,
            "is_favorite": self.is_favorite,
            "for_trade": self.for_trade,
            "is_perfect": self.is_perfect,
            "rank_great": self.rank_great,
            "rank_ultra": self.rank_ultra,
            "rank_little": self.rank_little,
            "catch_date": self.catch_date,
            "scan_date": self.scan_date,
        }

    def __repr__(self) -> str:
        return f"<UserPokemon user={self.user_id} form={self.form_id} cp={self.cp}>"
