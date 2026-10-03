# MeuPokémonGO

Portfólio pessoal para gerenciar coleção de Pokémon GO — rastreia capturas, evoluções pendentes, oportunidades de troca e estatísticas de progresso. Acesso público por link, sem obrigatoriedade de login para visualizar o estoque de um treinador.

**Produção:** http://casakek.duckdns.org:5001

---

## Screenshots

<table>
  <tr>
    <td align="center"><b>Dashboard (desktop)</b></td>
    <td align="center"><b>Dashboard (mobile)</b></td>
  </tr>
  <tr>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/A1-home-sem-debug-1280.png" alt="Home desktop" /></td>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/M-home-390x844.png" alt="Home mobile" /></td>
  </tr>
  <tr>
    <td align="center"><b>Estoque público (desktop)</b></td>
    <td align="center"><b>Estoque público (mobile)</b></td>
  </tr>
  <tr>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/M-estoque-1280x800.png" alt="Estoque desktop" /></td>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/M-estoque-390x844.png" alt="Estoque mobile" /></td>
  </tr>
  <tr>
    <td align="center"><b>Catalogar por região</b></td>
    <td align="center"><b>Bottom navigation mobile</b></td>
  </tr>
  <tr>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/J36-regioes-1280.png" alt="Catalogar por região" /></td>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/I28-bottom-nav-375.png" alt="Bottom nav mobile" /></td>
  </tr>
  <tr>
    <td align="center"><b>Oportunidades de troca</b></td>
    <td align="center"><b>Progresso de captura</b></td>
  </tr>
  <tr>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/F21-aba-troca-1280.png" alt="Trocas" /></td>
    <td><img src="cypress/screenshots/audit_uxui.cy.js/B5-progresso-1280.png" alt="Progresso" /></td>
  </tr>
</table>

---

## Funcionalidades

### Pokédex
- **1025 espécies** cobertas (Gerações 1–9, Kanto a Paldea), sincronizadas via PokéAPI
- Busca em tempo real por nome (PT-BR ou EN) ou número da Pokédex
- Filtros por geração, tipo elemental (18 tipos) e status de captura (capturado/faltante)
- Paginação de 24 por página
- Página de detalhe com tipos, taxa de captura, cadeia evolutiva completa e status da coleção
- Badges visuais: ★ amarelo para Lendário, ✦ roxo para Mítico em todos os cards

### Coleção do treinador
- Marcar/desmarcar como capturado com quantidade
- Disponibilizar para troca (`for_trade`)
- Rastrear Shiny: flag `has_shiny` + quantidade de shinies
- Selo **100% IV** (`has_perfect`) — toggle manual ou automático (exemplar 15/15/15)
- Modal de detalhe (bottom sheet) ao tocar/clicar em qualquer card — sem sair da página
  - Incremento/decremento de quantidade
  - Toggle capturado, troca, shiny e 100%
  - **Fraquezas e resistências** como defensor e como atacante (multiplicadores do GO: 1,6× / 0,625× / 0,39×)
  - Cadeia evolutiva navegável dentro do modal
  - **Duplo clique** abre a carta expandida (tela cheia) com todos os exemplares e detalhes
- Exemplares individuais (`user_pokemon`): CP, HP, IVs, nível, golpes, sortudo, sombroso/purificado,
  favorito, peso/altura, rank PvP GL/UL/LC e a linha original completa (`raw`)
  - Cadastro manual rápido no modal (tudo opcional) para quem não tem PokeGenie Pro
- Importação em lote via CSV exportado pelo app **PokeGenie** (recurso do PokeGenie **Pro**) —
  reimportar substitui os exemplares importados antes; os manuais são preservados

### Catalogar por região
- Seleção individual ou em massa por região (Kanto, Johto… Paldea)
- Dois modos: "Marcar faltantes" (padrão) ou "Marcar como tenho"
- Barra de confirmação flutuante com contagem ao vivo
- Botões de Selecionar Todos / Limpar Seleção
- Busca por nome/número dentro da região
- Salva tudo em uma requisição POST única

### Estoque público compartilhável
- URL pública `/estoque/<username>` — sem login obrigatório
- Três abas: **Tenho** (capturados), **Faltantes** (lazy load com infinite scroll), **Troca** (disponíveis para negociar)
- Avatar + nome do treinador com código de treinador Pokémon GO
- Botão de compartilhamento via WhatsApp e cópia de link
- Badges lendário/mítico em todos os cards das três abas

### Sistema de trocas
- Engine de matching automático cruza a wishlist automática (tudo que falta) × estoque de outros treinadores
- Lista de oportunidades de troca com foto do Pokémon, nome do dono e código de treinador
- Clique em "Contato via WhatsApp" gera mensagem pré-preenchida e redireciona para wa.me
- Ciclo de vida do match: `active → contacted → completed / cancelled`
- Sincronia manual via `/trades/sync` para atualizar matches após mudanças na coleção

### Wishlist (lista de desejos)
- **Automática**: lista sozinha todas as espécies que faltam na coleção — nada a cadastrar
- ⭐ opcional para priorizar (grava em `wishlists`); prioridades e faltantes com oferta de troca aparecem primeiro
- Mostra quantos treinadores oferecem cada faltante para troca; filtros por nome, região, oferta e prioridade
- Usada pelo matching engine para encontrar treinadores que têm o que você quer

### Amigos
- Cadastro de amizade entre treinadores
- Visibilidade `friends` na coleção: somente amigos aceitos veem o estoque

### Perfil do treinador
- Upload de foto de perfil (JPEG/PNG/WebP, máx 2 MB)
  - Crop automático para quadrado central, redimensionado para 200×200, salvo como JPEG quality 85
  - Armazenado como LONGBLOB no banco (sem dependência de CDN)
- Código de treinador Pokémon GO (exibido nas propostas de troca)
- Visibilidade da coleção: Pública / Amigos / Privada
- Troca de senha com verificação da senha atual
- Link direto para o estoque público pessoal

### Painel admin
- Métricas globais: usuários, matches, eventos, espécies, formas, capturas
- Sincronização PokéAPI ao vivo com streaming SSE — barra de progresso em tempo real
- Lista de usuários com avatar, badge admin, visibilidade e data de cadastro
- Logs de eventos analytics (últimos 200)
- Visualização de coleção de qualquer usuário diretamente do painel (somente leitura)
- Dropdown no estoque de qualquer treinador para trocar de usuário visualizado (somente admin)

### UX / Interface
- Design **mobile-first** com Tailwind CSS
- Bottom navigation com 5 abas globais (Dashboard, Pokédex, Coleção, Trocas, Catálogo)
  — páginas com navegação própria sobrescrevem via `{% block bottom_nav %}`
- Botões de Login e Logout visíveis na navbar em dispositivos móveis
- Avatar do treinador logado na navbar (foto ou inicial do nome)
- Bottom sheet modal com animação `translateY` e gesto de swipe para fechar
- Scroll infinito (lazy load) na aba Faltantes do estoque público
- Eventos do Pokémon GO na dashboard (rodada de eventos futuros)
- Analytics internos com log de eventos por página/ação

---

## Stack

| Camada | Tecnologia |
|--------|-----------|
| Backend | Python 3.11 + Flask 3.1.3 |
| ORM | SQLAlchemy 2.x + Flask-Migrate |
| Auth | Flask-Login + Werkzeug |
| Banco | MySQL 8.0 (PyMySQL) |
| Frontend | Jinja2 + Tailwind CSS CDN |
| Imagens | Pillow (crop/resize avatar) |
| Deploy | Docker Compose + Gunicorn |
| Dados Pokémon | PokéAPI (sync automático com cache no banco) |
| Testes E2E | Cypress |

---

## Estrutura do projeto

```
MeuPokemonGO/
├── app/
│   ├── blueprints/
│   │   ├── admin/          # Painel administrativo (sync, logs, usuários)
│   │   ├── auth/           # Login, registro, logout, perfil, avatar
│   │   ├── collection/     # Coleção, catalogar por região, upsert
│   │   ├── friends/        # Amizades entre treinadores
│   │   ├── import_/        # Importação CSV PokeGenie
│   │   ├── main/           # Dashboard, estoque público
│   │   ├── pokedex/        # Pokédex, detalhe, API JSON
│   │   ├── trades/         # Matching engine, WhatsApp redirect
│   │   └── wishlist/       # Lista de desejos
│   ├── models/
│   │   ├── user.py         # User (avatar LONGBLOB, visibility, trainer_code)
│   │   ├── pokemon.py      # Species, Form, EvolutionChain
│   │   ├── collection.py   # UserCollection (owned, quantity, for_trade, shiny)
│   │   ├── trade.py        # TradeMatch, WhatsappClick
│   │   ├── friendship.py   # Friendship
│   │   ├── wishlist.py     # Wishlist
│   │   └── event.py        # AnalyticsEvent
│   ├── services/
│   │   ├── collection_service.py   # stats, missing, pending evolutions
│   │   ├── matching_service.py     # matching engine (wishlist × estoque)
│   │   ├── import_service.py       # parse PokeGenie CSV
│   │   ├── sync_service.py         # sincronização com PokéAPI
│   │   └── analytics_service.py    # log_event()
│   ├── providers/
│   │   ├── pokeapi.py      # cliente HTTP PokéAPI
│   │   └── cached.py       # cache de espécies/formas no banco
│   ├── templates/          # Jinja2 + Tailwind CSS
│   ├── config.py           # timezone Brasília (UTC-3), configurações
│   └── extensions.py       # db, login_manager, csrf, migrate
├── migrations/             # Flask-Migrate (Alembic)
├── cypress/                # Testes E2E (audit UX/UI)
├── docker-compose.yml      # Desenvolvimento local
├── docker-compose.prod.yml # Produção
├── Dockerfile
├── deploy.ps1              # Script de deploy PowerShell
└── requirements.txt
```

---

## Banco de dados — schema resumido

```
users
  id, username, email, password_hash
  trainer_code, is_admin
  avatar (LONGBLOB), avatar_mime
  visibility (public|friends|private)
  created_at, updated_at

species
  id (= número Pokédex), name (EN), name_pt (PT-BR)
  generation, is_legendary, is_mythical, capture_rate

forms
  id, species_id, form_name (normal|alolan|galarian|…)
  type1, type2, sprite_url, is_shiny_available

evolution_chains
  id, from_form_id, to_form_id, candy_cost

user_collections
  id, user_id, form_id
  owned, quantity, for_trade
  has_shiny, shiny_qty, notes

trade_matches
  id, wisher_id, owner_id, form_id
  status (active|contacted|completed|cancelled)
  created_at

whatsapp_clicks
  id, match_id, clicker_id, clicked_at

friendships
  id, requester_id, addressee_id
  status (pending|accepted|declined)

wishlists
  id, user_id, form_id, created_at

analytics_events
  id, user_id (nullable), event_type, data (JSON), created_at
```

---

## API endpoints

| Método | Rota | Auth | Descrição |
|--------|------|------|-----------|
| `GET` | `/pokedex/api/<id>` | opcional | Detalhe JSON de uma espécie (form, collection, evolutions) |
| `POST` | `/collection/upsert` | obrigatório | Atualizar owned/qty/for_trade/shiny de uma forma |
| `POST` | `/collection/regiao` | obrigatório | Salvar coleção em massa por região |
| `GET` | `/auth/avatar/<user_id>` | público | Foto de perfil (JPEG, cache 24h) |
| `GET` | `/admin/sync/run` | admin | SSE: streaming de sincronização com PokéAPI |
| `POST` | `/api/log` | público | Registrar evento de analytics (CSRF exempt) |

---

## Rotas principais

| Rota | Acesso | Descrição |
|------|--------|-----------|
| `/` | público | Dashboard com stats, faltantes, trocas e eventos GO |
| `/pokedex/` | público | Pokédex completa com filtros |
| `/pokedex/<id>` | público | Detalhe de uma espécie |
| `/collection/` | login | Coleção pessoal com filtros |
| `/collection/catalogar` | login | Catalogar em massa por região |
| `/trades/` | login | Oportunidades de troca |
| `/trades/sync` | login | Atualizar matches |
| `/trades/whatsapp/<id>` | login | Redirecionar para WhatsApp com mensagem |
| `/wishlist/` | login | Lista de desejos |
| `/friends/` | login | Amigos |
| `/import/` | login | Importar CSV PokeGenie |
| `/auth/perfil` | login | Editar perfil, senha e foto |
| `/estoque/<username>` | público | Estoque público de qualquer treinador |
| `/admin/` | admin | Painel administrativo |
| `/admin/sync` | admin | Sincronizar Pokédex com PokéAPI |
| `/admin/usuarios` | admin | Lista de usuários |
| `/admin/logs` | admin | Logs de eventos |

---

## Variáveis de ambiente

Copie `.env.example` para `.env`:

```env
SECRET_KEY=troque-por-chave-aleatoria-longa
DB_HOST=db
DB_PORT=3306
DB_NAME=meupokemongo
DB_USER=root
DB_PASSWORD=senha-aqui
FLASK_ENV=production

# Opcionais — notificações Telegram
TELEGRAM_BOT_TOKEN=
TELEGRAM_ADMIN_CHAT_ID=
```

---

## Desenvolvimento local

```bash
# 1. Subir banco + app
docker compose up -d

# 2. Aplicar migrations (primeira vez)
docker exec meupokemongo-web-1 flask db upgrade

# 3. Sincronizar Pokédex com PokéAPI (~15 min, 1025 espécies)
docker exec meupokemongo-web-1 flask sync-pokedex

# 4. Acessar
# http://localhost:5000
```

Para rodar sem Docker:

```bash
python -m venv .venv && .venv\Scripts\activate   # Windows
pip install -r requirements.txt
flask db upgrade
flask run
```

---

## Testes E2E (Cypress)

```bash
# Instalar dependências
npm install

# Rodar suite de auditoria UX/UI (modo headless)
npx cypress run --spec cypress/e2e/audit_uxui.cy.js

# Modo interativo
npx cypress open
```

Screenshots são gerados automaticamente em `cypress/screenshots/`.

---

## Deploy em produção

```powershell
# Apenas código (sem rebuild da imagem Docker)
.\deploy.ps1

# Com rebuild completo
.\deploy.ps1 -Build
```

O script executa: `git push` → SSH no servidor → `git pull` → rebuild Docker (se `-Build`) → restart do container.

**Servidor:** `casakek.duckdns.org:64622`  
**Pasta:** `/home/felipe/sistemas/MEUPOKEMONGO`  
**Container:** `meupokemongo_web_1` (porta `5001`)

Rebuild manual direto no servidor:
```bash
docker build -t meupokemongo_web .
docker rm -f meupokemongo_web_1
docker run -d --name meupokemongo_web_1 \
  --network meupokemongo_default \
  --restart unless-stopped \
  -p 5001:5000 \
  --env-file .env \
  -e DB_HOST=meupokemongo_db_1 \
  -e DB_PORT=3306 \
  meupokemongo_web
```

Acesso ao banco em produção:
```bash
docker exec meupokemongo_db_1 mysql -u root -ppokemon123prod meupokemongo
```

---

## Importar coleção via PokeGenie

1. Instale **PokeGenie** no celular (iOS/Android)
2. Escaneie seus Pokémon ou use a exportação automática do app
3. Exporte o CSV pelo PokeGenie
4. Acesse `/import/` e faça o upload do arquivo
5. O sistema faz o parse, resolve o Pokémon pelo nome e marca como capturado

---

## Progresso da Pokédex (28/09/2026)

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
| **Total** | **698** | **1025** | **68%** |

---

## Licença

Projeto pessoal / portfólio — dados de Pokémon GO pertencem à Niantic / The Pokémon Company.
