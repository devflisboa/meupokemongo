"""OCR service para #17-B — processa screenshots do Pokémon GO.

Estratégia: ROIs relativos (0.0–1.0) + pré-processamento Pillow + pytesseract PSM 6.
Desacoplado do Flask: recebe name_index do chamador e retorna ScanResult.
"""
from __future__ import annotations

import io
import os
import re
import difflib
import colorsys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import pytesseract
    from PIL import Image, ImageOps
    _HAS_TESSERACT = True
except ImportError:  # pragma: no cover
    _HAS_TESSERACT = False

_TESSERACT_PATH = os.environ.get("TESSERACT_PATH")
if _TESSERACT_PATH and _HAS_TESSERACT:
    pytesseract.pytesseract.tesseract_cmd = _TESSERACT_PATH

_OCR_CFG = "--psm 6 --oem 3"


def calc_iv_pct(atk: int | None, def_: int | None, sta: int | None) -> float | None:
    """(atk+def+sta)/45*100 com validação de bounds. Retorna None se qualquer IV for None."""
    if any(v is None for v in (atk, def_, sta)):
        return None
    atk = max(0, min(15, atk))
    def_ = max(0, min(15, def_))
    sta = max(0, min(15, sta))
    return round((atk + def_ + sta) / 45 * 100, 1)


# ---------------------------------------------------------------------------
# Dataclass de resultado
# ---------------------------------------------------------------------------

@dataclass
class ScanResult:
    raw_name: str | None = None
    species_id: int | None = None
    species_name: str | None = None
    form_id: int | None = None
    cp: int | None = None
    hp_current: int | None = None
    hp_max: int | None = None
    atk_iv: int | None = None
    def_iv: int | None = None
    sta_iv: int | None = None
    iv_pct: float | None = None
    is_shiny: bool = False
    screen_type: str = "unknown"   # "main" | "appraisal" | "unknown"
    confidence: float = 0.0
    warnings: list[str] = field(default_factory=list)
    thumbnail_url: str | None = None

    def to_dict(self) -> dict:
        return {
            "raw_name": self.raw_name,
            "species_id": self.species_id,
            "species_name": self.species_name,
            "form_id": self.form_id,
            "cp": self.cp,
            "hp_current": self.hp_current,
            "hp_max": self.hp_max,
            "atk_iv": self.atk_iv,
            "def_iv": self.def_iv,
            "sta_iv": self.sta_iv,
            "iv_pct": self.iv_pct,
            "is_shiny": self.is_shiny,
            "screen_type": self.screen_type,
            "confidence": self.confidence,
            "warnings": self.warnings,
            "thumbnail_url": self.thumbnail_url,
        }


# ---------------------------------------------------------------------------
# Índice de nomes — carregado pelo chamador (Flask route)
# ---------------------------------------------------------------------------

def build_name_index(species_list) -> dict[str, tuple[int, int | None]]:
    """Retorna {nome_normalizado: (species_id, form_id_padrão)}.

    Indexa pelos nomes PT-BR e inglês de cada espécie.
    """
    index: dict[str, tuple[int, int | None]] = {}
    for sp in species_list:
        form = sp.forms.filter_by(form_name="normal").first() or sp.forms.first()
        form_id = form.id if form else None
        for name in [sp.name_pt, sp.name]:
            if name:
                key = _norm(name)
                if key and key not in index:
                    index[key] = (sp.id, form_id)
    return index


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]", "", s.lower())


# ---------------------------------------------------------------------------
# Processamento em lote
# ---------------------------------------------------------------------------

def process_images(
    image_files: list[bytes],
    name_index: dict[str, tuple[int, int | None]],
    thumb_dir: Path | None = None,
) -> list[ScanResult]:
    results = []
    for i, img_bytes in enumerate(image_files):
        result = _process_single(img_bytes, name_index)
        if thumb_dir:
            try:
                img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
                img.thumbnail((200, 200))
                thumb_path = thumb_dir / f"thumb_{i}.jpg"
                img.save(thumb_path, "JPEG", quality=70)
                result.thumbnail_url = f"/static/scan_temp/{thumb_dir.name}/thumb_{i}.jpg"
            except Exception:
                pass
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# Processamento individual
# ---------------------------------------------------------------------------

def _process_single(img_bytes: bytes, name_index: dict) -> ScanResult:
    result = ScanResult()

    if not _HAS_TESSERACT:
        result.warnings.append("pytesseract não está instalado no servidor.")
        return result

    try:
        img = Image.open(io.BytesIO(img_bytes)).convert("RGB")
    except Exception as e:
        result.warnings.append(f"Imagem inválida: {e}")
        return result

    w, h = img.size
    if w == 0 or h == 0:
        result.warnings.append("Imagem vazia.")
        return result

    ratio = w / h
    if ratio > 0.65:
        result.warnings.append("Proporção incomum — certifique-se que é um print de celular em modo retrato.")

    # Detecta tipo de tela pelo texto completo
    full_text = _ocr_roi(img, 0.0, 1.0, 0.0, 1.0)
    result.screen_type = _detect_screen_type(full_text)

    # CP — topo da tela (y=3-12%)
    cp_text = _ocr_roi(img, 0.03, 0.12, 0.15, 0.85)
    result.cp = _extract_cp(cp_text)

    # Nome — card branco (y=46-60%); PT-BR usa o nome no card, não no topo
    name_text = _ocr_roi(img, 0.46, 0.60, 0.15, 0.85)
    result.raw_name = _clean(name_text)
    match = _match_species(result.raw_name or "", name_index)
    if match:
        result.species_id, result.form_id, result.species_name = match
    elif result.raw_name:
        result.warnings.append(f"Pokémon '{result.raw_name}' não identificado — selecione manualmente.")

    # HP — abaixo do nome (y=55-67%)
    hp_text = _ocr_roi(img, 0.55, 0.67, 0.15, 0.85)
    hp = _extract_hp(hp_text)
    if hp:
        result.hp_current, result.hp_max = hp

    # IVs (tela de appraisal)
    if result.screen_type == "appraisal":
        result.atk_iv = _extract_iv(_ocr_roi(img, 0.30, 0.42, 0.60, 0.95))
        result.def_iv = _extract_iv(_ocr_roi(img, 0.42, 0.54, 0.60, 0.95))
        result.sta_iv = _extract_iv(_ocr_roi(img, 0.54, 0.66, 0.60, 0.95))
        result.iv_pct = calc_iv_pct(result.atk_iv, result.def_iv, result.sta_iv)
        if result.iv_pct is None:
            result.warnings.append("IVs não lidos com precisão — preencha manualmente.")

    # Shiny (heurística por pixel dourado)
    result.is_shiny = _detect_shiny(img)
    if result.is_shiny:
        result.warnings.append("Shiny detectado — confirme abaixo.")

    result.confidence = _calc_confidence(result)
    return result


# ---------------------------------------------------------------------------
# Helpers de OCR
# ---------------------------------------------------------------------------

def _ocr_roi(img: "Image.Image", y0: float, y1: float, x0: float, x1: float) -> str:
    w, h = img.size
    box = (int(x0 * w), int(y0 * h), int(x1 * w), int(y1 * h))
    roi = img.crop(box).convert("L")
    roi = ImageOps.invert(roi)
    # Escala 2× para melhorar acurácia em números pequenos
    roi = roi.resize((roi.width * 2, roi.height * 2), Image.LANCZOS)
    roi = roi.point(lambda p: 255 if p > 128 else 0)
    try:
        return pytesseract.image_to_string(roi, lang="por+eng", config=_OCR_CFG)
    except Exception:
        return ""


def _clean(text: str) -> str:
    return " ".join(text.split()).strip()


def _detect_screen_type(text: str) -> str:
    t = text.lower()
    # Tela de avaliação — palavras exclusivas do modo appraisal
    if any(k in t for k in ["ataque", "defesa", "stamina", "attack", "defense"]):
        return "appraisal"
    # Tela principal — PT-BR usa "pc" (PC 1010) e "peso"/"fortalecer"
    if any(k in t for k in ["cp ", "pv ", "hp ", "pc ", "peso", "fortalecer", "evoluir", "power up"]):
        return "main"
    return "unknown"


def _extract_cp(text: str) -> int | None:
    # PT-BR usa "PC" (Pontos de Combate); EN usa "CP"
    m = re.search(r"\b(?:CP|PC)\s*(\d{2,4})\b", text, re.IGNORECASE)
    if m:
        return int(m.group(1))
    # fallback: número isolado de 3-4 dígitos
    m = re.search(r"\b(\d{3,4})\b", text)
    return int(m.group(1)) if m else None


def _extract_hp(text: str) -> tuple[int, int] | None:
    m = re.search(r"(\d{1,4})\s*/\s*(\d{1,4})", text)
    return (int(m.group(1)), int(m.group(2))) if m else None


def _extract_iv(text: str) -> int | None:
    # IVs vão de 0 a 15; pega o último número no range
    nums = re.findall(r"\b(\d{1,2})\b", text)
    for n in reversed(nums):
        v = int(n)
        if 0 <= v <= 15:
            return v
    return None


def _detect_shiny(img: "Image.Image") -> bool:
    """Detecta pixel dourado no canto superior direito da área do nome."""
    try:
        w, h = img.size
        roi = img.crop((int(0.70 * w), int(0.04 * h), int(0.92 * w), int(0.16 * h)))
        count = 0
        for r, g, b in roi.getdata():
            hue, sat, val = colorsys.rgb_to_hsv(r / 255, g / 255, b / 255)
            if 0.11 <= hue <= 0.16 and sat > 0.5 and val > 0.6:
                count += 1
        return count > 20
    except Exception:
        return False


def _match_species(raw: str, index: dict) -> tuple[int, int | None, str] | None:
    if not raw:
        return None
    key = _norm(raw)
    if key in index:
        sid, fid = index[key]
        return sid, fid, raw
    matches = difflib.get_close_matches(key, index.keys(), n=1, cutoff=0.75)
    if matches:
        sid, fid = index[matches[0]]
        return sid, fid, raw
    return None


def _calc_confidence(r: ScanResult) -> float:
    scores = [1.0 if r.species_id else 0.0, 1.0 if r.cp else 0.3]
    if r.screen_type == "appraisal":
        scores.append(1.0 if r.iv_pct is not None else 0.2)
    elif r.hp_max:
        scores.append(0.8)
    return round(sum(scores) / len(scores), 2)
