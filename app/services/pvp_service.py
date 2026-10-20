"""
Motor de cálculo de Rank PVP para Pokémon GO.

Fórmula oficial:
  CP = floor(0.1 * (ATK + iv_atk) * sqrt(DEF + iv_def) * sqrt(STA + iv_sta) * CPM²)

CPM (CP Multiplier) por nível — tabela oficial Niantic (nível 1 a 50, passo 0.5).
Rank é ordenado por "stat product": (ATK+ivA)*CPM × (DEF+ivD)*CPM × (STA+ivS)*CPM
O Rank 1 é o maior stat product que ainda cabe no limite de CP da liga.
"""

import math

# CPM por nível (nível 1 até 50 inclusive, step 0.5)
_CPM: list[float] = [
    0.094,     # 1
    0.135137432,
    0.16639787,
    0.192650919,
    0.21573247,
    0.236572661,
    0.25572005,
    0.273530381,
    0.29024988,
    0.306057377,
    0.32100438,  # 6
    0.335445036,
    0.34921268,
    0.362457751,
    0.37523559,
    0.387592406,
    0.39956728,
    0.411193551,
    0.42250001,
    0.432926419,
    0.44310755,  # 11
    0.453059958,
    0.46279839,
    0.472336083,
    0.48168495,
    0.4908558,
    0.49985844,
    0.508701765,
    0.51739395,
    0.525942511,
    0.53435433,  # 16
    0.542635767,
    0.55079269,
    0.558830576,
    0.56675452,
    0.574569153,
    0.58227891,
    0.589887917,
    0.59740001,
    0.604818814,
    0.61215729,  # 21
    0.619399365,
    0.62656069,
    0.633644533,
    0.64065295,
    0.647592566,
    0.65443563,
    0.661214806,
    0.66741719,  # 25 (Nível 13 = índice 24)
    0.673814295,
    0.67985001,
    0.685874864,
    0.69169989,
    0.697524052,
    0.70329409,
    0.708884849,
    0.71432697,
    0.719597564,
    0.72471963,  # 30
    0.729663968,
    0.73455834,
    0.739393,
    0.744184,
    0.748927,
    0.753623,
    0.758281,
    0.762896,
    0.767469,
    0.7720,      # 40
    0.776491,
    0.780941,
    0.785353,
    0.789725,
    0.794061,
    0.798358,
    0.802619,
    0.806842,
    0.811029,
    0.815200,    # 50
]

# Monta dict: nível (float, passo 0.5) → CPM
LEVEL_CPM: dict[float, float] = {}
for _i, _cpm in enumerate(_CPM):
    _level = 1.0 + _i * 0.5
    LEVEL_CPM[_level] = _cpm

LEVELS = sorted(LEVEL_CPM.keys())  # 1.0, 1.5, 2.0 ... 50.0


def calc_cp(base_atk: int, base_def: int, base_sta: int,
            iv_atk: int, iv_def: int, iv_sta: int,
            cpm: float) -> int:
    """Retorna o CP para as IVs e nível dados."""
    atk = (base_atk + iv_atk) * cpm
    def_ = math.sqrt((base_def + iv_def) * cpm)   # ← CPM entra no sqrt
    sta = math.sqrt((base_sta + iv_sta) * cpm)
    return max(10, int(0.1 * atk * def_ * sta))


def stat_product(base_atk: int, base_def: int, base_sta: int,
                 iv_atk: int, iv_def: int, iv_sta: int,
                 cpm: float) -> float:
    """Produto de stats — métrica de bulk PVP."""
    return ((base_atk + iv_atk) * cpm *
            (base_def + iv_def) * cpm *
            (base_sta + iv_sta) * cpm)


def best_level_for_cp_limit(base_atk: int, base_def: int, base_sta: int,
                             iv_atk: int, iv_def: int, iv_sta: int,
                             cp_limit: int | None) -> float:
    """
    Retorna o nível máximo em que este conjunto de IVs fica dentro do cp_limit.
    Se cp_limit é None (Liga Mestre), retorna 50.0.
    """
    if cp_limit is None:
        return 50.0
    best = 1.0
    for lv in LEVELS:
        cpm = LEVEL_CPM[lv]
        cp = calc_cp(base_atk, base_def, base_sta, iv_atk, iv_def, iv_sta, cpm)
        if cp <= cp_limit:
            best = lv
        else:
            break
    return best


def rank_ivs(base_atk: int, base_def: int, base_sta: int,
             cp_limit: int | None) -> list[dict]:
    """
    Calcula o rank de todas as 4096 combinações de IVs (0–15 cada) para um Pokémon.
    Retorna lista ordenada por stat_product decrescente.
    Cada item: {iv_atk, iv_def, iv_sta, level, cp, sp, rank}
    """
    results = []
    for ia in range(16):
        for id_ in range(16):
            for is_ in range(16):
                lv = best_level_for_cp_limit(
                    base_atk, base_def, base_sta, ia, id_, is_, cp_limit)
                cpm = LEVEL_CPM[lv]
                cp = calc_cp(base_atk, base_def, base_sta, ia, id_, is_, cpm)
                sp = stat_product(base_atk, base_def, base_sta, ia, id_, is_, cpm)
                results.append({
                    "iv_atk": ia, "iv_def": id_, "iv_sta": is_,
                    "level": lv, "cp": cp, "sp": sp,
                })

    results.sort(key=lambda x: x["sp"], reverse=True)
    for i, r in enumerate(results):
        r["rank"] = i + 1
    return results


def rank_of(base_atk: int, base_def: int, base_sta: int,
            iv_atk: int, iv_def: int, iv_sta: int,
            cp_limit: int | None) -> dict:
    """
    Retorna o rank (1 = melhor) de IVs específicas dentro da liga.
    Também retorna o nível, CP e % do stat product máximo.
    """
    all_ranks = rank_ivs(base_atk, base_def, base_sta, cp_limit)
    best_sp = all_ranks[0]["sp"] if all_ranks else 1.0

    for r in all_ranks:
        if r["iv_atk"] == iv_atk and r["iv_def"] == iv_def and r["iv_sta"] == iv_sta:
            return {
                **r,
                "sp_pct": round(r["sp"] / best_sp * 100, 2) if best_sp else 0,
                "total_combinations": len(all_ranks),
            }
    return {}
