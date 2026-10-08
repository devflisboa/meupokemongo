import click
from flask import current_app
from flask.cli import with_appcontext
from .extensions import db
from .models.user import User


@click.command("sync-pokemon")
@click.option("--limit", default=151, show_default=True, help="Número de Pokémon a sincronizar.")
@click.option("--offset", default=0, show_default=True, help="Offset na lista da PokeAPI.")
@with_appcontext
def sync_pokemon_cmd(limit, offset):
    """Sincroniza dados da PokeAPI → MySQL (species, forms, evolution_chains)."""
    from .services.sync_service import sync_pokemon
    click.echo(f"Iniciando sync: limit={limit} offset={offset}")
    report = sync_pokemon(limit=limit, offset=offset, log=click.echo)
    if report["errors"]:
        click.echo(f"\nErros ({len(report['errors'])}):")
        for e in report["errors"]:
            click.echo(f"  • {e}")


@click.command("sync-candy")
@with_appcontext
def sync_candy_cmd():
    """Preenche o custo de doces das evoluções (fonte: pogoapi.net)."""
    from .services.candy_service import sync_candy_costs
    sync_candy_costs(log=click.echo)


@click.command("sync-forms")
@with_appcontext
def sync_forms_cmd():
    """Importa formas alternativas da PokeAPI: regionais, Mega, Gigantamax e especiais."""
    from .services.sync_service import sync_regional_forms
    sync_regional_forms(log=click.echo)


@click.command("create-admin")
@click.argument("username")
@click.argument("email")
@click.argument("password")
@with_appcontext
def create_admin_cmd(username, email, password):
    """Cria um usuário administrador. Uso: flask create-admin <user> <email> <senha>"""
    existing = db.session.query(User).filter_by(username=username).first()
    if existing:
        click.echo(f"Usuário '{username}' já existe.")
        return
    user = User(username=username, email=email, is_admin=True)
    user.set_password(password)
    db.session.add(user)
    db.session.commit()
    click.echo(f"Admin '{username}' criado com sucesso!")


_SHINIES_SEED = [
    # (nome_en, cp, iv_pct, atk_iv, def_iv, sta_iv)
    ("gyarados",   3197, 100.0, 15, 15, 15),
    ("metagross",  2200, None,  None, None, None),
    ("entei",      1968, 94.0,  None, None, None),
    ("entei",      1947, None,  None, None, None),
    ("latias",     1941, None,  None, None, None),
    ("latias",     1938, None,  None, None, None),
    ("blaziken",   1667, None,  None, None, None),
    ("gengar",     1604, 82.0,  None, None, None),
    ("swampert",   1534, None,  None, None, None),
    ("lapras",     1458, None,  None, None, None),
    ("latias",     1455, None,  None, None, None),
    ("arcanine",   1275, None,  None, None, None),
    ("flareon",    1275, 87.0,  None, None, None),
    ("metang",     1146, None,  None, None, None),
    ("rapidash",   1083, None,  None, None, None),
    ("flamigo",    1002, None,  None, None, None),
    ("larvesta",    841, 92.0,  None, None, None),
    ("metang",      810, None,  None, None, None),
    ("beldum",      677, None,  None, None, None),
    ("quilava",     631, None,  None, None, None),
    ("grubbin",     528, None,  None, None, None),
    ("charmander",  467, None,  None, None, None),
    ("marowak",     461, None,  None, None, None),
    ("thievul",     381, None,  None, None, None),
    ("snubbull",    313, None,  None, None, None),
    ("cyndaquil",   294, None,  None, None, None),
    ("cyndaquil",   259, None,  None, None, None),
    ("gible",       256, None,  None, None, None),
    ("aipom",       236, None,  None, None, None),
    ("lampent",     210, None,  None, None, None),
    ("noibat",      200, None,  None, None, None),
    ("mudkip",      129, None,  None, None, None),
    ("herdier",     100, None,  None, None, None),
    ("torchic",      99, None,  None, None, None),
    ("hitmonchan",   31, None,  None, None, None),
]


@click.command("seed-shinies")
@click.option("--username", required=True, help="Username do treinador dono dos Brilhantes.")
@with_appcontext
def seed_shinies_cmd(username):
    """Cadastra manualmente os 35 Brilhantes do treinador na tabela user_pokemon."""
    from .models.pokemon import Form, Species
    from .models.collection import UserCollection
    from .models.individual import UserPokemon

    user = db.session.query(User).filter_by(username=username).first()
    if not user:
        click.echo(f"Usuário '{username}' não encontrado.")
        return

    inserted, skipped, not_found = 0, 0, []

    for nome, cp, iv_pct, atk, dfn, sta in _SHINIES_SEED:
        form = (
            db.session.query(Form)
            .join(Species, Species.id == Form.species_id)
            .filter(
                db.func.lower(Species.name) == nome.lower(),
                Form.form_name == "normal",
            )
            .first()
        )
        if not form:
            not_found.append(nome)
            continue

        already = db.session.query(UserPokemon).filter_by(
            user_id=user.id, form_id=form.id, cp=cp, is_shiny=True
        ).first()
        if already:
            click.echo(f"  ~ {nome} CP {cp} já existe, pulando.")
            skipped += 1
            continue

        ind = UserPokemon(
            user_id=user.id,
            form_id=form.id,
            source="manual",
            cp=cp,
            atk_iv=atk,
            def_iv=dfn,
            sta_iv=sta,
            iv_pct=iv_pct,
            is_shiny=True,
        )
        db.session.add(ind)

        entry = db.session.query(UserCollection).filter_by(
            user_id=user.id, form_id=form.id
        ).first()
        if not entry:
            entry = UserCollection(user_id=user.id, form_id=form.id, quantity=0)
            db.session.add(entry)
        entry.owned = True
        entry.quantity = (entry.quantity or 0) + 1
        entry.has_shiny = True
        entry.shiny_qty = (entry.shiny_qty or 0) + 1
        if atk == 15 and dfn == 15 and sta == 15:
            entry.has_perfect = True

        inserted += 1
        click.echo(f"  + {nome.capitalize()} CP {cp}")

    db.session.commit()
    click.echo(f"\nPronto! {inserted} inseridos, {skipped} já existiam.")
    if not_found:
        click.echo(f"Não encontrados no banco: {not_found}")


def register_commands(app):
    app.cli.add_command(sync_pokemon_cmd)
    app.cli.add_command(create_admin_cmd)
    app.cli.add_command(sync_candy_cmd)
    app.cli.add_command(sync_forms_cmd)
    app.cli.add_command(seed_shinies_cmd)
