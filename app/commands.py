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


def register_commands(app):
    app.cli.add_command(sync_pokemon_cmd)
    app.cli.add_command(create_admin_cmd)
    app.cli.add_command(sync_candy_cmd)
