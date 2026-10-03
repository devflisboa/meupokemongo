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
from ..models.individual import UserPokemon
from ..models.pokemon import Form, PokemonCache

# ── Campos aceitos por apply_import ──────────────────────────────────────────
_IMPORT_FIELDS = {"form_id", "owned", "quantity", "for_trade", "has_perfect", "notes"}


# ── Schema para formato interno ───────────────────────────────────────────────
class CollectionRowSchema(Schema):
    class Meta:
        unknown = EXCLUDE

    form_id = fields.Int(required=True)
    owned = fields.Bool(load_default=False)
    quantity = fields.Int(load_default=0, validate=validate.Range(min=0))
    for_trade = fields.Bool(load_default=False)
    has_perfect = fields.Bool(load_default=False)
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
_TRUE_VALUES = ("yes", "true", "1", "sim", "y")


def _col(row: dict, *names: str) -> str:
    """Primeiro valor não vazio entre os nomes de coluna (case-insensitive)."""
    lower = {(k or "").strip().lower(): v for k, v in row.items()}
    for n in names:
        v = lower.get(n.lower())
        if v is not None and str(v).strip() != "":
            return str(v).strip()
    return ""


def _int(v: str) -> int | None:
    try:
        return int(float(v.replace(",", ".")))
    except (ValueError, AttributeError):
        return None


def _float(v: str) -> float | None:
    try:
        return float(v.replace("%", "").replace(",", "."))
    except (ValueError, AttributeError):
        return None


def _bool(v: str) -> bool:
    return v.strip().lower() in _TRUE_VALUES


def _parse_individual(row: dict) -> dict:
    """Extrai todos os campos conhecidos de uma linha do PokeGenie."""
    lvl_min = _float(_col(row, "Level Min", "Level"))
    lvl_max = _float(_col(row, "Level Max"))
    sha_pur = _col(row, "Shadow/Purified", "Sha/Pur").lower()  # 0=normal 1=shadow 2=purified
    atk, dfn, sta = (_int(_col(row, c)) for c in ("Atk IV", "Def IV", "Sta IV"))
    iv_pct = _float(_col(row, "IV Avg", "IV %", "IV"))
    if iv_pct is None and None not in (atk, dfn, sta):
        iv_pct = round((atk + dfn + sta) / 45 * 100, 1)
    return {
        "nickname": _col(row, "Name")[:100] or None,
        "form_label": _col(row, "Form")[:50] or None,
        "gender": _col(row, "Gender")[:10] or None,
        "cp": _int(_col(row, "CP")),
        "hp": _int(_col(row, "HP")),
        "atk_iv": atk,
        "def_iv": dfn,
        "sta_iv": sta,
        "iv_pct": iv_pct,
        "level": lvl_max if lvl_max is not None else lvl_min,
        "quick_move": _col(row, "Quick Move", "Fast Move")[:60] or None,
        "charge_move": _col(row, "Charge Move", "Charge Move 1")[:60] or None,
        "charge_move2": _col(row, "Charge Move 2")[:60] or None,
        "weight": _float(_col(row, "Weight")),
        "height": _float(_col(row, "Height")),
        "is_lucky": _bool(_col(row, "Lucky")),
        "is_shadow": sha_pur in ("1", "shadow"),
        "is_purified": sha_pur in ("2", "purified"),
        "is_shiny": _bool(_col(row, "Shiny")),
        "is_favorite": _bool(_col(row, "Favorite")),
        "for_trade": _bool(_col(row, "Marked for Trade", "marked_for_trade")),
        "rank_great": _float(_col(row, "Rank % (G)")),
        "rank_ultra": _float(_col(row, "Rank % (U)")),
        "rank_little": _float(_col(row, "Rank % (L)")),
        "catch_date": _col(row, "Catch Date")[:30] or None,
        "scan_date": _col(row, "Scan Date", "Original Scan Date")[:30] or None,
        "raw": {k: v for k, v in row.items() if k},
    }


def _is_perfect_iv(ind: dict) -> bool:
    """True se o indivíduo for 100% IV (Atk/Def/Sta = 15)."""
    return (ind["atk_iv"], ind["def_iv"], ind["sta_iv"]) == (15, 15, 15)


def parse_pokegenie(raw_bytes: bytes) -> tuple[list[dict], list[str]]:
    """
    Parseia export do PokeGenie (uma linha por indivíduo).
    Agrupa por espécie: quantity = nº de indivíduos, for_trade = se algum estiver marcado,
    has_perfect = se algum indivíduo for 15/15/15. Cada indivíduo vai em _individuals.
    """
    valid, errors = [], []
    text = raw_bytes.decode("utf-8-sig")
    reader = csv.DictReader(io.StringIO(text))

    group: dict[int, dict] = defaultdict(
        lambda: {"count": 0, "for_trade": False, "has_perfect": False, "has_shiny": False,
                 "name": "", "individuals": []}
    )

    row_count = 0
    for i, row in enumerate(reader, start=2):
        row_count += 1

        # Tenta vários nomes de coluna para o ID da espécie
        sid_raw = _col(row, "Pokemon Number", "Pokémon Number", "Pokémon Id", "Pokemon Id", "pokemon_id")

        if not sid_raw or not sid_raw.isdigit():
            errors.append(f"Linha {i}: ID da espécie inválido ('{sid_raw}')")
            continue

        sid = int(sid_raw)
        ind = _parse_individual(row)
        g = group[sid]
        g["count"] += 1
        g["individuals"].append(ind)
        if not g["name"]:
            g["name"] = ind["nickname"] or f"#{sid:03d}"
        g["for_trade"] = g["for_trade"] or ind["for_trade"]
        g["has_perfect"] = g["has_perfect"] or _is_perfect_iv(ind)
        g["has_shiny"] = g["has_shiny"] or ind["is_shiny"]

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
            "has_perfect": data["has_perfect"],
            "notes": "Importado via PokeGenie",
            # campos extras — não vão direto para UserCollection
            "_name": data["name"],
            "_species_id": sid,
            "_has_shiny": data["has_shiny"],
            "_individuals": data["individuals"],
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
    created, updated, individuals = 0, 0, 0

    # Export PokeGenie é o retrato completo da coleção: substitui os exemplares
    # importados antes (os cadastrados manualmente são preservados).
    if any("_individuals" in r for r in rows):
        db.session.query(UserPokemon).filter_by(user_id=user_id, source="pokegenie").delete()

    for raw_row in rows:
        for ind in raw_row.get("_individuals", []):
            db.session.add(UserPokemon(user_id=user_id, form_id=raw_row["form_id"], source="pokegenie", **ind))
            individuals += 1

        row = {k: v for k, v in raw_row.items() if k in _IMPORT_FIELDS}
        if raw_row.get("_has_shiny"):
            row["has_shiny"] = True
        existing = db.session.query(UserCollection).filter_by(
            user_id=user_id, form_id=row["form_id"]
        ).first()
        if existing:
            existing.owned = row["owned"]
            existing.quantity = row["quantity"]
            existing.for_trade = row["for_trade"] if row["owned"] and row["quantity"] > 0 else False
            existing.has_perfect = row.get("has_perfect", False) if row["owned"] and row["quantity"] > 0 else False
            if row.get("has_shiny"):
                existing.has_shiny = True
            existing.notes = row.get("notes", "")
            updated += 1
        else:
            db.session.add(UserCollection(user_id=user_id, **row))
            created += 1
    db.session.commit()
    return {"created": created, "updated": updated, "total": created + updated, "individuals": individuals}
