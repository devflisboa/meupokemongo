import os
from flask import Flask
from .config import config_map
from .extensions import db, migrate, login_manager, csrf, limiter


def create_app(env: str | None = None) -> Flask:
    env = env or os.environ.get("FLASK_ENV", "development")
    cfg = config_map.get(env, config_map["development"])()

    app = Flask(__name__, instance_relative_config=False)
    app.config.from_object(cfg)
    app.config["SQLALCHEMY_DATABASE_URI"] = cfg.SQLALCHEMY_DATABASE_URI

    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    csrf.init_app(app)
    limiter.init_app(app)

    from .models import user, pokemon, collection, wishlist, friendship, trade, event  # noqa: F401

    from .blueprints.main import bp as main_bp
    from .blueprints.auth import bp as auth_bp
    from .blueprints.pokedex import bp as pokedex_bp
    from .blueprints.collection import bp as collection_bp
    from .blueprints.trades import bp as trades_bp
    from .blueprints.friends import bp as friends_bp
    from .blueprints.import_ import bp as import_bp
    from .blueprints.admin import bp as admin_bp
    from .blueprints.wishlist import bp as wishlist_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(auth_bp, url_prefix="/auth")
    app.register_blueprint(pokedex_bp, url_prefix="/pokedex")
    app.register_blueprint(collection_bp, url_prefix="/collection")
    app.register_blueprint(trades_bp, url_prefix="/trades")
    app.register_blueprint(friends_bp, url_prefix="/friends")
    app.register_blueprint(import_bp, url_prefix="/import")
    app.register_blueprint(admin_bp, url_prefix="/admin")
    app.register_blueprint(wishlist_bp, url_prefix="/wishlist")

    from .commands import register_commands
    register_commands(app)

    @app.template_filter("poke_name")
    def poke_name_filter(name: str) -> str:
        if not name:
            return ""
        return name.replace("-", " ").title()

    return app
