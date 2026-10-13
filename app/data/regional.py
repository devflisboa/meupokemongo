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


REGION_COORDS: dict[int, list[list[float]]] = {
    # Farfetch'd — Ásia
    83: [
        [35.7150,  139.7738],  # Tokyo: Ueno Park
        [37.5796,  126.9770],  # Seoul: Gyeongbokgung Palace
        [31.2350,  121.4905],  # Shanghai: The Bund
    ],
    # Kangaskhan — Austrália e Nova Zelândia
    115: [
        [-33.8740,  151.2099], # Sydney: Hyde Park
        [-37.8182,  144.9691], # Melbourne: Federation Square
    ],
    # Mr. Mime — Europa
    122: [
        [48.8548,    2.2945],  # Paris: Champ de Mars (Torre Eiffel)
        [51.5085,   -0.1660],  # London: Hyde Park
        [52.5144,   13.3501],  # Berlin: Tiergarten
    ],
    # Tauros — América do Norte
    128: [
        [40.7851,  -73.9683],  # New York: Central Park
        [41.8827,  -87.6233],  # Chicago: Millennium Park
        [34.1184, -118.3004],  # Los Angeles: Griffith Park
    ],
    # Heracross — América Latina (aparece no Brasil)
    214: [
        [-3.7298,  -38.5002],  # Fortaleza: Beira Mar
        [-22.9368, -43.1730],  # Rio de Janeiro: Aterro do Flamengo
        [-23.5918, -46.6570],  # São Paulo: Parque do Ibirapuera
        [4.6574,   -74.1027],  # Bogotá: Parque Simón Bolívar
        [-34.6169, -58.3634],  # Buenos Aires: Puerto Madero
    ],
    # Corsola — faixa tropical (aparece no Brasil)
    222: [
        [-3.7431,  -38.4644],  # Fortaleza: Praia do Futuro
        [-12.9714, -38.5097],  # Salvador: Pelourinho
        [-3.0619,  -60.0677],  # Manaus: Praia da Ponta Negra
        [25.7853,  -80.1300],  # Miami: South Beach
    ],
    # Torkoal — Sul e Sudeste da Ásia
    324: [
        [18.9219,   72.8348],  # Mumbai: Gateway of India
        [13.7500,  100.4913],  # Bangkok: Grand Palace
        [1.2816,   103.8636],  # Singapura: Gardens by the Bay
    ],
    # Tropius — África e Mediterrâneo
    357: [
        [-1.2892,   36.8219],  # Nairobi: Uhuru Park
        [-33.9031,  18.4178],  # Cape Town: V&A Waterfront
        [30.0590,   31.2263],  # Cairo: Al-Azhar Park
    ],
    # Relicanth — Nova Zelândia e ilhas do Pacífico
    369: [
        [-41.2865,  174.7762], # Wellington: Waterfront
        [-36.8617,  174.7713], # Auckland: Auckland Domain
    ],
    # Pachirisu — Alasca, Canadá e Rússia
    417: [
        [64.8401,  -147.7228], # Fairbanks: Pioneer Park
        [61.2181,  -149.9003], # Anchorage: Town Square Park
        [60.7212,  -135.0568], # Whitehorse: Rotary Peace Park
    ],
    # Mime Jr. — Europa (mesmas regiões do Mr. Mime)
    439: [
        [48.8548,    2.2945],  # Paris: Champ de Mars
        [51.5085,   -0.1660],  # London: Hyde Park
        [52.5144,   13.3501],  # Berlin: Tiergarten
    ],
    # Chatot — Hemisfério Sul (aparece no Brasil)
    441: [
        [-22.9676, -43.2194],  # Rio de Janeiro: Jardim Botânico
        [-3.7215,  -38.5153],  # Fortaleza: Dragão do Mar
        [-34.5705, -58.4194],  # Buenos Aires: Parque Palermo
        [-33.8979,  151.2318], # Sydney: Centennial Park
    ],
    # Carnivine — Sudeste dos EUA
    455: [
        [25.7748,  -80.1836],  # Miami: Bayfront Park
        [29.9584,  -90.0634],  # New Orleans: Jackson Square
        [33.7601,  -84.3921],  # Atlanta: Centennial Olympic Park
    ],
    # Pansage — Ásia-Pacífico
    511: [
        [35.6856,  139.7104],  # Tokyo: Shinjuku Gyoen
        [-33.8713,  151.1994], # Sydney: Darling Harbour
        [25.0338,  121.5448],  # Taipei: Daan Park
    ],
    # Pansear — Europa, Oriente Médio e África
    513: [
        [51.5080,   -0.1281],  # London: Trafalgar Square
        [25.1972,   55.2744],  # Dubai: Downtown / Burj Khalifa
        [-26.1545,  28.0347],  # Johannesburg: Zoo Lake
    ],
    # Panpour — Américas (aparece no Brasil)
    515: [
        [-3.7473,  -38.4766],  # Fortaleza: Parque do Cocó
        [-23.5918, -46.6570],  # São Paulo: Parque do Ibirapuera
        [40.7007,  -73.9964],  # New York: Brooklyn Bridge Park
        [4.6574,   -74.1027],  # Bogotá: Parque Simón Bolívar
    ],
    # Maractus — América Latina (aparece no Brasil)
    556: [
        [-3.7215,  -38.5153],  # Fortaleza: Dragão do Mar
        [19.4204,  -99.1963],  # Cidade do México: Chapultepec
        [10.4236,  -75.5519],  # Cartagena: Ciudad Amurallada
    ],
    # Sigilyph — Egito e Grécia
    561: [
        [30.0590,   31.2263],  # Cairo: Praça Tahrir (Al-Azhar Park)
        [37.9761,   23.7261],  # Atenas: Monastiraki Square
        [41.0055,   28.9769],  # Istambul: Sultanahmet / Hagia Sophia
    ],
    # Bouffalant — Nova York e Paris
    626: [
        [40.7851,  -73.9683],  # New York: Central Park
        [48.8623,    2.2891],  # Paris: Trocadéro
    ],
    # Hawlucha — México
    701: [
        [19.4204,  -99.1963],  # Cidade do México: Chapultepec
        [20.9674,  -89.6235],  # Mérida: Paseo de Montejo
    ],
    # Klefki — França
    707: [
        [48.8548,    2.2945],  # Paris: Champ de Mars (Torre Eiffel)
        [45.7573,    4.8327],  # Lyon: Place Bellecour
    ],
    # Comfey — Havaí
    764: [
        [21.2765,  -157.8268], # Honolulu: Waikiki Beach
        [21.3069,  -157.8583], # Honolulu: Downtown / Aloha Tower
    ],
    # Stonjourner — Reino Unido
    874: [
        [51.1789,   -1.8262],  # Amesbury: cidade próxima a Stonehenge
        [51.5081,   -0.0759],  # London: Tower of London
        [55.9533,   -3.1883],  # Edinburgh: Old Town / Royal Mile
    ],
}


def exclusive_info(species_id: int) -> tuple[str, bool] | None:
    return REGION_EXCLUSIVES.get(species_id)


def exclusive_full(species_id: int) -> dict | None:
    """Returns {region, in_brazil, coords} or None if not a regional exclusive."""
    info = REGION_EXCLUSIVES.get(species_id)
    if not info:
        return None
    region, in_brazil = info
    return {"region": region, "in_brazil": in_brazil, "coords": REGION_COORDS.get(species_id, [])}


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
