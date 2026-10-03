"""
Miniaturas HD dos cards: arte oficial (~129 KB, 475 px) → WebP 160 px (~6 KB).

Mais nítido que o sprite pixelado de 96 px e ~20× mais leve que a arte original.
Gera sob demanda, guarda em disco (sobrevive entre requisições/workers; após um deploy
o cache recomeça vazio e se refaz sozinho) e o navegador guarda por 1 ano.
"""
import io
import os
import tempfile

import requests
from PIL import Image

ART_URL = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/other/official-artwork/{pid}.png"
SIZE = 160  # cobre cards de até ~64 px CSS em telas 2,5×
QUALITY = 82
CACHE_DIR = os.environ.get("THUMB_CACHE_DIR", os.path.join(tempfile.gettempdir(), "meupokemongo-thumbs"))
MAX_PID = 20000  # espécies (1..1025) e formas (10001..)


def thumb_path(pid: int) -> str:
    return os.path.join(CACHE_DIR, f"{pid}-{SIZE}.webp")


def make_thumb(art_bytes: bytes) -> bytes:
    img = Image.open(io.BytesIO(art_bytes)).convert("RGBA")
    img.thumbnail((SIZE, SIZE), Image.LANCZOS)
    buf = io.BytesIO()
    img.save(buf, "WEBP", quality=QUALITY, method=4)
    return buf.getvalue()


def get_thumb(pid: int, fetch=None) -> bytes | None:
    """Bytes do WebP (do cache ou gerado agora). None se a arte não existir."""
    if not (1 <= pid <= MAX_PID):
        return None
    path = thumb_path(pid)
    if os.path.exists(path):
        with open(path, "rb") as f:
            return f.read()
    fetch = fetch or _fetch_art
    art = fetch(pid)
    if not art:
        return None
    data = make_thumb(art)
    os.makedirs(CACHE_DIR, exist_ok=True)
    tmp = f"{path}.{os.getpid()}.tmp"  # escrita atômica: 4 workers do gunicorn podem gerar ao mesmo tempo
    with open(tmp, "wb") as f:
        f.write(data)
    os.replace(tmp, path)
    return data


def _fetch_art(pid: int) -> bytes | None:
    try:
        r = requests.get(ART_URL.format(pid=pid), timeout=15)
        return r.content if r.ok else None
    except requests.RequestException:
        return None
