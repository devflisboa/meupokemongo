"""
RF14: Upload → Validação → Preview → Confirmação → Importação → Relatório
"""
import csv
import io
import json
from marshmallow import Schema, fields, ValidationError, validate, EXCLUDE
from ..extensions import db
from ..models.collection import UserCollection
from ..models.pokemon import Form


class CollectionRowSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    form_id = fields.Int(required=True)
    owned = fields.Bool(load_default=False)
    quantity = fields.Int(load_default=0, validate=validate.Range(min=0))
    for_trade = fields.Bool(load_default=False)
    notes = fields.Str(load_default="", validate=validate.Length(max=500))


_schema = CollectionRowSchema()


def parse_csv(raw_bytes: bytes) -> tuple[list[dict], list[str]]:
    """Lê CSV e retorna (linhas_válidas, erros)."""
    valid, errors = [], []
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))
    for i, row in enumerate(reader, start=2):
        try:
            valid.append(_schema.load(row))
        except ValidationError as e:
            errors.append(f"Linha {i}: {e.messages}")
    return valid, errors


def parse_json(raw_bytes: bytes) -> tuple[list[dict], list[str]]:
    """Lê JSON e retorna (linhas_válidas, erros)."""
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


def apply_import(user_id: int, rows: list[dict]) -> dict:
    """Executa a importação em transação única. Retorna relatório."""
    created, updated = 0, 0
    for row in rows:
        existing = db.session.query(UserCollection).filter_by(
            user_id=user_id, form_id=row["form_id"]
        ).first()
        if existing:
            existing.owned = row["owned"]
            existing.quantity = row["quantity"]
            existing.for_trade = row["for_trade"] if row["owned"] and row["quantity"] > 0 else False
            existing.notes = row["notes"]
            updated += 1
        else:
            entry = UserCollection(user_id=user_id, **row)
            db.session.add(entry)
            created += 1
    db.session.commit()
    return {"created": created, "updated": updated, "total": created + updated}
