# MeuPokémonGO

Portfólio pessoal para gerenciar a coleção de Pokémon GO — rastreia Pokémon capturados, evoluções pendentes e oportunidades de troca com outros treinadores.

**Treinador:** FelipeLisboa · **Produção:** http://casakek.duckdns.org:5001

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + Flask 3.1.3 |
| ORM | SQLAlchemy 2.x + Flask-Migrate |
| Auth | Flask-Login + Werkzeug |
| Banco | MySQL 8.0 (PyMySQL) |
| Frontend | Jinja2 + Tailwind CSS CDN |
| Deploy | Docker Compose + Gunicorn |
| Dados | PokéAPI (sync automático) |

---

## Estrutura

```
app/
├── blueprints/        # Rotas organizadas por módulo
│   ├── main/          # Dashboard + eventos
│   ├── auth/          # Login / Registro / Logout
│   ├── pokedex/       # Pokédex completa (1025 espécies)
│   ├── collection/    # Gerenciar coleção do treinador
│   ├── trades/        # Oportunidades de troca
│   ├── friends/       # Lista de amigos
│   ├── import_/       # Importar CSV/JSON (PokeGenie)
│   ├── wishlist/      # Lista de desejos
│   └── admin/         # Painel administrativo
├── models/            # SQLAlchemy: User, Species, Form, UserCollection…
├── services/          # Lógica de negócio: stats, matches, import, sync
├── providers/         # Integração com PokéAPI (com cache no banco)
├── templates/         # HTML Jinja2 com Tailwind CSS
└── config.py          # Configurações + timezone Brasília (UTC-3)
```

---

## Variáveis de ambiente

Copie `.env.example` para `.env` e ajuste:

```env
SECRET_KEY=troque-por-chave-segura
DB_HOST=db
DB_PORT=3306
DB_NAME=meupokemongo
DB_USER=root
DB_PASSWORD=senha-aqui
FLASK_ENV=production
TELEGRAM_BOT_TOKEN=          # opcional
TELEGRAM_ADMIN_CHAT_ID=      # opcional
```

---

## Desenvolvimento local

```bash
# 1. Subir banco + app
docker compose up -d

# 2. Aplicar migrations (primeira vez)
docker exec meupokemongo-web-1 flask db upgrade

# 3. Sincronizar Pokédex com PokéAPI (1025 espécies, ~15 min)
docker exec meupokemongo-web-1 flask sync-pokedex

# 4. Acessar
# http://localhost:5000
```

---

## Deploy em produção

```powershell
# Apenas código (sem rebuild)
.\deploy.ps1

# Com rebuild da imagem Docker
.\deploy.ps1 -Build
```

O script faz: `git push` → SSH no servidor → `git pull` → `docker-compose -f docker-compose.prod.yml up -d [--build]`

**Servidor:** `casakek.duckdns.org:64622` · Pasta: `/home/felipe/sistemas/MEUPOKEMONGO`

---

## Importar coleção via PokeGenie

1. Instale **PokeGenie** no celular
2. Escaneie seus Pokémon (ou use a exportação automática)
3. Exporte CSV pelo app
4. Acesse `/import/` no site e faça o upload

---

## Pokédex do treinador (28/09/2026)

| Região | Capturados | Total | % |
|--------|-----------|-------|---|
| Kanto | 151 | 151 | 100% ✅ |
| Johto | 100 | 100 | 100% ✅ |
| Hoenn | 130 | 135 | 96% |
| Sinnoh | 85 | 107 | 79% |
| Unova | 87 | 156 | 56% |
| Kalos | 42 | 72 | 58% |
| Alola | 34 | 86 | 40% |
| Galar | 32 | 89 | 36% |
| Hisui | 2 | 7 | 29% |
| Paldea | 35 | 120 | 29% |
| Indefinida | 1 | 2 | 50% |
| **Total** | **699** | **1025** | **68%** |

---

## Licença

Projeto pessoal — dados de Pokémon GO pertencem à Niantic / The Pokémon Company.
