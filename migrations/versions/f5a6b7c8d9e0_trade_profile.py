"""perfil de troca (#23): estado, cidade, troca à distância, WhatsApp com consentimento

Também aplica a decisão D1/D2: visibilidade "friends" deixa de existir na prática
e migra para "public" (todos se enxergam).

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-10-02 00:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


revision = 'f5a6b7c8d9e0'
down_revision = 'e4f5a6b7c8d9'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('state', sa.String(2), nullable=True))
    op.add_column('users', sa.Column('city', sa.String(80), nullable=True))
    op.add_column('users', sa.Column('can_trade_remote', sa.Boolean(), nullable=False, server_default='0'))
    op.add_column('users', sa.Column('whatsapp', sa.String(20), nullable=True))
    op.add_column('users', sa.Column('allow_whatsapp', sa.Boolean(), nullable=False, server_default='0'))
    op.execute("UPDATE users SET visibility = 'public' WHERE visibility = 'friends'")


def downgrade():
    op.drop_column('users', 'allow_whatsapp')
    op.drop_column('users', 'whatsapp')
    op.drop_column('users', 'can_trade_remote')
    op.drop_column('users', 'city')
    op.drop_column('users', 'state')
