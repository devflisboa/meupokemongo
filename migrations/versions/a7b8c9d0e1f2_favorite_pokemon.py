"""Pokémon favorito do treinador (adesivo no Trade Binder)

Revision ID: a7b8c9d0e1f2
Revises: f5a6b7c8d9e0
Create Date: 2026-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'a7b8c9d0e1f2'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('favorite_species_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_users_favorite_species', 'users', 'species', ['favorite_species_id'], ['id'])


def downgrade():
    op.drop_constraint('fk_users_favorite_species', 'users', type_='foreignkey')
    op.drop_column('users', 'favorite_species_id')
