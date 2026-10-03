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


# Cor de cada tipo (classes Tailwind) — usada para personalizar o card do treinador
# pela cor do tipo do Pokémon favorito.
TYPE_GRAD = {
    "fire": "from-orange-400 to-red-500", "water": "from-blue-400 to-cyan-500",
    "grass": "from-green-400 to-emerald-500", "electric": "from-yellow-300 to-amber-400",
    "psychic": "from-pink-400 to-fuchsia-500", "ice": "from-cyan-300 to-blue-400",
    "dragon": "from-indigo-500 to-purple-600", "dark": "from-gray-600 to-gray-800",
    "fairy": "from-pink-300 to-rose-400", "fighting": "from-red-500 to-orange-600",
    "flying": "from-sky-300 to-blue-400", "poison": "from-purple-400 to-violet-500",
    "ground": "from-yellow-500 to-amber-600", "rock": "from-stone-400 to-stone-600",
    "bug": "from-lime-400 to-green-500", "ghost": "from-violet-500 to-purple-700",
    "steel": "from-slate-400 to-gray-500", "normal": "from-gray-300 to-gray-400",
}
# tipos de cor clara: texto escuro fica legível
LIGHT_TYPES = {"electric", "ice", "fairy", "flying", "normal", "ground", "bug"}


def tipo(type_name: str | None) -> str:
    """'grass' → 'Planta'. Desconhecido → capitalizado; None → ''."""
    if not type_name:
        return ""
    return TYPE_PT.get(type_name.lower(), type_name.capitalize())
