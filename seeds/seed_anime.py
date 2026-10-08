"""
Seed do módulo anime — lê os arquivos .mp4 da pasta ANIME_VIDEO_FOLDER
e popula as tabelas anime_temporadas e anime_episodios automaticamente.

Padrão de nome esperado: "JN 029 - Uma Visita Inesperada!.mp4"
  └ código: JN | número: 29 | título: Uma Visita Inesperada!

Uso:
  flask --app run:app shell < seeds/seed_anime.py
  ou:
  python seeds/seed_anime.py
"""
import os
import re
import sys

# Permite rodar direto: python seeds/seed_anime.py
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from run import app
from app.extensions import db
from app.models.anime import Temporada, Episodio

# ── Mapa de códigos → informações da temporada ───────────────────────────────
TEMPORADAS_INFO = {
    "OS":  (1,  "Liga Indigo"),
    "OB":  (2,  "Ilhas Laranja"),
    "GS":  (3,  "Liga Johto"),
    "RS":  (4,  "A Jornada de Johto"),
    "MC":  (5,  "Mestre da Liga Johto"),
    "AG":  (6,  "Pokémon Advance"),
    "AGN": (7,  "Pokémon Advance Battle"),
    "DP":  (8,  "Diamante e Pérola"),
    "DPN": (9,  "Pokémon DP: Rivalries!"),
    "BW":  (10, "Pokémon Negro e Branco"),
    "XY":  (11, "Pokémon XY"),
    "XYZ": (12, "Pokémon XYZ"),
    "SM":  (13, "Sol e Lua"),
    "JN":  (14, "Jornadas de Pokémon"),
    "MPM": (15, "Horizontes Pokémon"),
}

_RE_NOME = re.compile(r"^([A-Z]+)\s+(\d+)\s+-\s+(.+?)\.mp4$", re.IGNORECASE)


def parsear_arquivo(nome_arquivo: str):
    """Extrai (codigo, numero, titulo) do nome do arquivo ou retorna None."""
    m = _RE_NOME.match(nome_arquivo)
    if not m:
        return None
    codigo = m.group(1).upper()
    numero = int(m.group(2))
    titulo = m.group(3).strip()
    return codigo, numero, titulo


def run():
    video_folder = app.config.get("ANIME_VIDEO_FOLDER", "")
    if not video_folder or not os.path.isdir(video_folder):
        print(f"ERRO: pasta de vídeos não encontrada: {video_folder!r}")
        print("Configure ANIME_VIDEO_FOLDER no .env ou em config.py")
        return

    arquivos = sorted(f for f in os.listdir(video_folder) if f.lower().endswith(".mp4"))
    print(f"Encontrados {len(arquivos)} arquivos .mp4 em {video_folder!r}\n")

    codigos_vistos = {}

    with app.app_context():
        for nome in arquivos:
            parsed = parsear_arquivo(nome)
            if not parsed:
                print(f"  [ignorado] {nome}")
                continue

            codigo, numero, titulo = parsed

            # Garante que a temporada existe
            if codigo not in codigos_vistos:
                t = Temporada.query.filter_by(codigo=codigo).first()
                if not t:
                    num_temp, titulo_temp = TEMPORADAS_INFO.get(codigo, (99, f"Temporada {codigo}"))
                    t = Temporada(
                        codigo=codigo,
                        numero=num_temp,
                        titulo=titulo_temp,
                        ordem=num_temp,
                    )
                    db.session.add(t)
                    db.session.flush()
                    print(f"  [nova temporada] {codigo} — {t.titulo}")
                codigos_vistos[codigo] = t
            else:
                t = codigos_vistos[codigo]

            # Verifica se episódio já existe
            ep = Episodio.query.filter_by(temporada_id=t.id, numero=numero).first()
            if ep:
                # Atualiza arquivo caso tenha mudado
                if ep.arquivo != nome:
                    ep.arquivo = nome
                    print(f"  [atualizado] {codigo} EP {numero:03d} — {titulo}")
            else:
                ep = Episodio(
                    temporada_id=t.id,
                    numero=numero,
                    titulo=titulo,
                    arquivo=nome,
                )
                db.session.add(ep)
                print(f"  [inserido]   {codigo} EP {numero:03d} — {titulo}")

        db.session.commit()
        print("\nSeed concluído!")

        # Resumo
        for codigo, t in sorted(codigos_vistos.items()):
            total = Episodio.query.filter_by(temporada_id=t.id).count()
            print(f"  {codigo}: {total} episódios")


if __name__ == "__main__":
    run()
