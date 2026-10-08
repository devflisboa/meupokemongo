from ..extensions import db


class Temporada(db.Model):
    __tablename__ = "anime_temporadas"

    id          = db.Column(db.Integer, primary_key=True)
    codigo      = db.Column(db.String(10),  nullable=False)        # JN, OS, AG, …
    numero      = db.Column(db.Integer,     nullable=False)        # 1, 2, 3, …
    titulo      = db.Column(db.String(200), nullable=False)
    descricao   = db.Column(db.Text)
    capa_url    = db.Column(db.String(500))
    ordem       = db.Column(db.Integer, default=0)

    episodios   = db.relationship(
        "Episodio", backref="temporada",
        order_by="Episodio.numero", lazy="dynamic"
    )

    def total_episodios(self):
        return self.episodios.count()


class Episodio(db.Model):
    __tablename__ = "anime_episodios"

    id             = db.Column(db.Integer, primary_key=True)
    temporada_id   = db.Column(db.Integer, db.ForeignKey("anime_temporadas.id"), nullable=False)
    numero         = db.Column(db.Integer, nullable=False)
    titulo         = db.Column(db.String(300), nullable=False)
    titulo_original= db.Column(db.String(300))
    descricao      = db.Column(db.Text)
    arquivo        = db.Column(db.String(500))   # nome do arquivo .mp4 na pasta de vídeos
    duracao_seg    = db.Column(db.Integer)        # duração em segundos
    thumbnail_url  = db.Column(db.String(500))

    @property
    def duracao_fmt(self):
        if not self.duracao_seg:
            return ""
        m, s = divmod(self.duracao_seg, 60)
        return f"{m}:{s:02d}"

    @property
    def numero_fmt(self):
        return f"{self.numero:02d}"
