# Backlog — MeuPokémonGO

> **Premissa do produto:** o app existe para **encontrar treinadores para trocar**.
> Tudo que fecha o ciclo *"falta X → alguém tem X → combino a troca"* vem antes do resto.
>
> **Princípio de UX:** mínimo input. Se o usuário precisa cadastrar muita coisa, ele não usa —
> o padrão é automático (ex.: a wishlist já é tudo que falta).

*Última revisão: 02/10/2026*

---

## Índice

1. [Decisões de produto](#decisões-de-produto)
2. [Fila priorizada](#fila-priorizada)
3. [Agora — fechar o ciclo de troca](#agora--fechar-o-ciclo-de-troca)
4. [Logo depois](#logo-depois)
5. [Médio prazo](#médio-prazo)
6. [Parado / em avaliação](#parado--em-avaliação)
7. [Dívida técnica e segurança](#dívida-técnica-e-segurança)
8. [Entregue](#entregue)

---

## Decisões de produto

Tomadas em 02/10/2026 — valem para as features abaixo.

| # | Decisão | Motivo |
|---|---------|--------|
| D1 | **Todos os treinadores se enxergam.** Não é preciso ser amigo no app. A privacidade vira um único toggle: **"Aparecer para outros treinadores nas trocas"** (sim/não) | Exigir amizade antes de ver alguém mata a descoberta, que é o valor do app |
| D2 | **Amigos sai do menu agora** (código e tabela ficam); remoção definitiva depois | Reversível; usuários com visibilidade `friends` migram para público |
| D3 | **Troca à distância** com rótulo neutro **"Topo trocar à distância"** — nunca "fly" explícito | No GO a troca exige proximidade física; o campo entra no matching sem associar o app a GPS falso (contra os termos da Niantic) |
| D4 | **Localização: só Brasil por enquanto** — estado + cidade com autocompletar da lista do IBGE | Comunidade de Fortaleza primeiro; lista fechada = sem digitação livre nem erro de grafia |
| D5 | **Contato com consentimento explícito.** Código de amigo é sempre visível para quem aparece nas trocas; **WhatsApp é opcional** ("Permitir que treinadores me chamem no WhatsApp") | Telefone é dado pessoal (LGPD); o código de amigo já é o contato dentro do jogo |
| D6 | **Login com Google (#25) entra depois do Trade Binder (#18)**, não junto com o perfil | Depende de credenciais OAuth no Google Cloud; não bloqueia o ciclo de troca |

---

## Fila priorizada

| Ordem | # | Item | Esforço | Status |
|-------|---|------|---------|--------|
| 1 | [#23](#23--perfil-de-troca--visibilidade-aberta) | Perfil de troca + visibilidade aberta | ~1 dia | ✅ Entregue |
| 2 | [#24](#24--matching-por-cidade--troca-recíproca) | Matching por cidade + troca recíproca | ~1 dia | ✅ Entregue |
| 3 | [#18](#18--trade-binder-público) | Trade Binder público `/trade/<usuario>` | ~3 h | ✅ Entregue |
| 4 | [#25](#25--login-com-google) | Login com Google | ~½ dia | ⏳ Aguardando credenciais OAuth |
| 5 | [#20](#20--faltantes-sob-demanda) | Faltantes sob demanda (desempenho) | ~3 h | ✅ Entregue |
| 6 | [#15](#15--progresso-shiny-e-100-versão-enxuta) | Progresso Shiny e 100% (versão enxuta) | ~3 h | ✅ Entregue |
| 7 | [#14](#14--formas-regionais--exclusivos-de-região) | Formas regionais + exclusivos de região | ~1–2 dias | ✅ Entregue |
| 8 | [#13](#13--binder-view-33) | Binder 3×3 + imagem compartilhável | ~1 dia | Pendente |
| — | #16, #19, #21 | Gênero, valor da coleção, numeração dupla | — | Parado |
| — | #17 | Scan em lote (OCR) | 1–2 sem | Parado |
| — | #22 | Discord + comunidade | — | Em avaliação |

---

## Agora — fechar o ciclo de troca

### #23 — Perfil de troca + visibilidade aberta

> ✅ **Entregue em 02/10/2026.** Como ficou:
> - "Aparecer nas trocas" reaproveita a coluna `visibility` (public = sim, private = não) — sem segunda fonte de verdade;
>   `friends` migrado para `public` na migração `f5a6b7c8d9e0`
> - Cadastro sem o campo de código; código + UF/cidade + contato vão para `/auth/onboarding` (aviso no topo até completar)
> - Código de amigo validado (12 dígitos) e salvo como `1234 5678 9012`; cidade validada contra
>   `app/static/data/municipios_br.json` (IBGE, 5.571 municípios, tolera caixa/acento)
> - Contato unificado no macro `templates/_contact.html` (WhatsApp só com consentimento + copiar código)
> - Correção extra: `/estoque/<usuario>` nunca checava visibilidade — perfil privado agora dá 404 para terceiros

**Por quê:** hoje o botão **"Propor troca" abre o WhatsApp sem número de destino** — a troca morre ali.
Sem dados de contato e localização não existe ciclo de troca.

**Escopo:**
- Novos campos em `users`: `state` (UF), `city` (IBGE), `can_trade_remote` (bool),
  `whatsapp` (opcional), `allow_whatsapp` (bool), `show_in_trades` (bool, padrão sim)
- `trainer_code` já existe — passa a ser pedido no onboarding
- Onboarding curto após o cadastro (3 passos): código de amigo → estado/cidade → contato
- `visibility` → substituído por `show_in_trades` (D1); `friends` migra para público (D2)
- Menu: remover "Amigos" (D2)
- Perfil: opção **Apagar minha conta** (LGPD)
- "Propor troca": WhatsApp com número só se `allow_whatsapp`; senão mostra/copia o código de amigo

**Arquivos:** `models/user.py`, migração, `auth/routes.py` + `templates/auth/` (registro, perfil, onboarding),
`base.html` (menu), `services/matching_service.py` (`_interaction_allowed`), `trades/`

### #24 — Matching por cidade + troca recíproca

> ✅ **Entregue em 02/10/2026.** Regra em `matching_service.proximity_tier`: 📍 mesma cidade → 🌐 um dos dois troca à distância →
> ❔ cidade não informada (por último, para a lista não ficar vazia no início); cidades diferentes sem distância ficam de fora.
> "Trocas de mão dupla" no topo de /trades (`get_reciprocal_trades`), ordenadas por proximidade e nº de trocas possíveis.
> A contagem "p/ troca" da Wishlist usa a mesma regra em SQL (`_reachable_owner_filter`).

**Por quê:** é o valor central. Troca no GO exige proximidade, então quem está perto vale mais.

**Escopo:**
- Ordenação das ofertas: mesma cidade → mesmo estado → "troca à distância" → resto
- **Troca recíproca:** lista de treinadores com score
  *"Misty tem 3 que você quer · você tem 2 que ela quer"* — vira convite de troca de mão dupla
- Wishlist/Trocas mostram a distância lógica (📍 mesma cidade / 🗺️ mesmo estado / 🌐 à distância)
- Só entram treinadores com `show_in_trades = true`

### #18 — Trade Binder público

> ✅ **Entregue em 02/10/2026** em `/trade/<usuario>` (sem login, com OG tags): tenho para troca (×qtd, ⭐, 100), ⭐ prioridades em "Procuro",
> e para o visitante logado "Você tem N que fulano procura". Dono vê "Divulgar no WhatsApp"; link no perfil.
> ➕ "Procuro" agora lista **todos** os faltantes na ordem da Wishlist (`build_wishlist`), sob demanda, com filtros
> 🤝 Você tem / 🌍 / 🔥 / 🧬 e busca. **Pokémon favorito** (perfil/onboarding) aparece como adesivo animado
> (GIF Showdown da PokeAPI; sem GIF → arte oficial).

**Inspirado em:** Rare Candy (viralizou no TikTok em 2026)

Cerca de 70% já existe: aba **"Para troca"** do estoque público `/estoque/<usuario>`.

**Escopo:**
- Rota dedicada `/trade/<usuario>` (sem login) só com `for_trade = True`
- Selos ⭐ shiny / 💯 100% e o que o dono **procura** (faltantes dele) — vira vitrine de mão dupla
- "Propor troca" respeitando o consentimento do #23
- Botão "Copiar link" para WhatsApp / Discord / TikTok
- Valor em poeira estelar fica para o #19 (não bloqueia)

---

## Logo depois

### #25 — Login com Google

- OAuth Google (Authlib); callback `https://meupokemongo.duckdns.org/auth/google/callback`
- Conta nova via Google cai direto no onboarding do #23
- Vincular Google a conta existente pelo e-mail
- **Pré-requisito (usuário):** criar OAuth Client no Google Cloud → `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET`

### #20 — Faltantes sob demanda

> ✅ **Entregue em 02/10/2026.** Faltantes vão como JSON compacto (`MISSING`) e o JS desenha 30 por vez; a busca filtra o JSON.
> `/estoque/<usuario>#faltantes` abre direto a aba.
> ✅ **#20b entregue:** aba Tenho também sob demanda (JSON `OWNED` + toggles do dono sincronizados). Antes: com coleção grande o peso migrou para a aba **Tenho** — em produção `/estoque/felipe`
> (698 possuídos) ainda tem ~816 KB. Aplicar o mesmo render sob demanda na aba Tenho (cards têm botões ⭐/🔄 do dono).

**Status: parcial.** O estoque público já tem abas Tenho / Faltantes / Troca com scroll infinito (30 por vez),
mas os ~770 cards de faltantes vêm **todos no HTML** (ocultos) — peso no celular.

**Escopo:** endpoint JSON paginado e renderizar os cards de faltantes só quando a aba abre / ao rolar.

### #15 — Progresso Shiny e 100% (versão enxuta)

> ✅ **Entregue em 02/10/2026.** Cards ⭐ Shiny / 💯 100% / ✨ Shundo na coleção (clicáveis = filtro) + abas ⭐ e 💯.

Os dados já existem (`has_shiny`, `has_perfect`, `user_pokemon`). Em vez de "subcoleções" com tabela nova:
- Contadores no painel e na coleção: **Shiny 12/1025 · 100% 3/1025 · Shundo 1**
- Filtros "só shiny" / "só 100%" na coleção
- Sombroso entra quando houver dado suficiente (vem do import PokeGenie)

---

## Médio prazo

### #14 — Formas regionais + exclusivos de região

> ✅ **Entregue em 02/10/2026.** 57 formas regionais via `flask sync-forms` (também roda no fim do `sync-pokemon`);
> ignorados totem/boné/Darmanitan Zen e Mega/G-Max. Lista curada de exclusivos em `app/data/regional.py`
> (aproximada; fora os pares que alternam de região). Wishlist: toggle "Formas regionais" (`?formas=1`), card 🌍,
> exclusivos no topo da Alta e filtro "Só por troca". Modal: aviso de exclusivo + "Formas regionais" com "+ Tenho".
> Matching/mão dupla incluem formas regionais. % da Pokédex conta só formas normais.
> Fora do escopo: catalogar por região e estoque público ainda mostram só formas normais.
> ➕ **Ampliado em 02/10/2026:** além das regionais, Mega (97), Gigantamax (34) e Especiais (22: bonés do Pikachu,
> todos os Totem, Darmanitan Zen) — 210 formas. Wishlist com 4 categorias liga/desliga (`?formas=regional,mega,gmax,especial`).
> **Mega fica fora de trocas** (evolução temporária no GO; servidor recusa `for_trade`). Totem não existe no GO (aviso na categoria).

**Por que importa para a premissa:** exclusivos de região (Farfetch'd, Heracross, Corsola, Tauros…)
**só se conseguem por troca** — é o caso de uso mais forte do app.

**Escopo:**
- Sync: importar variedades da PokeAPI (`/pokemon-species/{id}` → `varieties`) como `Form`
- Toggle "Incluir formas: [ ] Alola [ ] Galar [ ] Hisui [ ] Paldea [ ] Mega" na coleção/wishlist
- Selo **"Exclusivo de região"** + prioridade de troca na wishlist
- Wishlist, catalogar e estoque passam a considerar formas além da `normal`

### #13 — Binder View 3×3

**Inspirado em:** Godex (feature de maior retenção)

- Páginas de 9 cards (3×3, opcional 3×4) com Anterior/Próximo — "Página 3 de 17 — #19–27"
- **Salvar como imagem** 1080×1080 (Pillow) para Instagram / Discord
- Benefício colateral: renderiza só 9 por vez

Valor de divulgação, não ajuda a trocar diretamente — por isso depois do ciclo de troca.

---

## Parado / em avaliação

| # | Item | Por que parado |
|---|------|----------------|
| #16 | **Rastreamento por gênero** (Nidoran ♂/♀, Pikachu coração) — toggle por espécie, ~4 h | Nicho ("living dex perfeito"); não ajuda a trocar |
| #19 | **Valor da coleção** em poeira estelar/doces (Collectr) | Falta dado de custo de PL por espécie; `candy_cost` já existe |
| #21 | **Numeração dupla** "#025 Pikachu / #034 da sua coleção Kanto", ~3 h | Baixo impacto |
| #17 | **Scan em lote** (Mint): câmera + Tesseract.js, 9 cards por foto | Caro (1–2 semanas); import PokeGenie + cadastro rápido de exemplar cobrem o básico |

### #22 — Discord + comunidade de trocas (em avaliação)

Inspirado em Pogo Profiles (2016) + Godex (2026). **Não implementar antes de validar.**
Com #23/#24 o próprio app vira a vitrine onde todos se enxergam — testar Discord só depois de ver trocas acontecendo pelo app.

**Ideia:** servidor "MeuPokémonGO"; bot posta matches (score > 70%) em `#matches-automaticos`;
login Discord OAuth2 (`discord_id` no `User`); `/colecao @user`; `#binder-showoff` com a imagem do #13.

<details>
<summary>Estrutura de canais, tabelas e env vars planejadas</summary>

```
📢 INÍCIO      #boas-vindas · #como-usar-app
🔍 COLEÇÃO     #faltantes-geral · #binder-showoff · #shiny-hundo
🤝 TROCAS      #procuro · #tenho-para-troca · #matches-automaticos · #trocas-realizadas
📅 EVENTOS     #reides-hoje · #eventos-go
💬 GERAL       #chat-geral
```

```sql
discord_users    (user_id, discord_id, discord_username, guild_id, joined_at)
discord_webhooks (guild_id, channel_id, type ENUM('matches','raids','events'))
```

```env
DISCORD_CLIENT_ID=
DISCORD_CLIENT_SECRET=
DISCORD_WEBHOOK_MATCHES_URL=
```

Arquivos: `app/blueprints/discord/routes.py`, `bot/bot.py` (discord.py), `docs/DISCORD.md`
</details>

**4 perguntas para validar antes de codar:**
1. Onde o jogador procura troca hoje? (WhatsApp? Campfire?) — Discord precisa ser 10× mais fácil
2. Qual a dor real? Achar quem tem / combinar horário / saber se vale a poeira?
3. Menor teste sem código: 2 amigos postando manualmente por 1 semana — se 3 trocas rolarem, validou
4. A comunidade de Fortaleza é ativa o suficiente para sustentar um servidor próprio?

---

## Dívida técnica e segurança

| Item | Ação |
|------|------|
| **Senhas no histórico do git** — senha pessoal (antigo `cypress.config.js`) e senha root do MySQL de produção (antigo README) | Já removidas dos arquivos; **trocar as duas senhas** (continuam no histórico do GitHub) |
| **Cypress 16 não roda na máquina de dev** (Electron 41 → "Illegal instruction") | Fluxos validados com Playwright avulso; migrar a suíte E2E para Playwright quando incomodar |
| `cypress/e2e/audit_uxui.cy.js` (auditoria antiga) | Depende de dados reais antigos; adaptar ao seed de `scripts/e2e_server.py` ou aposentar |
| docker-compose 1.29.2 no servidor (bug `ContainerConfig` no recreate) | `deploy.ps1` já contorna (remove e cria do zero); considerar migrar para `docker compose` v2 |
| Import PokeGenie validado só com o layout padrão de colunas | Testar com um CSV real de PokeGenie Pro quando houver |

---

## Entregue

| Data | Entrega | Commit |
|------|---------|--------|
| 02/10/2026 | Wishlist automática (tudo que falta) + prioridade 🔥 Alta / 🧬 Evoluir + ⭐ manual | `8524fc6` |
| 02/10/2026 | Selo 100% IV (`has_perfect`), exemplares individuais (`user_pokemon`), import PokeGenie completo | `8524fc6` |
| 02/10/2026 | Duplo clique = carta expandida; fraquezas e resistências (defensor e atacante, multiplicadores do GO) | `8524fc6` |
| 02/10/2026 | Rate limit sem bloquear uso normal + ProxyFix; `deploy.ps1` com build, migração e health check | `68ffc01`, `542dbac` |
| 02/10/2026 | Doces para evoluir (pogoapi), "Vitórias rápidas" no painel, matching automático, cabeçalho mobile | `918bf93` |
| 02/10/2026 | Ambiente E2E isolado (`scripts/e2e_server.py` + Pokédex real em fixture) | `918bf93` |
| 02/10/2026 | **#23** Perfil de troca (código, cidade IBGE, troca à distância, WhatsApp com consentimento), todos se enxergam, onboarding, apagar conta | `60e85a1` |
| 02/10/2026 | **#24** proximidade + trocas de mão dupla · **#18** Trade Binder · **#15** progresso Shiny/100% · **#20** faltantes sob demanda | `fac64ef` |
| 02/10/2026 | **#20b** aba Tenho sob demanda · **#14** formas regionais + exclusivos de região | `d6a62ab` |
| 02/10/2026 | Formas Mega/Gigantamax/Especiais · Trade Binder "Procuro" com todos os faltantes priorizados · Pokémon favorito como adesivo animado | `c4d3f2a` |
| 02/10/2026 | Imagens: sprite 96 px nas grades (~100× mais leve), GIF animado em destaques (modal com GIF shiny, "você tem", adesivo), "reduzir movimento" respeitado · Engrenagem = Admin (só administradores) + "ver como" no Trade Binder · Pressionar e segurar abre a carta expandida | `dd46117` |
| 03/10/2026 | Página **Treinadores** (`/treinadores`, card do painel e menu) · revisão **PT-BR** (tipos via `app/data/i18n.py`, Brilhante, PC/PS, Lista de Desejos, Vitrine de Trocas, Início) | `f583610` |
| 03/10/2026 | Miniaturas HD nos cards (WebP 160 px gerado da arte oficial, `/img/t/<id>.webp`, cache em disco + 1 ano no navegador) · GIF com suavização e ampliação limitada · menu: Perfil sai (foto), Catalogar entra · card do treinador com a cor do tipo do favorito + aviso para escolher favorito | `a97c7bb` `298100c` |
| 03/10/2026 | **Início redesenhado**: logado = Painel (cor do favorito, anel de progresso, Brilhante/100%, barras por região) → Central de Trocas (mão dupla, "o que fazer agora", treinadores perto) → Feed (quem tem o que você procura, treinadores novos, eventos); sem login = página de apresentação com vitrine de treinadores · decimais com vírgula | ver `git log` |
