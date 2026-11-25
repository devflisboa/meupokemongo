"""Tabelas do jogo Jornada (#27) — ver docs/SPEC-JORNADA.md §10.

O banco guarda só o ESTADO dos jogadores. O conteúdo (criaturas, casas, itens, eventos)
fica em app/data/jornada/*.json e é referenciado por chave (creature_key, item_key...).

Atenção com colunas JSON: o SQLAlchemy não detecta mutação in-place (lista.append, dict[k]=v).
Sempre reatribua o valor inteiro (ex.: player.insignias = [*player.insignias, "vento"]).
"""
from ..config import now_br
from ..extensions import db


class GamePlayer(db.Model):
    """Estado do jogador no tabuleiro (1 linha por usuário)."""
    __tablename__ = "game_players"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    fase = db.Column(db.SmallInteger, default=1, nullable=False)
    posicao = db.Column(db.SmallInteger, default=0, nullable=False)
    volta = db.Column(db.SmallInteger, default=1, nullable=False)
    pp = db.Column(db.Integer, default=0, nullable=False)
    energia = db.Column(db.SmallInteger, default=0, nullable=False)
    energia_dia = db.Column(db.Date, nullable=True)          # último dia em que a recarga foi aplicada
    sequencia_dias = db.Column(db.SmallInteger, default=0, nullable=False)
    ultimo_dia_jogado = db.Column(db.Date, nullable=True)
    insignias = db.Column(db.JSON, nullable=False, default=list)
    efeitos = db.Column(db.JSON, nullable=False, default=dict)          # ex.: {"sorte": 1}
    acao_pendente = db.Column(db.JSON, nullable=True)                   # máquina de estados (§11)
    baralho_eventos = db.Column(db.JSON, nullable=False, default=list)  # cartas restantes
    titulo_fase1_em = db.Column(db.DateTime, nullable=True)
    last_seen = db.Column(db.DateTime, default=now_br)
    created_at = db.Column(db.DateTime, default=now_br, nullable=False)
    updated_at = db.Column(db.DateTime, default=now_br, onupdate=now_br)

    user = db.relationship("User")

    __table_args__ = (
        db.Index("ix_game_players_fase_posicao", "fase", "posicao"),
    )

    def __repr__(self) -> str:
        return f"<GamePlayer user={self.user_id} fase={self.fase} casa={self.posicao} volta={self.volta} pp={self.pp}>"


class GameCreature(db.Model):
    """Criatura capturada. A UNIQUE (user_id, creature_key) garante: nunca repetida."""
    __tablename__ = "game_creatures"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    creature_key = db.Column(db.String(40), nullable=False)
    fase = db.Column(db.SmallInteger, nullable=False)
    estagio = db.Column(db.SmallInteger, nullable=False)
    volta = db.Column(db.SmallInteger, nullable=False)
    slot = db.Column(db.SmallInteger, nullable=True)          # 1–6 = time; NULL = reserva
    desmaiada = db.Column(db.Boolean, default=False, nullable=False)
    captured_at = db.Column(db.DateTime, default=now_br, nullable=False)

    __table_args__ = (
        db.UniqueConstraint("user_id", "creature_key", name="uq_game_creature_user"),
    )


class GameEscape(db.Model):
    """Criatura que fugiu do jogador numa volta — não reaparece na mesma volta."""
    __tablename__ = "game_escapes"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    creature_key = db.Column(db.String(40), primary_key=True)
    volta = db.Column(db.SmallInteger, primary_key=True)


class GameItem(db.Model):
    """Itens na mão do jogador."""
    __tablename__ = "game_items"

    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), primary_key=True)
    item_key = db.Column(db.String(20), primary_key=True)
    qtd = db.Column(db.SmallInteger, default=0, nullable=False)


class GameTurn(db.Model):
    """Log de toda ação do jogo: auditoria, feed e calibragem do balanceamento."""
    __tablename__ = "game_turns"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    fase = db.Column(db.SmallInteger, nullable=False)
    tipo = db.Column(db.String(20), nullable=False)          # movimento/captura/item/time/desafio
    dado = db.Column(db.SmallInteger, nullable=True)
    de = db.Column(db.SmallInteger, nullable=True)
    para = db.Column(db.SmallInteger, nullable=True)
    resultado = db.Column(db.JSON, nullable=True)
    pp_delta = db.Column(db.Integer, default=0, nullable=False)
    created_at = db.Column(db.DateTime, default=now_br, nullable=False)

    __table_args__ = (
        db.Index("ix_game_turns_fase_id", "fase", "id"),
    )


class GameDiscovery(db.Model):
    """Primeiro treinador do servidor a encontrar cada criatura (catálogo compartilhado)."""
    __tablename__ = "game_discoveries"

    creature_key = db.Column(db.String(40), primary_key=True)
    discovered_by = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    discovered_at = db.Column(db.DateTime, default=now_br, nullable=False)


class GameBattle(db.Model):
    """Batalha PvP assíncrona (J3) — ver SPEC-JORNADA.md §5.8."""
    __tablename__ = "game_battles"

    id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    fase = db.Column(db.SmallInteger, nullable=False)
    casa = db.Column(db.SmallInteger, nullable=False)
    desafiante_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    desafiado_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False, index=True)
    criatura_desafiante = db.Column(db.Integer, nullable=True)     # game_creatures.id
    criatura_desafiado = db.Column(db.Integer, nullable=True)
    isca_desafiante = db.Column(db.Boolean, default=False, nullable=False)
    isca_desafiado = db.Column(db.Boolean, default=False, nullable=False)
    dado_desafiante = db.Column(db.SmallInteger, nullable=True)
    dado_desafiado = db.Column(db.SmallInteger, nullable=True)
    total_desafiante = db.Column(db.SmallInteger, nullable=True)
    total_desafiado = db.Column(db.SmallInteger, nullable=True)
    vencedor_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=True)
    itens_roubados = db.Column(db.JSON, nullable=True)
    detalhe = db.Column(db.String(120), nullable=True)               # ex.: "W.O. — sem criatura saudável"
    status = db.Column(db.String(12), default="pendente", nullable=False)  # pendente/resolvida/expirada
    created_at = db.Column(db.DateTime, default=now_br, nullable=False)
    resolved_at = db.Column(db.DateTime, nullable=True)

    desafiante = db.relationship("User", foreign_keys=[desafiante_id])
    desafiado = db.relationship("User", foreign_keys=[desafiado_id])

    __table_args__ = (
        db.Index("ix_game_battles_status_created", "status", "created_at"),
    )
