# Pesquisa de Referências — GitHub + PokeAPI

> Exploração realizada em 07/10/2026. Objetivo: mapear projetos relevantes para inspirar e guiar o desenvolvimento do MeuPokémonGO.
> Conclusão: nenhum projeto encontrado justifica integração ou migração — o MeuPokémonGO já supera todos em escopo GO-específico.

---

## PokeAPI — Endpoints explorados ao vivo

A API raiz `https://pokeapi.co/api/v2/` expõe 60+ endpoints. Os mais relevantes para o projeto:

| Endpoint | Dados retornados | Status no projeto |
|---|---|---|
| `GET /pokemon/{id\|name}` | id, name, types, stats, abilities, sprites, height, weight | ✅ Sincronizado |
| `GET /pokemon-species/{id}` | is_legendary, is_mythical, capture_rate, flavor_text, evolves_from, egg_groups, gender_rate | ✅ Parcialmente (falta flavor_text) |
| `GET /evolution-chain/{id}` | Cadeia completa com triggers (level-up, use-item) e requisitos | ✅ Salvo em evolution_chains |
| `GET /type/{name}` | damage_relations: double/half/no damage to/from | ⚠️ Calculado local em types.py (ver #26-D) |
| `GET /move/{id}` | power, accuracy, pp, damage_class, type, effect_entries | 📋 Planejado (#26-B) |
| `GET /ability/{id}` | effect, short_effect, pokemon que possuem | Não usado |
| `GET /nature/{id}` | stat aumentado/reduzido, sabor preferido/odiado | Não relevante para GO |
| `GET /egg-group/{id}` | Pokémon do grupo | 📋 Planejado (#26-C) |
| `GET /pokemon/{id}/encounters` | Localização por versão/jogo | 📋 Planejado (#26-C) |
| `GET /pokeathlon-stat` | Stats de Pokéathlon (mini-games DS) | Não relevante |
| `GET /berry` | Frutas e efeitos | Não relevante para GO |

### Dados testados ao vivo

**Pikachu (id=25):**
- Tipos: Electric | Habilidades: Static, Lightning Rod (hidden)
- Capture rate: 190 | Base happiness: 70
- Evolui de: Pichu (nível + felicidade ≥ 220) → Raichu (Thunder Stone)
- Egg groups: ground, fairy | Gender rate: 4

**Bulbasaur (id=1):**
- Stats: HP 45 / Atk 49 / Def 49 / SpAtk 65 / SpDef 65 / Spd 45
- Sprite: `https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/1.png`

**Tipo Elétrico:**
- Super eficaz contra: Flying, Water
- Pouco eficaz contra: Grass, Electric, Dragon
- Sem efeito contra: Ground
- Fraco contra: Ground | Resistente a: Flying, Steel, Electric

---

## Repositório oficial — PokeAPI/sprites

**URL:** `https://github.com/PokeAPI/sprites` (1.7k ⭐)

Repositório com todos os sprites da PokeAPI. Acessível via raw GitHub como CDN:
```
https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/{id}.png
https://raw.githubusercontent.com/PokeAPI/sprites/master/sprites/pokemon/shiny/{id}.png
```
O projeto já usa essas URLs via `sync_service.py`. Referência para formas especiais.

---

## HybridShivam/Pokemon

**URL:** `https://github.com/HybridShivam/Pokemon` (390 ⭐, Python)

Repositório de assets de maior qualidade — arte oficial Sugimori, Gen 1–9, Mega, Gigantamax, formas regionais, Hero/Terastal. Nomeação: `{id}-{FormName}.png`.

**Pipeline de scraping:**
- `ImageScrapper.py` — extrai URLs do Bulbapedia
- `Downloader.py` — baixa e salva localmente
- `generateDataSet.py` — gera CSV/JSON estruturado

**Possível uso:** fallback de sprite de alta qualidade quando a PokeAPI não tem arte oficial para uma forma específica. Raw GitHub serve como CDN gratuito.

**Decisão:** não integrar agora. WebP 160px gerado localmente já cobre o caso de uso.

---

## graphql-pokeapi (mazipan)

**URL:** `https://github.com/mazipan/graphql-pokeapi` (189 ⭐, JavaScript)
**Playground:** `https://graphql-pokeapi.vercel.app/api/graphql`
**GraphCDN (com cache):** `https://graphql-pokeapi.graphcdn.app`

Wrapper GraphQL não-oficial sobre a PokeAPI REST. Stack: Apollo Server + Vercel.

**Queries disponíveis:** `pokemons`, `pokemon`, `abilities`, `ability`, `berries`, `berry`, `moves`, `move`, `types`, `regions`, `region`, `evolutionChains`, `evolutionChain`, `species`, `natures`, `nature`.

**Exemplo:**
```graphql
query pokemon($name: String!) {
  pokemon(name: $name) {
    id
    name
    abilities { ability { name } }
    types { type { name } }
  }
}
```

**Vantagem:** buscar só os campos necessários em uma query, sem over-fetch da REST.
**Decisão:** interessante para exploração, mas o `providers/pokeapi.py` já faz cache no banco — não compensa trocar.

---

## pogo-wave-radar (Kengkorok)

**URL:** `https://github.com/Kengkorok/pogo-wave-radar` (2 ⭐, Python/PWA)
**Demo:** `kengkorok.github.io/pogo-wave-radar`

Rastreador de eventos Pokémon GO que visualiza quando eventos locais (Community Day, Raid Day, Spotlight Hour) estão ativos em 22 cidades ao redor do mundo, seguindo a progressão de leste a oeste como uma "onda".

**Como funciona:**
- Scrapa `leekduck.com/events` a cada 30 min via GitHub Actions
- Gera `docs/cities.json` com horários por cidade e UTC offset
- Frontend PWA instalável (Android), atualiza automaticamente
- `scripts/sort_cities.py` reordena cidades por UTC offset

**Features:** Live Now, Wave Tracker, All Events, City Safari, Moonlight (evento específico com contagem regressiva). Dados bilíngues (EN + Malaio).

**Relevância para o MeuPokémonGO:** o dashboard já tem cards de eventos. Substituir os eventos hardcoded por um JSON scrapeado do LeekDuck via GitHub Actions seria o mesmo padrão.
**Decisão:** catalogado para referência futura. Não implementar agora.

---

## pokemon-team-analyzer (rxmarks)

**URL:** `https://github.com/rxmarks/pokemon-team-analyzer` (0 ⭐, Python/Streamlit)

Streamlit app que analisa fraquezas de tipo de um time Pokémon e ranqueia substituições que melhorariam a cobertura.

**Análises implementadas:**
1. Tabela defensiva por tipo de ataque
2. Lacunas ofensivas (tipos não cobertos super-efetivamente)
3. Sugestões de swap ranqueadas por redução de fraquezas
4. Cobertura de movimentos (até 4 ataques reais)
5. Análise stat-base (desequilíbrios físico/especial, velocidade)
6. Meta threats (vs. 30 Pokémon mais usados — dados Smogon)

**Stack:** Streamlit, package `pokedex` (lógica isolada e testável), pytest com 98% cobertura, GitHub Actions CI/CD.

**Relevância:** a matemática de multiplicadores de tipo está isolada e testável — referência para substituir o `app/data/types.py` hardcoded (item #26-D do backlog).
**Decisão:** catalogado. Não incorporar código diretamente.

---

## pokeldn (Decryptu)

**URL:** `https://github.com/Decryptu/pokeldn` (80 ⭐, Python/C++)

ESP32 que implementa o protocolo LDN/Pia da Nintendo via 2.4 GHz, permitindo se comunicar com jogos Pokémon no Switch como se fosse outro console.

**Casos de uso:** trocas automatizadas sem segundo console, Mystery Gift via rede local, backup de save, pesquisa de protocolo.

**Stack:** ESP-IDF v6.1 (C/C++), Python 3.11+, PKHeX.Core (.NET), GTK/Flutter para desktop.

**Suporte por geração:** FRLG, LGPE, SwSh, BDSP, PLA, SV, PLZA.

**Interessante porque:** engenharia reversa completa de protocolo não documentado. IA assistiu no processo. Licença AGPL-3.0, não-comercial.
**Relevância para GO:** zero (GO é mobile/servidor Niantic). Catalogado por curiosidade técnica.

---

## Outros projetos mapeados

| Projeto | Descrição | Por que não relevante |
|---|---|---|
| [poke95](https://github.com/wobsoriano/poke95) | Pokédex estilo Windows 95 em React (161⭐) | Frontend React, sem backend, só consulta |
| [pokedex-angular-app](https://github.com/HybridShivam/Pokemon) | PWA offline Angular (390⭐) | Angular, sem equivalente a collection/trades |
| [Heinkek-99/pokemon](https://github.com/Heinkek-99/pokemon) | Flask API + Streamlit + matplotlib | Apenas consulta, sem coleção/usuários |
| [JorgeMassaru/pokedex_python](https://github.com/JorgeMassaru/pokedex_python) | MVC Flask + SQLAlchemy + CRUD | CRUD básico, muito abaixo do escopo atual |
| [Holfkings/poke-explorer](https://github.com/Holfkings/poke-explorer) | Flask + SQLite, ~130 linhas | Demo de padrão API→cache, sem features |
| [PokeDex-Project](https://github.com/Sumdiboii/PokeDex-Project) | React + TensorFlow CNN 96% | IA para detecção por foto, fora do escopo GO |
| agent-oak | Agente que joga Pokémon Red | Curiosidade, sem relação com GO |
| pixel-flippers | MCP server p/ Claude + emulador | Curiosidade técnica |
| pokemon-champions-agents | Times via LangGraph | Pokémon Champions ≠ GO |
| poketext | CLI de captura em Go | CLI, sem web |

---

## Conclusão

O MeuPokémonGO já supera todos os projetos open-source encontrados em termos de escopo GO-específico (trocas, matching, estoque público, formas regionais, import PokeGenie). Os projetos catalogados servem como referência pontual para features específicas, não como base para reescrita ou integração.

Próximos passos documentados no `docs/BACKLOG.md` — item `#26 — Expansões PokeAPI`.
