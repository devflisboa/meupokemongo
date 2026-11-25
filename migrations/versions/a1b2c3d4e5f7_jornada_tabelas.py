"""jornada: tabelas do jogo de tabuleiro (#27, etapa J1)

Revision ID: a1b2c3d4e5f7
Revises: f5f195691630
Create Date: 2026-11-25 12:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'a1b2c3d4e5f7'
down_revision = 'f5f195691630'
branch_labels = None
depends_on = None


def upgrade():
    existing = set(sa.inspect(op.get_bind()).get_table_names())

    if 'game_players' not in existing:
        op.create_table(
            'game_players',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
            sa.Column('fase', sa.SmallInteger(), nullable=False, server_default='1'),
            sa.Column('posicao', sa.SmallInteger(), nullable=False, server_default='0'),
            sa.Column('volta', sa.SmallInteger(), nullable=False, server_default='1'),
            sa.Column('pp', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('energia', sa.SmallInteger(), nullable=False, server_default='0'),
            sa.Column('energia_dia', sa.Date(), nullable=True),
            sa.Column('sequencia_dias', sa.SmallInteger(), nullable=False, server_default='0'),
            sa.Column('ultimo_dia_jogado', sa.Date(), nullable=True),
            sa.Column('insignias', sa.JSON(), nullable=False),
            sa.Column('efeitos', sa.JSON(), nullable=False),
            sa.Column('acao_pendente', sa.JSON(), nullable=True),
            sa.Column('baralho_eventos', sa.JSON(), nullable=False),
            sa.Column('titulo_fase1_em', sa.DateTime(), nullable=True),
            sa.Column('last_seen', sa.DateTime(), nullable=True),
            sa.Column('created_at', sa.DateTime(), nullable=False),
            sa.Column('updated_at', sa.DateTime(), nullable=True),
        )
        op.create_index('ix_game_players_fase_posicao', 'game_players', ['fase', 'posicao'])

    if 'game_creatures' not in existing:
        op.create_table(
            'game_creatures',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('creature_key', sa.String(40), nullable=False),
            sa.Column('fase', sa.SmallInteger(), nullable=False),
            sa.Column('estagio', sa.SmallInteger(), nullable=False),
            sa.Column('volta', sa.SmallInteger(), nullable=False),
            sa.Column('slot', sa.SmallInteger(), nullable=True),
            sa.Column('desmaiada', sa.Boolean(), nullable=False, server_default=sa.false()),
            sa.Column('captured_at', sa.DateTime(), nullable=False),
            sa.UniqueConstraint('user_id', 'creature_key', name='uq_game_creature_user'),
        )
        op.create_index('ix_game_creatures_user_id', 'game_creatures', ['user_id'])

    if 'game_escapes' not in existing:
        op.create_table(
            'game_escapes',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
            sa.Column('creature_key', sa.String(40), primary_key=True),
            sa.Column('volta', sa.SmallInteger(), primary_key=True),
        )

    if 'game_items' not in existing:
        op.create_table(
            'game_items',
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), primary_key=True),
            sa.Column('item_key', sa.String(20), primary_key=True),
            sa.Column('qtd', sa.SmallInteger(), nullable=False, server_default='0'),
        )

    if 'game_turns' not in existing:
        op.create_table(
            'game_turns',
            sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column('user_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('fase', sa.SmallInteger(), nullable=False),
            sa.Column('tipo', sa.String(20), nullable=False),
            sa.Column('dado', sa.SmallInteger(), nullable=True),
            sa.Column('de', sa.SmallInteger(), nullable=True),
            sa.Column('para', sa.SmallInteger(), nullable=True),
            sa.Column('resultado', sa.JSON(), nullable=True),
            sa.Column('pp_delta', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('created_at', sa.DateTime(), nullable=False),
        )
        op.create_index('ix_game_turns_user_id', 'game_turns', ['user_id'])
        op.create_index('ix_game_turns_fase_id', 'game_turns', ['fase', 'id'])

    if 'game_discoveries' not in existing:
        op.create_table(
            'game_discoveries',
            sa.Column('creature_key', sa.String(40), primary_key=True),
            sa.Column('discovered_by', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
            sa.Column('discovered_at', sa.DateTime(), nullable=False),
        )


def downgrade():
    for t in ('game_discoveries', 'game_turns', 'game_items', 'game_escapes', 'game_creatures', 'game_players'):
        op.drop_table(t)
