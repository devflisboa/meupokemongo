"""add avatar to users

Revision ID: c2d3e4f5a6b7
Revises: b1e2f3a4c5d6
Create Date: 2026-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'c2d3e4f5a6b7'
down_revision = 'b1e2f3a4c5d6'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('avatar', sa.LargeBinary(), nullable=True))
    op.add_column('users', sa.Column('avatar_mime', sa.String(30), nullable=True))


def downgrade():
    op.drop_column('users', 'avatar_mime')
    op.drop_column('users', 'avatar')
