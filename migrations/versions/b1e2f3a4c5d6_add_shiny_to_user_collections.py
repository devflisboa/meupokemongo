"""add shiny to user_collections

Revision ID: b1e2f3a4c5d6
Revises: cf05efdffcd3
Create Date: 2026-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'b1e2f3a4c5d6'
down_revision = 'cf05efdffcd3'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_collections', sa.Column('has_shiny', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('user_collections', sa.Column('shiny_qty', sa.Integer(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('user_collections', 'shiny_qty')
    op.drop_column('user_collections', 'has_shiny')
