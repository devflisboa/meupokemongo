"""add anime temporadas episodios

Revision ID: f5f195691630
Revises: a7b8c9d0e1f2
Create Date: 2026-10-08 00:19:54.327159

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f5f195691630'
down_revision = 'a7b8c9d0e1f2'
branch_labels = None
depends_on = None


def upgrade():
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    existing_tables = set(inspector.get_table_names())

    # Novas tabelas de anime — criadas só se não existirem
    if 'anime_temporadas' not in existing_tables:
        op.create_table('anime_temporadas',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('codigo', sa.String(length=10), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=200), nullable=False),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('capa_url', sa.String(length=500), nullable=True),
        sa.Column('ordem', sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint('id')
        )

    if 'anime_episodios' not in existing_tables:
        op.create_table('anime_episodios',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('temporada_id', sa.Integer(), nullable=False),
        sa.Column('numero', sa.Integer(), nullable=False),
        sa.Column('titulo', sa.String(length=300), nullable=False),
        sa.Column('titulo_original', sa.String(length=300), nullable=True),
        sa.Column('descricao', sa.Text(), nullable=True),
        sa.Column('arquivo', sa.String(length=500), nullable=True),
        sa.Column('duracao_seg', sa.Integer(), nullable=True),
        sa.Column('thumbnail_url', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['temporada_id'], ['anime_temporadas.id'], ),
        sa.PrimaryKeyConstraint('id')
        )

    # user_pokemon pode já existir em prod (foi criada manualmente antes desta migração)
    if 'user_pokemon' not in existing_tables:
        op.create_table('user_pokemon',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('form_id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('nickname', sa.String(length=100), nullable=True),
        sa.Column('form_label', sa.String(length=50), nullable=True),
        sa.Column('gender', sa.String(length=10), nullable=True),
        sa.Column('cp', sa.Integer(), nullable=True),
        sa.Column('hp', sa.Integer(), nullable=True),
        sa.Column('atk_iv', sa.Integer(), nullable=True),
        sa.Column('def_iv', sa.Integer(), nullable=True),
        sa.Column('sta_iv', sa.Integer(), nullable=True),
        sa.Column('iv_pct', sa.Float(), nullable=True),
        sa.Column('level', sa.Float(), nullable=True),
        sa.Column('quick_move', sa.String(length=60), nullable=True),
        sa.Column('charge_move', sa.String(length=60), nullable=True),
        sa.Column('charge_move2', sa.String(length=60), nullable=True),
        sa.Column('weight', sa.Float(), nullable=True),
        sa.Column('height', sa.Float(), nullable=True),
        sa.Column('is_lucky', sa.Boolean(), nullable=False),
        sa.Column('is_shadow', sa.Boolean(), nullable=False),
        sa.Column('is_purified', sa.Boolean(), nullable=False),
        sa.Column('is_shiny', sa.Boolean(), nullable=False),
        sa.Column('is_favorite', sa.Boolean(), nullable=False),
        sa.Column('for_trade', sa.Boolean(), nullable=False),
        sa.Column('rank_great', sa.Float(), nullable=True),
        sa.Column('rank_ultra', sa.Float(), nullable=True),
        sa.Column('rank_little', sa.Float(), nullable=True),
        sa.Column('catch_date', sa.String(length=30), nullable=True),
        sa.Column('scan_date', sa.String(length=30), nullable=True),
        sa.Column('raw', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['form_id'], ['forms.id'], ),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ),
        sa.PrimaryKeyConstraint('id')
        )
        with op.batch_alter_table('user_pokemon', schema=None) as batch_op:
            batch_op.create_index(batch_op.f('ix_user_pokemon_form_id'), ['form_id'], unique=False)
            batch_op.create_index(batch_op.f('ix_user_pokemon_user_id'), ['user_id'], unique=False)

    # Colunas que também podem já existir (adicionadas manualmente em prod antes desta revisão)
    uc_cols = {c['name'] for c in inspector.get_columns('user_collections')}
    with op.batch_alter_table('user_collections', schema=None) as batch_op:
        if 'has_shiny' not in uc_cols:
            batch_op.add_column(sa.Column('has_shiny', sa.Boolean(), nullable=False))
        if 'shiny_qty' not in uc_cols:
            batch_op.add_column(sa.Column('shiny_qty', sa.Integer(), nullable=False))
        if 'has_perfect' not in uc_cols:
            batch_op.add_column(sa.Column('has_perfect', sa.Boolean(), nullable=False))

    u_cols = {c['name'] for c in inspector.get_columns('users')}
    with op.batch_alter_table('users', schema=None) as batch_op:
        if 'avatar' not in u_cols:
            batch_op.add_column(sa.Column('avatar', sa.LargeBinary(), nullable=True))
        if 'avatar_mime' not in u_cols:
            batch_op.add_column(sa.Column('avatar_mime', sa.String(length=30), nullable=True))
        if 'state' not in u_cols:
            batch_op.add_column(sa.Column('state', sa.String(length=2), nullable=True))
        if 'city' not in u_cols:
            batch_op.add_column(sa.Column('city', sa.String(length=80), nullable=True))
        if 'can_trade_remote' not in u_cols:
            batch_op.add_column(sa.Column('can_trade_remote', sa.Boolean(), nullable=False))
        if 'whatsapp' not in u_cols:
            batch_op.add_column(sa.Column('whatsapp', sa.String(length=20), nullable=True))
        if 'allow_whatsapp' not in u_cols:
            batch_op.add_column(sa.Column('allow_whatsapp', sa.Boolean(), nullable=False))
        if 'favorite_species_id' not in u_cols:
            batch_op.add_column(sa.Column('favorite_species_id', sa.Integer(), nullable=True))
            batch_op.create_foreign_key(None, 'species', ['favorite_species_id'], ['id'])


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('users', schema=None) as batch_op:
        # WARNING: constraint name is None; this directive will fail as
        # rendered.  Add a name, or use a naming convention; see
        # https://alembic.sqlalchemy.org/en/latest/naming.html
        batch_op.drop_constraint(None, type_='foreignkey')
        batch_op.drop_column('favorite_species_id')
        batch_op.drop_column('allow_whatsapp')
        batch_op.drop_column('whatsapp')
        batch_op.drop_column('can_trade_remote')
        batch_op.drop_column('city')
        batch_op.drop_column('state')
        batch_op.drop_column('avatar_mime')
        batch_op.drop_column('avatar')

    with op.batch_alter_table('user_collections', schema=None) as batch_op:
        batch_op.drop_column('has_perfect')
        batch_op.drop_column('shiny_qty')
        batch_op.drop_column('has_shiny')

    with op.batch_alter_table('user_pokemon', schema=None) as batch_op:
        batch_op.drop_index(batch_op.f('ix_user_pokemon_user_id'))
        batch_op.drop_index(batch_op.f('ix_user_pokemon_form_id'))

    op.drop_table('user_pokemon')
    op.drop_table('anime_episodios')
    op.drop_table('anime_temporadas')
    # ### end Alembic commands ###
