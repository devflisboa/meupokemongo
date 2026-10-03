"""
Variações de imagem a partir da arte oficial gravada em Form.sprite_url.

Regra de uso (decisão de 02/10/2026, revista em 03/10/2026 por qualidade):
- Grades (coleção, estoque, wishlist, binder…): miniatura HD WebP 160 px (~6 KB) — ~20× mais leve que a arte (~129 KB)
- Destaques (modal, adesivo do favorito, "você tem" do Trade Binder): GIF animado (~65 KB), shiny se o treinador tem
- Arte oficial grande: só página de detalhe da Pokédex e og:image
Todas as variações existem no repositório PokeAPI/sprites, inclusive para formas (ids 10xxx).
"""
import re

_BASE = "https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon"
_ID = re.compile(r"/(\d+)\.png$")


def _pokemon_id(art_url: str | None) -> str | None:
    m = _ID.search(art_url or "")
    return m.group(1) if m else None


def sprite_small(art_url: str | None) -> str:
    """
    Imagem dos cards: miniatura HD WebP 160 px (~6 KB) gerada a partir da arte oficial
    pela rota /img/t/<id>.webp (services/thumbs.py). Mais nítida que o sprite pixelado de 96 px
    e ~20× mais leve que a arte original. Cai na própria URL se não reconhecer o id.
    """
    pid = _pokemon_id(art_url)
    return f"/img/t/{pid}.webp" if pid else (art_url or "")


def sprite_anim(art_url: str | None, shiny: bool = False) -> str:
    """GIF animado (estilo Showdown); shiny=True usa a versão brilhante."""
    pid = _pokemon_id(art_url)
    if not pid:
        return art_url or ""
    return f"{_BASE}/other/showdown/{'shiny/' if shiny else ''}{pid}.gif"
