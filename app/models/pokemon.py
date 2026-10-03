from ..config import now_br
from ..extensions import db


class Species(db.Model):
    """Dados normativos de cada espécie Pokémon (sincronizados via Provider)."""
    __tablename__ = "species"

    id = db.Column(db.Integer, primary_key=True)          # número nacional Pokédex
    name = db.Column(db.String(100), nullable=False)
    name_pt = db.Column(db.String(100), nullable=True)
    generation = db.Column(db.Integer, nullable=False)
    is_legendary = db.Column(db.Boolean, default=False)
    is_mythical = db.Column(db.Boolean, default=False)
    base_happiness = db.Column(db.Integer, nullable=True)
    capture_rate = db.Column(db.Integer, nullable=True)
    synced_at = db.Column(db.DateTime, default=now_br)

    forms = db.relationship("Form", back_populates="species", lazy="dynamic")

    def __repr__(self) -> str:
        return f"<Species #{self.id} {self.name}>"


class Form(db.Model):
    """Formas de uma espécie (normal, alolan, galarian, shiny, etc.)."""
    __tablename__ = "forms"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    species_id = db.Column(db.Integer, db.ForeignKey("species.id"), nullable=False, index=True)
    form_name = db.Column(db.String(50), nullable=False, default="normal")
    type1 = db.Column(db.String(20), nullable=True)
    type2 = db.Column(db.String(20), nullable=True)
    sprite_url = db.Column(db.String(255), nullable=True)
    is_shiny_available = db.Column(db.Boolean, default=False)

    species = db.relationship("Species", back_populates="forms")
    collection_entries = db.relationship("UserCollection", back_populates="form", lazy="dynamic")

    __table_args__ = (
        db.UniqueConstraint("species_id", "form_name", name="uq_species_form"),
    )

    @property
    def label(self) -> str:
        """'' para a forma normal; 'Alola', 'Mega X', 'Gigantamax', 'Boné Original'... (#14)."""
        from ..data.regional import form_label
        return form_label(self.form_name)

    @property
    def category(self) -> str | None:
        """None (normal) | 'regional' | 'mega' | 'gmax' | 'especial'."""
        from ..data.regional import form_category
        return form_category(self.form_name)

    @property
    def display_name(self) -> str:
        """'Rattata' · 'Rattata de Alola' · 'Mega Charizard X' · 'Charizard Gigantamax'."""
        from ..data.regional import form_display_name
        name = (self.species.name_pt or self.species.name).removesuffix("-normal").replace("-", " ").title()
        return form_display_name(name, self.form_name)

    def __repr__(self) -> str:
        return f"<Form {self.species_id} {self.form_name}>"


class EvolutionChain(db.Model):
    """Relação de evolução entre formas."""
    __tablename__ = "evolution_chains"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    from_form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False)
    to_form_id = db.Column(db.Integer, db.ForeignKey("forms.id"), nullable=False)
    candy_cost = db.Column(db.Integer, nullable=True)
    candy_name = db.Column(db.String(50), nullable=True)

    from_form = db.relationship("Form", foreign_keys=[from_form_id])
    to_form = db.relationship("Form", foreign_keys=[to_form_id])

    def __repr__(self) -> str:
        return f"<EvolutionChain {self.from_form_id} -> {self.to_form_id}>"


class PokemonCache(db.Model):
    """Cache raw da PokeAPI para evitar chamadas repetidas (RB12)."""
    __tablename__ = "pokemon_cache"

    cache_key = db.Column(db.String(100), primary_key=True)
    payload = db.Column(db.JSON, nullable=False)
    cached_at = db.Column(db.DateTime, default=now_br, onupdate=now_br)
