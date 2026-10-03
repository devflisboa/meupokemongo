"""
Servidor isolado para os testes Cypress (E2E).

- Banco SQLite novo a cada execução (nunca toca MySQL local nem produção)
- Pokédex real (species/forms/evolutions exportadas de produção) em cypress/fixtures/pokedex_seed.json
- Treinadores de teste com cenários conhecidos (shiny, 100%, exemplares, evoluções, trocas)

Uso:  python scripts/e2e_server.py            (sobe em http://localhost:5001)
      npx cypress run
"""
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

DB_DIR = Path(os.environ.get("E2E_DB_DIR", r"D:\.ClaudeCode\.temp"))
DB_FILE = DB_DIR / "meupokemongo_e2e.db"
PORT = int(os.environ.get("E2E_PORT", "5001"))

# Credenciais SÓ de teste — usadas também em cypress/support/commands.js
E2E_USER, E2E_PASSWORD = "felipe", "e2e-senha-teste"
E2E_FRIEND = "misty"

from app.config import ProductionConfig, config_map  # noqa: E402


class E2EConfig(ProductionConfig):
    """Igual à produção (CSRF ligado, sem DEBUG), mas em SQLite descartável."""
    SECRET_KEY = "e2e-only"
    SQLALCHEMY_DATABASE_URI = f"sqlite:///{DB_FILE.as_posix()}"


config_map["e2e"] = E2EConfig

from app import create_app  # noqa: E402
from app.extensions import db  # noqa: E402
from app.models.user import User  # noqa: E402
from app.models.pokemon import Species, Form, EvolutionChain  # noqa: E402
from app.models.collection import UserCollection  # noqa: E402
from app.models.individual import UserPokemon  # noqa: E402

# Kanto: o que o "felipe" possui. Bulbasaur/Charmander/Squirtle possuídos e
# Ivysaur/Charmeleon faltando → aparecem como "Evoluir" na Wishlist.
OWNED = {1: 3, 4: 1, 7: 2, 16: 5, 19: 4, 25: 2, 52: 1, 63: 1, 92: 1, 129: 6, 133: 2, 143: 1, 147: 1}
FOR_TRADE = {16, 19, 129}
SHINY = {25, 129}
PERFECT = {1}
# Misty oferece para troca espécies que o felipe NÃO tem (sem pré-evolução → prioridade Alta)
FRIEND_TRADES = {131: 1, 132: 2, 54: 1, 120: 3}


def seed(app):
    data = json.loads((ROOT / "cypress" / "fixtures" / "pokedex_seed.json").read_text(encoding="utf-8"))
    with app.app_context():
        db.drop_all()
        db.create_all()
        db.session.bulk_insert_mappings(Species, data["species"])
        db.session.bulk_insert_mappings(Form, data["forms"])
        db.session.bulk_insert_mappings(EvolutionChain, data["evolutions"])

        felipe = User(username=E2E_USER, email="felipe@e2e.test", trainer_code="1111 2222 3333", visibility="public")
        misty = User(username=E2E_FRIEND, email="misty@e2e.test", trainer_code="4444 5555 6666", visibility="public")
        felipe.set_password(E2E_PASSWORD)
        misty.set_password(E2E_PASSWORD)
        db.session.add_all([felipe, misty])
        db.session.flush()

        form_of = {f["species_id"]: f["id"] for f in data["forms"] if f["form_name"] == "normal"}
        for sid, qty in OWNED.items():
            db.session.add(UserCollection(
                user_id=felipe.id, form_id=form_of[sid], owned=True, quantity=qty,
                for_trade=sid in FOR_TRADE, has_shiny=sid in SHINY, shiny_qty=1 if sid in SHINY else 0,
                has_perfect=sid in PERFECT,
            ))
        # Exemplares detalhados do Bulbasaur (um 100%) para o duplo clique
        db.session.add_all([
            UserPokemon(user_id=felipe.id, form_id=form_of[1], source="pokegenie", cp=1102, hp=118,
                        atk_iv=15, def_iv=15, sta_iv=15, iv_pct=100.0, level=30, quick_move="Vine Whip",
                        charge_move="Sludge Bomb", is_lucky=True, rank_great=85.3),
            UserPokemon(user_id=felipe.id, form_id=form_of[1], source="manual", cp=640,
                        atk_iv=10, def_iv=12, sta_iv=5, iv_pct=60.0),
        ])
        for sid, qty in FRIEND_TRADES.items():
            db.session.add(UserCollection(user_id=misty.id, form_id=form_of[sid], owned=True,
                                          quantity=qty, for_trade=True))
        db.session.commit()
        print(f"[e2e] banco {DB_FILE} semeado: {len(data['species'])} espécies, "
              f"{len(OWNED)} possuídos por {E2E_USER}")


if __name__ == "__main__":
    DB_DIR.mkdir(parents=True, exist_ok=True)
    app = create_app("e2e")
    seed(app)
    print(f"[e2e] http://localhost:{PORT}  (usuário {E2E_USER} / {E2E_PASSWORD})")
    app.run(host="127.0.0.1", port=PORT, debug=False, threaded=True)
