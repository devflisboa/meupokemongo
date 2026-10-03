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

# Variedades da PokeAPI tratadas como forma regional colecionável
REGIONAL_VARIETY = re.compile(r"-(alola|galar|hisui|paldea)(-|$)")
# Variedades regionais que NÃO são colecionáveis (totem, boné, modo de batalha)
REGIONAL_SKIP = {"raticate-totem-alola", "pikachu-alola-cap", "darmanitan-galar-zen"}

REGION_LABEL = {"alola": "Alola", "galar": "Galar", "hisui": "Hisui", "paldea": "Paldea"}
FORM_EXTRA_LABEL = {
    "combat-breed": "Combate", "blaze-breed": "Chamas", "aqua-breed": "Aquática",
    "standard": "",  # darmanitan-galar-standard
}

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


def form_label(form_name: str) -> str:
    """'alola' → 'Alola'; 'paldea-combat-breed' → 'Paldea (Combate)'; 'normal' → ''."""
    if not form_name or form_name == "normal":
        return ""
    region, _, rest = form_name.partition("-")
    label = REGION_LABEL.get(region, region.replace("-", " ").title())
    extra = FORM_EXTRA_LABEL.get(rest, rest.replace("-", " ").title()) if rest else ""
    return f"{label} ({extra})" if extra else label
