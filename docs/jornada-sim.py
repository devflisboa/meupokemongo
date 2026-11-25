"""Simulação Monte Carlo do balanceamento da Jornada (Fase 1) — ver SPEC-JORNADA.md §9.

Uso: python docs/jornada-sim.py
Reflete as regras da spec: sem requisitos no fim, volta para a casa 0 (volta seguinte);
Estágio 1 com 2 números de captura, Estágio 2+ com 1 número e PP x estágio; nunca sorteia
criatura que o jogador já tem (33 por estágio); ginásio ~55% de vitória (+40 PP +1 item). Ajuste e rode de novo ao
mudar regras; depois do lançamento, calibre com os dados reais de game_turns.
"""
import random
import statistics as st

CAP = {1, 4, 6, 8, 10, 12, 14, 16, 18, 19, 22, 23, 26, 28, 30, 31, 35, 37, 39, 42, 44,
       46, 47, 50, 51, 54, 55, 58, 60, 62, 63, 67, 68}
CITY = {2, 7, 11, 21, 29, 36, 45, 53, 61, 69}
GYM = {17, 25, 33, 41, 49, 57, 65}
EV = {3, 9, 13, 20, 27, 32, 38, 43, 52, 59, 66}
BON = {5, 15, 24, 34, 40, 48, 56, 64}  # 70 = +100
ITEMS = [("isca", 35), ("tonico", 30), ("rede", 20), ("elixir", 12), ("amuleto", 3)]
NEED_PP, NEED_TEAM = 300, 6
POOL = {1: 33, 2: 33, 3: 33}  # criaturas por estágio


def draw():
    return random.choices([i for i, _ in ITEMS], [w for _, w in ITEMS])[0]


def attempt(hand, n_nums):
    nums = random.sample(range(1, 7), n_nums)
    r = random.randint(1, 6)
    if r in nums:
        return True
    if "rede" in hand and (r - 1 in nums or r + 1 in nums):
        hand.remove("rede"); return True
    if "isca" in hand and r + 1 in nums:
        hand.remove("isca"); return True
    if "amuleto" in hand:
        hand.remove("amuleto"); return True
    return False


def partida():
    pos = pp = team = turns = 0
    volta = 1
    hand, owned = ["isca", "isca"], {1: 0, 2: 0, 3: 0}
    while turns < 2000:
        turns += 1
        pos = min(pos + random.randint(1, 6), 71)
        if pos == 71:
            if pp >= NEED_PP and team >= NEED_TEAM:
                return turns, volta
            volta += 1; pos = 0; continue
        if pos in CAP:
            est = min(volta, 3)
            while est <= 3 and owned[est] >= POOL[est]:
                est += 1
            if est > 3:
                pp += 10; continue
            if attempt(hand, 2 if est == 1 else 1):
                owned[est] += 1; team += 1; pp += 25 * est
        elif pos in CITY:
            hand += [draw(), draw()]
        elif pos in GYM:
            if random.random() < 0.55:
                pp += 40; hand.append(draw())
        elif pos in BON:
            pp += 50
        elif pos == 70:
            pp += 100
        elif pos in EV:
            e = random.choice(["+30", "+20", "-20", "fwd2", "back2", "item"])
            if e[0] in "+-":
                pp = max(0, pp + int(e))
            elif e == "item":
                hand.append(draw())
            elif e == "fwd2":
                pos = min(pos + 2, 70)
            else:
                pos = max(pos - 2, 0)
    return turns, volta


if __name__ == "__main__":
    N = 5000
    R = [partida() for _ in range(N)]
    t = sorted(r[0] for r in R)
    print("rolagens p/ zerar: p10", t[N // 10], "mediana", t[N // 2], "p90", t[N * 9 // 10], "max", t[-1])
    for v in (1, 2):
        print(f"% zera na volta {v}", round(100 * sum(r[1] == v for r in R) / N))
    print("% precisa de 3+ voltas", round(100 * sum(r[1] >= 3 for r in R) / N))
    for e in (6, 8, 10):
        print(f"{e} rolagens/dia -> mediana {t[N // 2] / e:.1f} dias, p90 {t[N * 9 // 10] / e:.1f} dias")
