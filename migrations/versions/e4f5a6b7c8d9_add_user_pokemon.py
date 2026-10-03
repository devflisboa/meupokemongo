"""add user_pokemon (exemplares individuais do PokeGenie)

Revision ID: e4f5a6b7c8d9
Revises: d3e4f5a6b7c8
Create Date: 2026-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'e4f5a6b7c8d9'
down_revision = 'd3e4f5a6b7c8'
branch_labels = None
depends_on = None


def upgrade():
    op.create_table(
        'user_pokemon',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(20), nullable=False, server_default='pokegenie'),
        sa.Column('nickname', sa.String(100), nullable=True),
        sa.Column('form_label', sa.String(50), nullable=True),
        sa.Column('gender', sa.String(10), nullable=True),
        sa.Column('cp', sa.Integer(), nullable=True),
        sa.Column('hp', sa.Integer(), nullable=True),
        sa.Column('atk_iv', sa.Integer(), nullable=True),
        sa.Column('def_iv', sa.Integer(), nullable=True),
        sa.Column('sta_iv', sa.Integer(), nullable=True),
        sa.Column('iv_pct', sa.Float(), nullable=True),
        sa.Column('level', sa.Float(), nullable=True),
        sa.Column('quick_move', sa.String(60), nullable=True),
        sa.Column('charge_move', sa.String(60), nullable=True),
        sa.Column('charge_move2', sa.String(60), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('is_lucky', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_shadow', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_purified', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_shiny', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('is_favorite', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('for_trade', sa.Boolean(), nullable=False, server_default='0'),
        sa.Column('rank_great', sa.Float(), nullable=True),
        sa.Column('rank_ultra', sa.Float(), nullable=True),
        sa.Column('rank_little', sa.Float(), nullable=True),
        sa.Column('catch_date', sa.String(30), nullable=True),
        sa.Column('scan_date', sa.String(30), nullable=True),
        sa.Column('raw', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['user_id'], ['users.id']),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id']),
        sa.PrimaryKeyConstraint('id'),
    )
    op.create_index('ix_user_pokemon_user_id', 'user_pokemon', ['user_id'])
    op.create_index('ix_user_pokemon_form_id', 'user_pokemon', ['form_id'])


def downgrade():
    op.drop_index('ix_user_pokemon_form_id', table_name='user_pokemon')
    op.drop_index('ix_user_pokemon_user_id', table_name='user_pokemon')
    op.drop_table('user_pokemon')
