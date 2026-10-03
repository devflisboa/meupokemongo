"""
Vocabulário PT-BR do app — segue a tradução oficial do Pokémon GO em português.

Termos fixos (18 tipos, rótulos) ficam aqui no código, versionados e testados.
Tabela no banco só faria sentido para texto editável por admin sem deploy (não é o caso hoje).
Nomes das espécies já vêm em Species.name_pt (PokeAPI) — no Brasil são os mesmos do inglês.

Glossário usado na interface:
  Shiny → Brilhante · Shundo → Brilhante 100% · Lucky → Sortudo · Shadow → Sombroso
  Purified → Purificado · CP → PC · HP → PS · Attack/Defense → Ataque/Defesa
  Wishlist → Lista de Desejos · Trade Binder → Vitrine de Trocas · Dashboard → Início
"""

TYPE_PT = {
    "normal": "Normal", "fire": "Fogo", "water": "Água", "electric": "Elétrico",
    "grass": "Planta", "ice": "Gelo", "fighting": "Lutador", "poison": "Venenoso",
    "ground": "Terrestre", "flying": "Voador", "psychic": "Psíquico", "bug": "Inseto",
    "rock": "Pedra", "ghost": "Fantasma", "dragon": "Dragão", "dark": "Sombrio",
    "steel": "Aço", "fairy": "Fada",
}


def tipo(type_name: str | None) -> str:
    """'grass' → 'Planta'. Desconhecido → capitalizado; None → ''."""
    if not type_name:
        return ""
    return TYPE_PT.get(type_name.lower(), type_name.capitalize())
