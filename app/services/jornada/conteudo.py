"""Carrega e valida o conteúdo do jogo (app/data/jornada/*.json).

O motor nunca tem nome de criatura/casa fixo no código: tudo vem daqui.
Trocar conteúdo = editar JSON. Uma fase nova = pasta nova faseN/.
"""
from __future__ import annotations

import json
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

DATA_DIR = Path(__file__).resolve().parents[2] / "data" / "jornada"

TIPOS_CASA = {"inicio", "captura", "cidade", "ginasio", "evento", "bonus", "desafio", "fim"}
EFEITOS_EVENTO = {"mover", "pp", "item", "energia", "curar", "sorte", "perde_item"}


class ConteudoInvalido(Exception):
    pass


@dataclass
class Fase:
    numero: int
    regiao: dict
    casas: list[dict]
    criaturas: dict[str, dict]
    eventos: list[dict]
    ginasios: dict[str, dict] = field(default_factory=dict)

    def local_da_casa(self, casa: int) -> dict:
        for loc in self.regiao["locais"]:
            if loc["de"] <= casa <= loc["ate"]:
                return loc
        raise KeyError(casa)

    def indice_local(self, casa: int) -> int:
        """Posição do local na trilha (1..N) — usado na barra de progresso X/10."""
        for i, loc in enumerate(self.regiao["locais"], start=1):
            if loc["de"] <= casa <= loc["ate"]:
                return i
        raise KeyError(casa)


@dataclass
class Conteudo:
    jogo: dict
    itens: dict[str, dict]
    limite_mao: int
    fases: dict[int, Fase]

    def fase(self, numero: int) -> Fase:
        return self.fases[numero]


def _ler(path: Path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def _validar_fase(f: Fase) -> None:
    erros = []
    final = f.regiao["casa_final"]
    if [c["casa"] for c in f.casas] != list(range(final + 1)):
        erros.append(f"casas devem ir de 0 a {final}, sem buracos")
    if f.casas[f.regiao["casa_desafio"]]["tipo"] != "desafio":
        erros.append("casa_desafio não é do tipo 'desafio'")
    for c in f.casas:
        if c["tipo"] not in TIPOS_CASA:
            erros.append(f"casa {c['casa']}: tipo desconhecido {c['tipo']!r}")
        if c["tipo"] == "captura" and c.get("habitat") not in f.criaturas:
            erros.append(f"casa {c['casa']}: habitat {c.get('habitat')!r} não existe")
        if c["tipo"] == "ginasio" and c.get("ginasio") not in f.ginasios:
            erros.append(f"casa {c['casa']}: ginásio {c.get('ginasio')!r} não existe")
    for k, cr in f.criaturas.items():
        nums = cr["captura"]
        if not nums or len(set(nums)) != len(nums) or any(not 1 <= n <= 6 for n in nums):
            erros.append(f"criatura {k}: números de captura inválidos {nums}")
        if cr["estagio"] not in (1, 2, 3):
            erros.append(f"criatura {k}: estágio inválido")
    for ev in f.eventos:
        if ev["efeito"] not in EFEITOS_EVENTO:
            erros.append(f"evento {ev['key']}: efeito desconhecido {ev['efeito']!r}")
    if erros:
        raise ConteudoInvalido(f"Fase {f.numero}: " + "; ".join(erros))


@lru_cache(maxsize=1)
def carregar(data_dir: str | None = None) -> Conteudo:
    base = Path(data_dir) if data_dir else DATA_DIR
    jogo = _ler(base / "jogo.json")
    itens_raw = _ler(base / "itens.json")
    fases = {}
    for pasta in sorted(base.glob("fase*")):
        regiao = _ler(pasta / "regiao.json")
        criaturas = {c["key"]: c for c in _ler(pasta / "criaturas.json")}
        fase = Fase(
            numero=regiao["fase"],
            regiao=regiao,
            casas=_ler(pasta / "tabuleiro.json"),
            criaturas=criaturas,
            eventos=_ler(pasta / "eventos.json"),
            ginasios={g["key"]: g for g in regiao["ginasios"]},
        )
        _validar_fase(fase)
        fases[fase.numero] = fase
    return Conteudo(
        jogo=jogo,
        itens={i["key"]: i for i in itens_raw["itens"]},
        limite_mao=itens_raw["limite_mao"],
        fases=fases,
    )
