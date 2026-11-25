"""jornada: batalhas PvP (#27, etapa J3)

Revision ID: b2c3d4e5f6a8
Revises: a1b2c3d4e5f7
Create Date: 2026-11-25 15:00:00

"""
from alembic import op
import sqlalchemy as sa


revision = 'b2c3d4e5f6a8'
down_revision = 'a1b2c3d4e5f7'
branch_labels = None
depends_on = None


def upgrade():
    if 'game_battles' in set(sa.inspect(op.get_bind()).get_table_names()):
        return
    op.create_table(
        'game_battles',
        sa.Column('id', sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column('fase', sa.SmallInteger(), nullable=False),
        sa.Column('casa', sa.SmallInteger(), nullable=False),
        sa.Column('desafiante_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('desafiado_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('criatura_desafiante', sa.Integer(), nullable=True),
        sa.Column('criatura_desafiado', sa.Integer(), nullable=True),
        sa.Column('isca_desafiante', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('isca_desafiado', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('dado_desafiante', sa.SmallInteger(), nullable=True),
        sa.Column('dado_desafiado', sa.SmallInteger(), nullable=True),
        sa.Column('total_desafiante', sa.SmallInteger(), nullable=True),
        sa.Column('total_desafiado', sa.SmallInteger(), nullable=True),
        sa.Column('vencedor_id', sa.Integer(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('itens_roubados', sa.JSON(), nullable=True),
        sa.Column('detalhe', sa.String(120), nullable=True),
        sa.Column('status', sa.String(12), nullable=False, server_default='pendente'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('resolved_at', sa.DateTime(), nullable=True),
    )
    op.create_index('ix_game_battles_desafiante_id', 'game_battles', ['desafiante_id'])
    op.create_index('ix_game_battles_desafiado_id', 'game_battles', ['desafiado_id'])
    op.create_index('ix_game_battles_status_created', 'game_battles', ['status', 'created_at'])


def downgrade():
    op.drop_table('game_battles')
