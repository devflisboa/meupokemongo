"""
Dados regionais (#14).

1) Formas regionais (Alola, Galar, Hisui, Paldea) — vêm da PokeAPI no sync (`flask sync-forms`).
2) Exclusivos de região do Pokémon GO — só aparecem na natureza em certas partes do mundo,
   então para quem não mora lá o caminho é a TROCA (o caso de uso mais forte do app).

A lista de exclusivos é curada e aproximada: a Niantic muda a distribuição de tempos em tempos.
Ficaram de fora os pares que alternam de região (Zangoose/Seviper, Lunatone/Solrock,
Volbeat/Illumise, Throh/Sawk, Heatmor/Durant) por não terem região fixa confiável.
"""
import re

REGION_LABEL = {"alola": "Alola", "galar": "Galar", "hisui": "Hisui", "paldea": "Paldea"}
FORM_EXTRA_LABEL = {
    "combat-breed": "Combate", "blaze-breed": "Chamas", "aqua-breed": "Aquática",
    "standard": "",  # darmanitan-galar-standard
    "zen": "Zen", "disguised": "Disfarçado", "busted": "Revelado",
    "amped": "Amped", "low-key": "Low Key", "single-strike": "Golpe Único", "rapid-strike": "Golpe Fluido",
    "x": "X", "y": "Y", "z": "Z",
}
CAP_LABEL = {
    "original": "Original", "hoenn": "de Hoenn", "sinnoh": "de Sinnoh", "unova": "de Unova",
    "kalos": "de Kalos", "alola": "de Alola", "partner": "de Parceiro", "world": "Mundial",
}

# Categorias de formas alternativas (além da "normal")
CATEGORIES = {
    "regional": "Regionais",     # Alola, Galar, Hisui, Paldea
    "mega": "Mega",              # Mega Evolução — temporária no GO, NÃO se troca
    "gmax": "Gigantamax",
    "especial": "Especiais",     # bonés do Pikachu, Totem (não existe no GO), Darmanitan Zen
}
TRADEABLE_CATEGORIES = {"regional", "gmax", "especial"}  # Mega fica fora do matching


def form_category(form_name: str) -> str | None:
    """Categoria de uma forma pelo nome ('alola' → regional, 'mega-x' → mega...). None = normal/desconhecida."""
    if not form_name or form_name == "normal":
        return None
    tokens = form_name.split("-")
    if "mega" in tokens:
        return "mega"
    if tokens[-1] == "gmax":
        return "gmax"
    if {"cap", "totem", "zen"} & set(tokens):
        return "especial"
    if tokens[0] in REGION_LABEL:
        return "regional"
    return None


def variety_category(variety_name: str) -> str | None:
    """Mesma regra, aplicada ao nome completo da variedade da PokeAPI ('charizard-mega-x')."""
    tokens = variety_name.split("-")
    if "mega" in tokens[1:]:
        return "mega"
    if tokens[-1] == "gmax":
        return "gmax"
    if {"cap", "totem", "zen"} & set(tokens[1:]):
        return "especial"
    if set(tokens[1:]) & set(REGION_LABEL):
        return "regional"
    return None

# species_id: (onde aparece, disponível no Brasil?)
REGION_EXCLUSIVES: dict[int, tuple[str, bool]] = {
    83:  ("Ásia", False),                                 # Farfetch'd
    115: ("Austrália e Nova Zelândia", False),            # Kangaskhan
    122: ("Europa", False),                               # Mr. Mime
    128: ("América do Norte", False),                     # Tauros
    214: ("América Latina", True),                        # Heracross
    222: ("faixa tropical", True),                        # Corsola
    324: ("Sul e Sudeste da Ásia", False),                # Torkoal
    357: ("África e Mediterrâneo", False),                # Tropius
    369: ("Nova Zelândia e ilhas do Pacífico", False),    # Relicanth
    417: ("Alasca, Canadá e Rússia", False),              # Pachirisu
    439: ("Europa", False),                               # Mime Jr.
    441: ("Hemisfério Sul", True),                        # Chatot
    455: ("Sudeste dos EUA", False),                      # Carnivine
    511: ("Ásia-Pacífico", False),                        # Pansage
    513: ("Europa, Oriente Médio e África", False),       # Pansear
    515: ("Américas", True),                              # Panpour
    556: ("América Latina", True),                        # Maractus
    561: ("Egito e Grécia", False),                       # Sigilyph
    626: ("Nova York e Paris", False),                    # Bouffalant
    701: ("México", False),                               # Hawlucha
    707: ("França", False),                               # Klefki
    764: ("Havaí", False),                                # Comfey
    874: ("Reino Unido", False),                          # Stonjourner
}


def exclusive_info(species_id: int) -> tuple[str, bool] | None:
    return REGION_EXCLUSIVES.get(species_id)


def trade_only_in_brazil(species_id: int) -> bool:
    """Exclusivo de outra região → para quem joga no Brasil, só por troca."""
    info = REGION_EXCLUSIVES.get(species_id)
    return bool(info and not info[1])


def _extra(rest: str) -> str:
    return FORM_EXTRA_LABEL.get(rest, rest.replace("-", " ").title()) if rest else ""


def _with_extra(label: str, rest: str) -> str:
    extra = _extra(rest)
    return f"{label} ({extra})" if extra else label


def form_label(form_name: str) -> str:
    """
    Rótulo curto da forma:
    'alola' → 'Alola' · 'paldea-combat-breed' → 'Paldea (Combate)' · 'mega-x' → 'Mega X'
    'gmax' → 'Gigantamax' · 'amped-gmax' → 'Gigantamax (Amped)' · 'original-cap' → 'Boné Original'
    'totem-alola' → 'Totem (Alola)' · 'galar-zen' → 'Galar (Zen)' · 'normal' → ''
    """
    category = form_category(form_name)
    tokens = form_name.split("-") if form_name else []
    if category is None:
        return "" if not form_name or form_name == "normal" else form_name.replace("-", " ").title()
    if category == "mega":
        suffix = [t.upper() for t in tokens if t != "mega"]
        return "Mega" + (" " + " ".join(suffix) if suffix else "")
    if category == "gmax":
        return _with_extra("Gigantamax", "-".join(tokens[:-1]))
    if "cap" in tokens:
        return "Boné " + CAP_LABEL.get(tokens[0], tokens[0].title())
    if tokens[0] == "totem":
        rest = "-".join(tokens[1:])
        return f"Totem ({REGION_LABEL.get(rest) or _extra(rest)})" if rest else "Totem"
    if tokens[0] in REGION_LABEL:  # regional e 'galar-zen'
        return _with_extra(REGION_LABEL[tokens[0]], "-".join(tokens[1:]))
    return _extra(form_name)  # 'zen' → 'Zen'


def form_display_name(species_name: str, form_name: str) -> str:
    """'Rattata de Alola' · 'Darmanitan de Galar (Zen)' · 'Mega Charizard X' · 'Charizard Gigantamax'
    · 'Pikachu Boné Original' · 'Raticate Totem (Alola)'."""
    category = form_category(form_name)
    label = form_label(form_name)
    if not label:
        return species_name
    if form_name.split("-")[0] in REGION_LABEL:  # regionais, inclusive 'galar-zen'
        return f"{species_name} de {label}"
    if category == "mega":
        suffix = label.removeprefix("Mega").strip()
        return f"Mega {species_name}" + (f" {suffix}" if suffix else "")
    return f"{species_name} {label}"
