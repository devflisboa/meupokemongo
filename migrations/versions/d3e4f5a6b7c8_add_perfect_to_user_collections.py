"""add has_perfect (100% IV) to user_collections

Revision ID: d3e4f5a6b7c8
Revises: c2d3e4f5a6b7
Create Date: 2026-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'd3e4f5a6b7c8'
down_revision = 'c2d3e4f5a6b7'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('user_collections', sa.Column('has_perfect', sa.Boolean(), nullable=False, server_default='0'))


def downgrade():
    op.drop_column('user_collections', 'has_perfect')
