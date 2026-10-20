"""
Banco de moves PVP e simulador de batalha 1v1 para Pokémon GO.
Stats: pvpoke.com (Season 23). Power = battle power (não o tooltip do jogo).
"""
import math

# ── Fast Moves: {name: {power, energy, turns, type}} ─────────────────────────
# turns = ticks de 500ms de cooldown
FAST_MOVES: dict[str, dict] = {
    "Bubble":        {"power": 8,  "energy": 11.5, "turns": 3, "type": "water"},
    "Charm":         {"power": 16, "energy": 6,    "turns": 3, "type": "fairy"},
    "Confusion":     {"power": 20, "energy": 15,   "turns": 4, "type": "psychic"},
    "Counter":       {"power": 12, "energy": 8.7,  "turns": 2, "type": "fighting"},
    "Dragon Breath": {"power": 6,  "energy": 4,    "turns": 1, "type": "dragon"},
    "Dragon Tail":   {"power": 15, "energy": 9.5,  "turns": 3, "type": "dragon"},
    "Feint Attack":  {"power": 10, "energy": 9,    "turns": 3, "type": "dark"},
    "Fury Cutter":   {"power": 3,  "energy": 9,    "turns": 2, "type": "bug"},
    "Hex":           {"power": 6,  "energy": 8,    "turns": 2, "type": "ghost"},
    "Ice Shard":     {"power": 12, "energy": 10,   "turns": 3, "type": "ice"},
    "Incinerate":    {"power": 29, "energy": 12.5, "turns": 5, "type": "fire"},
    "Infestation":   {"power": 10, "energy": 14,   "turns": 3, "type": "bug"},
    "Lock On":       {"power": 1,  "energy": 5,    "turns": 1, "type": "normal"},
    "Mud Shot":      {"power": 3,  "energy": 9,    "turns": 1, "type": "ground"},
    "Powder Snow":   {"power": 5,  "energy": 8,    "turns": 1, "type": "ice"},
    "Psycho Cut":    {"power": 5,  "energy": 8.5,  "turns": 2, "type": "psychic"},
    "Razor Leaf":    {"power": 13, "energy": 7,    "turns": 3, "type": "grass"},
    "Shadow Claw":   {"power": 9,  "energy": 9,    "turns": 2, "type": "ghost"},
    "SmackDown":     {"power": 18, "energy": 9,    "turns": 3, "type": "rock"},
    "Snarl":         {"power": 5,  "energy": 8,    "turns": 2, "type": "dark"},
    "Water Gun":     {"power": 3,  "energy": 3,    "turns": 1, "type": "water"},
    "Waterfall":     {"power": 16, "energy": 9,    "turns": 3, "type": "water"},
    "Wing Attack":   {"power": 8,  "energy": 7,    "turns": 2, "type": "flying"},
    "Yawn":          {"power": 0,  "energy": 6,    "turns": 3, "type": "normal"},
}

# ── Charged Moves: {name: {power, energy, type}} ─────────────────────────────
CHARGED_MOVES: dict[str, dict] = {
    "Aerial Ace":      {"power": 55,  "energy": 45, "type": "flying"},
    "Aeroblast+":      {"power": 170, "energy": 75, "type": "flying"},
    "Blizzard":        {"power": 130, "energy": 75, "type": "ice"},
    "Body Slam":       {"power": 60,  "energy": 35, "type": "normal"},
    "Brave Bird":      {"power": 130, "energy": 55, "type": "flying"},
    "Breaking Swipe":  {"power": 50,  "energy": 35, "type": "dragon"},
    "Bubble Beam":     {"power": 25,  "energy": 40, "type": "water"},
    "Bug Buzz":        {"power": 100, "energy": 60, "type": "bug"},
    "Cross Poison":    {"power": 70,  "energy": 35, "type": "poison"},
    "Dark Pulse":      {"power": 80,  "energy": 50, "type": "dark"},
    "Draco Meteor":    {"power": 150, "energy": 65, "type": "dragon"},
    "Dragon Claw":     {"power": 50,  "energy": 35, "type": "dragon"},
    "Dragon Pulse":    {"power": 90,  "energy": 60, "type": "dragon"},
    "Dynamax Cannon":  {"power": 100, "energy": 40, "type": "dragon"},
    "Earth Power":     {"power": 100, "energy": 55, "type": "ground"},
    "Earthquake":      {"power": 120, "energy": 65, "type": "ground"},
    "Energy Ball":     {"power": 90,  "energy": 55, "type": "grass"},
    "Fire Blast":      {"power": 140, "energy": 80, "type": "fire"},
    "Flame Charge":    {"power": 65,  "energy": 50, "type": "fire"},
    "Flamethrower":    {"power": 90,  "energy": 55, "type": "fire"},
    "Flash Cannon":    {"power": 100, "energy": 70, "type": "steel"},
    "Focus Blast":     {"power": 140, "energy": 75, "type": "fighting"},
    "Foul Play":       {"power": 70,  "energy": 45, "type": "dark"},
    "Grass Knot":      {"power": 90,  "energy": 50, "type": "grass"},
    "Heavy Slam":      {"power": 70,  "energy": 50, "type": "steel"},
    "Hydro Cannon":    {"power": 80,  "energy": 40, "type": "water"},
    "Ice Beam":        {"power": 90,  "energy": 55, "type": "ice"},
    "Ice Punch":       {"power": 55,  "energy": 40, "type": "ice"},
    "Icicle Spear":    {"power": 60,  "energy": 40, "type": "ice"},
    "Icy Wind":        {"power": 60,  "energy": 45, "type": "ice"},
    "Iron Head":       {"power": 70,  "energy": 50, "type": "steel"},
    "Last Resort":     {"power": 90,  "energy": 55, "type": "normal"},
    "Moonblast":       {"power": 110, "energy": 60, "type": "fairy"},
    "Night Slash":     {"power": 50,  "energy": 35, "type": "dark"},
    "Oblivion Wing":   {"power": 80,  "energy": 40, "type": "flying"},
    "Outrage":         {"power": 110, "energy": 60, "type": "dragon"},
    "Play Rough":      {"power": 90,  "energy": 60, "type": "fairy"},
    "Power-Up Punch":  {"power": 20,  "energy": 35, "type": "fighting"},
    "Psyshock":        {"power": 70,  "energy": 45, "type": "psychic"},
    "Psychic":         {"power": 90,  "energy": 55, "type": "psychic"},
    "Rock Slide":      {"power": 80,  "energy": 45, "type": "rock"},
    "Seed Bomb":       {"power": 55,  "energy": 40, "type": "grass"},
    "Shadow Ball":     {"power": 100, "energy": 55, "type": "ghost"},
    "Shadow Sneak":    {"power": 50,  "energy": 45, "type": "ghost"},
    "Sky Attack":      {"power": 80,  "energy": 45, "type": "flying"},
    "Stone Edge":      {"power": 100, "energy": 55, "type": "rock"},
    "Surf":            {"power": 65,  "energy": 40, "type": "water"},
    "Water Pulse":     {"power": 70,  "energy": 60, "type": "water"},
}

# ── Tabela de efetividade GO ─────────────────────────────────────────────────
# SE=1.6 / NVE=0.625 / imune→0.390625 (não existe imunidade real no GO)
TYPE_CHART: dict[str, dict[str, float]] = {
    "normal":   {"rock": 0.625, "ghost": 0.390625, "steel": 0.625},
    "fire":     {"fire": 0.625, "water": 0.625, "grass": 1.6, "ice": 1.6,
                 "bug": 1.6, "rock": 0.625, "dragon": 0.625, "steel": 1.6},
    "water":    {"fire": 1.6, "water": 0.625, "grass": 0.625, "ground": 1.6,
                 "rock": 1.6, "dragon": 0.625},
    "electric": {"water": 1.6, "electric": 0.625, "grass": 0.625, "ground": 0.390625,
                 "flying": 1.6, "dragon": 0.625},
    "grass":    {"fire": 0.625, "water": 1.6, "grass": 0.625, "poison": 0.625,
                 "ground": 1.6, "flying": 0.625, "bug": 0.625, "rock": 1.6,
                 "dragon": 0.625, "steel": 0.625},
    "ice":      {"water": 0.625, "grass": 1.6, "ice": 0.625, "ground": 1.6,
                 "flying": 1.6, "dragon": 1.6, "steel": 0.625},
    "fighting": {"normal": 1.6, "ice": 1.6, "poison": 0.625, "flying": 0.625,
                 "psychic": 0.625, "bug": 0.625, "rock": 1.6, "ghost": 0.390625,
                 "dark": 1.6, "steel": 1.6, "fairy": 0.625},
    "poison":   {"grass": 1.6, "poison": 0.625, "ground": 0.625, "rock": 0.625,
                 "ghost": 0.625, "steel": 0.390625, "fairy": 1.6},
    "ground":   {"fire": 1.6, "electric": 1.6, "grass": 0.625, "poison": 1.6,
                 "flying": 0.390625, "bug": 0.625, "rock": 1.6, "steel": 1.6},
    "flying":   {"electric": 0.625, "grass": 1.6, "fighting": 1.6, "bug": 1.6,
                 "rock": 0.625, "steel": 0.625},
    "psychic":  {"fighting": 1.6, "poison": 1.6, "psychic": 0.625, "dark": 0.390625,
                 "steel": 0.625},
    "bug":      {"fire": 0.625, "grass": 1.6, "fighting": 0.625, "flying": 0.625,
                 "ghost": 0.625, "psychic": 1.6, "dark": 1.6, "steel": 0.625, "fairy": 0.625},
    "rock":     {"fire": 1.6, "ice": 1.6, "fighting": 0.625, "ground": 0.625,
                 "flying": 1.6, "bug": 1.6, "steel": 0.625},
    "ghost":    {"normal": 0.390625, "ghost": 1.6, "psychic": 1.6, "dark": 0.625},
    "dragon":   {"dragon": 1.6, "steel": 0.625, "fairy": 0.390625},
    "dark":     {"fighting": 0.625, "ghost": 1.6, "psychic": 1.6, "dark": 0.625, "fairy": 0.625},
    "steel":    {"fire": 0.625, "water": 0.625, "electric": 0.625, "ice": 1.6,
                 "rock": 1.6, "steel": 0.625, "fairy": 1.6},
    "fairy":    {"fire": 0.625, "fighting": 1.6, "poison": 0.625, "dragon": 1.6,
                 "dark": 1.6, "steel": 0.625},
}

ALL_TYPES = sorted(TYPE_CHART.keys())


def type_effectiveness(move_type: str, defender_types: list[str]) -> float:
    """Multiplicador de tipo GO (inclui dupla fraqueza/resistência)."""
    chart = TYPE_CHART.get(move_type, {})
    mult = 1.0
    for dt in defender_types:
        mult *= chart.get(dt, 1.0)
    return mult


def _move_damage(power: int, atk_eff: float, def_eff: float,
                 move_type: str, atk_types: list[str], def_types: list[str]) -> int:
    """Fórmula oficial GO PVP: floor(0.5 × power × stab × eff × atk/def) + 1."""
    stab = 1.2 if move_type in atk_types else 1.0
    eff  = type_effectiveness(move_type, def_types)
    return max(1, math.floor(0.5 * power * stab * eff * (atk_eff / def_eff)) + 1)


def simulate_battle(pkm_a: dict, pkm_b: dict,
                    shields_a: int = 2, shields_b: int = 2) -> dict:
    """
    Simulação 1v1 simplificada de PVP.

    Cada pkm deve ter:
      atk_eff, def_eff, hp_max  ← calculados de (base+iv)*CPM
      types: [str]
      fast_move: str
      charged_move: str
    """
    _DEF_FAST    = {"power": 5,  "energy": 6,  "turns": 2, "type": "normal"}
    _DEF_CHARGED = {"power": 80, "energy": 50, "type": "normal"}

    fm_a = FAST_MOVES.get(pkm_a.get("fast_move", ""),    _DEF_FAST)
    cm_a = CHARGED_MOVES.get(pkm_a.get("charged_move", ""), _DEF_CHARGED)
    fm_b = FAST_MOVES.get(pkm_b.get("fast_move", ""),    _DEF_FAST)
    cm_b = CHARGED_MOVES.get(pkm_b.get("charged_move", ""), _DEF_CHARGED)

    hp_a, hp_b     = pkm_a["hp_max"], pkm_b["hp_max"]
    en_a = en_b    = 0
    sh_a, sh_b     = shields_a, shields_b
    next_a = next_b = 0   # próximo tick em que cada um pode atacar
    turn = 0

    while hp_a > 0 and hp_b > 0 and turn < 400:
        turn += 1

        # --- A ataca ---
        if turn >= next_a:
            if en_a >= cm_a["energy"]:
                dmg = _move_damage(cm_a["power"], pkm_a["atk_eff"], pkm_b["def_eff"],
                                   cm_a["type"], pkm_a["types"], pkm_b["types"])
                if sh_b > 0:
                    sh_b -= 1; dmg = 1
                hp_b -= dmg
                en_a -= cm_a["energy"]
                next_a = turn + 1
            else:
                dmg = _move_damage(fm_a["power"], pkm_a["atk_eff"], pkm_b["def_eff"],
                                   fm_a["type"], pkm_a["types"], pkm_b["types"])
                hp_b -= dmg
                en_a  = min(100, en_a + fm_a["energy"])
                next_a = turn + int(fm_a["turns"])

        if hp_b <= 0:
            break

        # --- B ataca ---
        if turn >= next_b:
            if en_b >= cm_b["energy"]:
                dmg = _move_damage(cm_b["power"], pkm_b["atk_eff"], pkm_a["def_eff"],
                                   cm_b["type"], pkm_b["types"], pkm_a["types"])
                if sh_a > 0:
                    sh_a -= 1; dmg = 1
                hp_a -= dmg
                en_b -= cm_b["energy"]
                next_b = turn + 1
            else:
                dmg = _move_damage(fm_b["power"], pkm_b["atk_eff"], pkm_a["def_eff"],
                                   fm_b["type"], pkm_b["types"], pkm_a["types"])
                hp_a -= dmg
                en_b  = min(100, en_b + fm_b["energy"])
                next_b = turn + int(fm_b["turns"])

    if hp_b <= 0 and hp_a > 0:
        winner = "a"
    elif hp_a <= 0 and hp_b > 0:
        winner = "b"
    else:
        winner = "draw"

    return {
        "winner": winner,
        "turns": turn,
        "hp_a": max(0, hp_a),
        "hp_b": max(0, hp_b),
        "hp_a_max": pkm_a["hp_max"],
        "hp_b_max": pkm_b["hp_max"],
        "shields_a_used": shields_a - sh_a,
        "shields_b_used": shields_b - sh_b,
    }
