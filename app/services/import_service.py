"""
RF14: Upload → Validação → Preview → Confirmação → Importação → Relatório

Formatos suportados:
  - PokeGenie CSV  (detectado automaticamente pelos headers)
  - Interno  CSV   (form_id, owned, quantity, for_trade, notes)
  - Interno  JSON  ([{"form_id": 1, "owned": true, ...}])
"""
import csv
import io
import json
import uuid
from collections import defaultdict

from marshmallow import Schema, fields, ValidationError, validate, EXCLUDE

from ..extensions import db
from ..models.collection import UserCollection
from ..models.pokemon import Form, PokemonCache

# ── Campos aceitos por apply_import ──────────────────────────────────────────
_IMPORT_FIELDS = {"form_id", "owned", "quantity", "for_trade", "notes"}


# ── Schema para formato interno ───────────────────────────────────────────────
class CollectionRowSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    form_id = fields.Int(required=True)
    owned = fields.Bool(load_default=False)
    quantity = fields.Int(load_default=0, validate=validate.Range(min=0))
    for_trade = fields.Bool(load_default=False)
    notes = fields.Str(load_default="", validate=validate.Length(max=500))


_schema = CollectionRowSchema()


# ── Detecção de formato ───────────────────────────────────────────────────────
def detect_format(raw_bytes: bytes, ext: str) -> str:
    """Retorna 'pokegenie', 'csv' ou 'json'."""
    if ext == "json":
        return "json"
    if ext == "csv":
        text = raw_bytes.decode("utf-8-sig")
        first_line = text.split("\n")[0].lower()
        if "atk iv" in first_line or "pokémon id" in first_line or "pokemon id" in first_line:
            return "pokegenie"
        return "csv"
    return "unknown"


# ── Parser: PokeGenie ─────────────────────────────────────────────────────────
def parse_pokegenie(raw_bytes: bytes) -> tuple[list[dict], list[str]]:
    """
    Parseia export do PokeGenie (uma linha por indivíduo).
    Agrupa por espécie: quantity = nº de indivíduos, for_trade = se algum estiver marcado.
    """
    valid, errors = [], []
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    # group[species_id] = {count, for_trade, name}
    group: dict[int, dict] = defaultdict(lambda: {"count": 0, "for_trade": False, "name": ""})

    row_count = 0
    for i, row in enumerate(reader, start=2):
        row_count += 1

        # Tenta vários nomes de coluna para o ID da espécie
        sid_raw = (
            row.get("Pokémon Id")
            or row.get("Pokemon Id")
            or row.get("Pokemon ID")
            or row.get("pokémon id")
            or row.get("pokemon_id")
            or ""
        ).strip()

        if not sid_raw or not sid_raw.isdigit():
            errors.append(f"Linha {i}: ID da espécie inválido ('{sid_raw}')")
            continue

        sid = int(sid_raw)
        group[sid]["count"] += 1
        if not group[sid]["name"]:
            group[sid]["name"] = (row.get("Name") or f"#{sid:03d}").strip()

        trade_val = (row.get("Marked for Trade") or row.get("marked_for_trade") or "").strip().lower()
        if trade_val in ("yes", "true", "1", "sim"):
            group[sid]["for_trade"] = True

    if row_count == 0:
        errors.append("Arquivo vazio ou formato inválido.")
        return [], errors

    # Resolve species_id → form_id via banco
    for sid, data in sorted(group.items()):
        form = db.session.query(Form).filter_by(species_id=sid, form_name="normal").first()
        if not form:
            errors.append(f"#{sid:03d} {data['name']}: não encontrado na Pokédex. Sincronize antes de importar.")
            continue

        valid.append({
            "form_id": form.id,
            "owned": True,
            "quantity": data["count"],
            "for_trade": data["for_trade"],
            "notes": "Importado via PokeGenie",
            # campos extras — só para preview, removidos em apply_import
            "_name": data["name"],
            "_species_id": sid,
        })

    return valid, errors


# ── Parser: CSV interno ───────────────────────────────────────────────────────
def parse_csv(raw_bytes: bytes) -> tuple[list[dict], list[str]]:
    valid, errors = [], []
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=2):
        try:
            valid.append(_schema.load(row))
        except ValidationError as e:
            errors.append(f"Linha {i}: {e.messages}")
    return valid, errors


# ── Parser: JSON interno ──────────────────────────────────────────────────────
def parse_json(raw_bytes: bytes) -> tuple[list[dict], list[str]]:
    valid, errors = [], []
    data = json.loads(raw_bytes.decode("utf-8"))
    if not isinstance(data, list):
        return [], ["JSON deve ser uma lista de objetos."]
    for i, row in enumerate(data, start=1):
        try:
            valid.append(_schema.load(row))
        except ValidationError as e:
            errors.append(f"Item {i}: {e.messages}")
    return valid, errors


# ── Armazenamento temporário no banco (evita limite de cookie) ────────────────
def store_import_session(user_id: int, rows: list[dict], fmt: str) -> str:
    key = f"import_{user_id}_{uuid.uuid4().hex}"
    db.session.add(PokemonCache(cache_key=key, payload={"rows": rows, "fmt": fmt}))
    db.session.commit()
    return key


def load_import_session(key: str) -> tuple[list[dict], str]:
    entry = db.session.get(PokemonCache, key)
    if not entry:
        return [], ""
    payload = entry.payload
    db.session.delete(entry)
    db.session.commit()
    return payload.get("rows", []), payload.get("fmt", "")


# ── Aplicar importação ────────────────────────────────────────────────────────
def apply_import(user_id: int, rows: list[dict]) -> dict:
    created, updated = 0, 0
    for raw_row in rows:
        row = {k: v for k, v in raw_row.items() if k in _IMPORT_FIELDS}
        existing = db.session.query(UserCollection).filter_by(
            user_id=user_id, form_id=row["form_id"]
        ).first()
        if existing:
            existing.owned = row["owned"]
            existing.quantity = row["quantity"]
            existing.for_trade = row["for_trade"] if row["owned"] and row["quantity"] > 0 else False
            existing.notes = row.get("notes", "")
            updated += 1
        else:
            db.session.add(UserCollection(user_id=user_id, **row))
            created += 1
    db.session.commit()
    return {"created": created, "updated": updated, "total": created + updated}
