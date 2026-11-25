# Spec: Jornada — jogo de tabuleiro multijogador (#27)

*Revisão: 25/11/2026 — rascunho para revisão do Felipe. Nenhum código escrito ainda.*

> **Nome do jogo:** codinome **"Trilha dos Domadores"** (renomeável — o nome mora num arquivo de dados).
> **Módulo:** blueprint `jornada`, rota `/jornada/`, dentro do MeuPokémonGO.

---

## Índice

1. [Contexto e objetivo](#1-contexto-e-objetivo)
2. [Decisão de conteúdo (propriedade intelectual)](#2-decisão-de-conteúdo-propriedade-intelectual)
3. [Escopo](#3-escopo)
4. [O loop do jogo](#4-o-loop-do-jogo)
5. [Regras exatas](#5-regras-exatas)
6. [Tabuleiro da Fase 1 — Vale Aurora (73 casas)](#6-tabuleiro-da-fase-1--vale-aurora-73-casas)
7. [Criaturas da Fase 1](#7-criaturas-da-fase-1)
8. [Itens e baralho de eventos](#8-itens-e-baralho-de-eventos)
9. [Balanceamento (simulação)](#9-balanceamento-simulação)
10. [Modelo de dados](#10-modelo-de-dados)
11. [Rotas e API](#11-rotas-e-api)
12. [Telas](#12-telas)
13. [Tempo real e desempenho](#13-tempo-real-e-desempenho)
14. [Anti-trapaça](#14-anti-trapaça)
15. [Conteúdo como dados](#15-conteúdo-como-dados)
16. [Fases de entrega](#16-fases-de-entrega)
17. [Decisões em aberto](#17-decisões-em-aberto)

---

## 1. Contexto e objetivo

Jogo de tabuleiro digital, assíncrono e multijogador, dentro do app. O jogador rola o dado,
anda pela trilha, captura criaturas, ganha Pontos de Poder (PP) e sobe de região. O diferencial
social é o **Mapa Global**: todo mundo vê onde cada treinador parou — uns perto do topo, outros
ainda no começo.

**Por que dentro do MeuPokémonGO:** reaproveita login, perfil, avatar, cidade (IBGE) e a base de
usuários. Dá ao app um motivo para **voltar todo dia** além das trocas.

**Loop que vicia:** rolar → andar → capturar/evento → ganhar PP → subir no ranking →
desbloquear a próxima cidade → ver os amigos para trás.

---

## 2. Decisão de conteúdo (propriedade intelectual)

Decidido em 25/11/2026: **todo o conteúdo do jogo é original**.

- **Não usar:** nomes, imagens ou sprites de Pokémon, regiões e cidades oficiais (Kanto, Pallet,
  Cerulean…), líderes de ginásio (Brock, Misty…), Elite Four, nomes de itens da marca
  ("Poké Bola", "Potion", "Revive", "Master Ball"), o nome "Master Trainer" (é um jogo de
  tabuleiro existente) e a pokébola no logo/ícones.
- **Usar:** criaturas, região, cidades, líderes, itens e nome próprios — definidos nesta spec.
- A **mecânica** (dado, casas, 2 números de captura, PvP, ranking por fase) é genérica de jogo de
  tabuleiro e fica como o documento original pediu.
- Os sprites da PokeAPI/Showdown que o resto do app usa **não** entram no jogo.

---

## 3. Escopo

### Dentro (Fase 1 — Vale Aurora)

- Tabuleiro de 73 casas (0–72), 10 locais, 7 ginásios, chefe final
- Dado, energia diária, casas de Captura / Cidade / Ginásio / Evento / Bônus
- Voltas: ao chegar no fim sem os requisitos, recomeça com criaturas de estágio mais difícil
- 99 criaturas originais (33 × 3 estágios); nunca aparece uma que o jogador já tem
- 5 itens, baralho de 12 eventos
- Time de até 6 criaturas + reserva
- Batalha PvP assíncrona entre jogadores na mesma casa
- Mapa Global, Card do Jogador, Ranking por fase, feed de movimentos
- Sequência de dias (streak)

### Fora (esta entrega)

- Fase 2 (segunda região) — o fim da Fase 1 mostra "em breve"
- Moedas / loja / doações dentro do jogo (ver [D7](#17-decisões-em-aberto))
- Notificação push / Telegram ("fulano te desafiou")
- Arte final das criaturas — o protótipo usa silhuetas/emoji por tipo

---

## 4. O loop do jogo

```
           ┌──────────── energia > 0? ───────────┐
           ▼                                     │
   [Rolar dado 1–6] → anda N casas → resolve a casa
                                         │
   ┌──────────┬──────────┬──────────┬────┴─────┬──────────┐
 Captura    Cidade    Ginásio    Evento     Bônus   (outro jogador
 2º dado    +2 itens  batalha    carta      +50 PP   na casa?)
 acertou?   cura      vs líder   efeito               → oferta de
 +criatura  desmaiada +insígnia  imediato               batalha PvP
 +PP                  +PP
           └────────────── volta ao início ──────────────┘
```

---

## 5. Regras exatas

### 5.1 Turno e energia

- Cada **rolagem do dado de movimento** gasta 1 de **energia**.
- **6 de energia por dia**, recarga à meia-noite (horário de Brasília, `now_br()`); acumula até **12**.
- A rolagem de captura, as batalhas e o uso de itens **não** gastam energia.
- Jogador novo começa na casa 0, com 0 PP, 6 de energia e **2 Iscas** na mão.

### 5.2 Movimento

- Dado 1–6, sorteado no servidor. O peão anda N casas para frente.
- **Parada obrigatória** na casa 71 (Desafio do Pico): o movimento para nela mesmo sobrando pontos.
- Ginásios **não** são parada obrigatória — só se luta quando se cai exatamente neles.

### 5.3 Casa de Captura

> **Regra de ouro (pedido do Felipe, 25/11/2026): nunca aparece para o jogador uma criatura que
> ele já tem.** A casa não tem criatura fixa — o servidor sorteia na hora (ver 5.12).

1. O servidor sorteia a criatura: do **estágio da volta atual**, que o jogador **ainda não tem** e
   que **não fugiu dele nesta volta**, dando preferência às do habitat daquele local.
2. O jogador pode escolher **um** item de captura (opcional) e rola o dado de captura.
3. **Captura** se o resultado bater com um dos números da criatura: **2 números** no Estágio 1
   (chance 2/6), **1 número** nos Estágios 2 e 3 (chance 1/6 — "nível mais difícil").
   - **Isca:** o jogador pode somar +1 ao resultado.
   - **Rede:** o jogador pode somar +1 ou −1 ao resultado.
   - **Amuleto:** captura garantida (não rola).
   - O servidor aplica o item **só se ele fizer diferença**; nesse caso ele é consumido.
4. **Acertou:** a criatura vai para o time (se houver vaga) ou para a reserva; ganha os PP dela.
5. **Errou:** a criatura **foge** — não volta a aparecer para ele nesta volta (pode aparecer
   numa volta seguinte).
6. **Acabaram as criaturas** do estágio que ele ainda não tem: sorteia do estágio seguinte; se
   ele já tem todas, a casa vira **+10 PP**. Assim o jogador nunca trava e nunca vê repetida.

### 5.4 Cidade

- Ganha **2 itens** sorteados (pesos no §8).
- **Cura todas as criaturas desmaiadas** (Centro de recuperação).

### 5.5 Ginásio

- Batalha contra o líder: **dado + ataque da melhor criatura saudável do time** vs **dado + nível do líder**.
- Nível do líder: 1º ginásio = 1, aumenta 1 por ginásio (7º = 7).
- **Vitória:** insígnia daquele ginásio + **40 PP** + 1 item. Empate = vitória do jogador.
- **Derrota:** nada se perde.
- Já tem a insígnia: a casa vira Cidade comum.
- Insígnias **não** são requisito para zerar — são prestígio e aparecem no card (ver [D3](#17-decisões-em-aberto)).

### 5.6 Evento (?)

Compra uma carta do baralho de eventos (§8). Efeito imediato. Se o efeito mover o peão, a casa de
destino **não** é resolvida (evita cadeias).

### 5.7 Bônus

+50 PP (casa 70: +100 PP).

### 5.8 Batalha PvP

**Quando:** ao cair numa casa onde outro jogador **está parado**, abre a opção **Batalhar** (opcional).

**Restrições:**
- Os dois precisam ter pelo menos 1 criatura saudável.
- O mesmo par só batalha **1 vez a cada 24 h**.
- O desafiado precisa estar com "aparecer para outros treinadores" ativo.

**Como resolve (assíncrono):**
1. O desafiante escolhe 1 criatura e confirma. O desafio fica **pendente** para o desafiado.
2. O desafiado escolhe a criatura dele quando entrar. Se não responder em **24 h**, o servidor
   escolhe a criatura saudável de maior ataque dele.
3. Cada lado: **dado + ataque da criatura** (+1 se usar Isca como bônus de batalha — opcional).
4. Maior total vence; **empate = defensor vence**.
5. **Vencedor:** rouba até **2 itens aleatórios** do perdedor + **30 PP**.
6. **Perdedor:** a criatura usada fica **desmaiada** até usar Tônico/Elixir ou cair numa Cidade.

### 5.9 Descobertas compartilhadas

Como a criatura é sorteada por jogador, a parte social passa a ser o **catálogo de descobertas**:
enquanto ninguém do servidor encontrou uma criatura, ela aparece como silhueta no catálogo. O
primeiro a encontrá-la fica registrado ("descoberta por *fulano*") e ela é revelada para todos.
Cada jogador captura a sua — ninguém "rouba" a criatura de outro.

### 5.10 Fim da fase

Ao chegar na casa **71 (Desafio do Pico)**:

- **Requisitos:** ≥ **300 PP** e **6 criaturas no time**.
- **Sem os requisitos:** aparece o aviso "Nova volta! Criaturas mais fortes à frente" e o peão
  volta para a **casa 0**, começando a **volta seguinte** (ver 5.12). PP, time, itens e insígnias
  são mantidos.
- **Com os requisitos:** batalha contra a **Guardiã do Pico** — melhor de 3 rodadas; em cada uma o
  jogador escolhe uma criatura diferente: **dado + ataque** vs **dado + 4**.
  - **Vitória:** vai para a casa 72, ganha o título **Mestre da Trilha — Vale Aurora**, o pin no
    Mapa Global sobe de nível e a Fase 2 aparece como "em breve".
  - **Derrota:** volta para a **casa 66** e tenta de novo (mantém PP e time).

### 5.11 Progressão e sequência

- **Progresso** exibido = locais alcançados (X/10).
- O ranking mostra só a fase atual do jogador e as anteriores.
- Ao zerar a fase, o jogador mantém time e PP na fase seguinte.
- **Sequência de dias:** +1 por dia em que o jogador rolou pelo menos uma vez; zera se pular um dia.
  No 7º dia seguido: +1 Rede (ver [D4](#17-decisões-em-aberto)).

### 5.12 Voltas e estágios

| Volta | Criaturas sorteadas | Números de captura | PP da criatura |
|---|---|---|---|
| 1ª | Estágio 1 | 2 (chance 2/6) | base (15–40) |
| 2ª | Estágio 2 | 1 (chance 1/6) | base × 2 |
| 3ª em diante | Estágio 3 | 1 (chance 1/6) | base × 3 |

- Cada criatura do Estágio 1 tem uma forma de Estágio 2 e uma de Estágio 3 (ex.: Seixo →
  Rochedo → Monólito), com **ataque +1 por estágio** (máx. 5). São criaturas **diferentes** no
  catálogo — capturar Seixo não impede encontrar Rochedo.
- O chip "Volta N" aparece no header e no card do jogador; o Mapa Global mostra a volta no pin.
- Ginásios já vencidos continuam valendo como Cidade nas voltas seguintes.

---

## 6. Tabuleiro da Fase 1 — Vale Aurora (73 casas)

Mantém a distribuição do documento original: 33 Captura (45%), 10 Cidade + 7 Ginásio (23%),
11 Evento (15%), 9 Bônus (12%), mais início, desafio e fim.

| Local | Casas | Ginásio (líder — tipo) |
|---|---|---|
| **Vila Semente** (início) | 0–2 | — |
| **Bosque Âmbar** | 3–10 | — |
| **Pedreira Cinza** | 11–18 | 17: Ginásio Vento — **Aurora** |
| **Lagoa Clara** | 19–26 | 25: Ginásio Correnteza — **Iago** |
| **Porto Faísca** | 27–34 | 33: Ginásio Rocha — **Dona Bento** |
| **Jardim Suspenso** | 35–42 | 41: Ginásio Sombra — **Noturno** |
| **Pântano Turvo** | 43–50 | 49: Ginásio Raiz — **Jurema** |
| **Cidade Mirante** | 51–58 | 57: Ginásio Trovão — **Capitã Raia** |
| **Ilha Brasa** | 59–65 | 65: Ginásio Brasa — **Tição** |
| **Pico Coroa** | 66–71 | 71: Desafio — **Guardiã do Pico** |
| **🏛️ Hall da Fama** (topo) | 72 | Quem venceu o Desafio — na ordem de conquista |

| Casa | Tipo | Conteúdo | | Casa | Tipo | Conteúdo |
|---|---|---|---|---|---|---|
| 0 | Início | Vila Semente | | 37 | Captura | Cipó |
| 1 | Captura | Brotim | | 38 | Evento | ? |
| 2 | Cidade | Vila Semente | | 39 | Captura | Plumito |
| 3 | Evento | ? | | 40 | Bônus | +50 PP |
| 4 | Captura | Pardalito | | 41 | Ginásio | Noturno |
| 5 | Bônus | +50 PP | | 42 | Captura | Sonhim |
| 6 | Captura | Bicudo | | 43 | Evento | ? |
| 7 | Cidade | Bosque Âmbar | | 44 | Captura | Sapão |
| 8 | Captura | Musguinho | | 45 | Cidade | Pântano Turvo |
| 9 | Evento | ? | | 46 | Captura | Lodim |
| 10 | Captura | Formigão | | 47 | Captura | Fumacê |
| 11 | Cidade | Pedreira Cinza | | 48 | Bônus | +50 PP |
| 12 | Captura | Seixo | | 49 | Ginásio | Jurema |
| 13 | Evento | ? | | 50 | Captura | Noctua |
| 14 | Captura | Cascalhão | | 51 | Captura | Miragem |
| 15 | Bônus | +50 PP | | 52 | Evento | ? |
| 16 | Captura | Tatuí | | 53 | Cidade | Cidade Mirante |
| 17 | Ginásio | Aurora | | 54 | Captura | Corujão |
| 18 | Captura | Breu | | 55 | Captura | Eco |
| 19 | Captura | Bolhudo | | 56 | Bônus | +50 PP |
| 20 | Evento | ? | | 57 | Ginásio | Capitã Raia |
| 21 | Cidade | Lagoa Clara | | 58 | Captura | Brutão |
| 22 | Captura | Garcelha | | 59 | Evento | ? |
| 23 | Captura | Concha | | 60 | Captura | Brasinha |
| 24 | Bônus | +50 PP | | 61 | Cidade | Ilha Brasa |
| 25 | Ginásio | Iago | | 62 | Captura | Lavor |
| 26 | Captura | Lambarim | | 63 | Captura | Fornalha |
| 27 | Evento | ? | | 64 | Bônus | +50 PP |
| 28 | Captura | Faiscão | | 65 | Ginásio | Tição |
| 29 | Cidade | Porto Faísca | | 66 | Evento | ? |
| 30 | Captura | Pilha | | 67 | Captura | Aurélio |
| 31 | Captura | Trovisco | | 68 | Captura | Coroado |
| 32 | Evento | ? | | 69 | Cidade | Pico Coroa |
| 33 | Ginásio | Dona Bento | | 70 | Bônus | +100 PP |
| 34 | Bônus | +50 PP | | 71 | Desafio | Guardiã do Pico |
| 35 | Captura | Mimosa | | 72 | Fim | 🏛️ Hall da Fama |
| 36 | Cidade | Jardim Suspenso | | | | |

---

## 7. Criaturas da Fase 1

> A coluna "Conteúdo" do tabuleiro (§6) passa a indicar o **habitat** de cada casa: na 1ª volta,
> a criatura listada é a preferida daquele local; nas voltas seguintes, a forma de Estágio 2/3
> dela. Se o jogador já a tem, sorteia outra (5.3).

**Estágio 1** abaixo (33). Estágios 2 e 3 (66 formas) são escritos na etapa J1, no mesmo
`criaturas.json` — total de **99 criaturas** na Fase 1.

Ataque de 1 a 4 (usado em ginásio, PvP e desafio final). Os PP crescem conforme a trilha avança.
Os números de captura foram distribuídos para que nenhum par se repita demais.

| # | Criatura | Tipo | Ataque | PP | Captura |
|---|---|---|---|---|---|
| 1 | Brotim | Planta | 1 | 15 | 2 · 5 |
| 2 | Pardalito | Vento | 1 | 15 | 1 · 4 |
| 3 | Bicudo | Vento | 1 | 15 | 3 · 6 |
| 4 | Musguinho | Planta | 1 | 15 | 1 · 6 |
| 5 | Formigão | Inseto | 2 | 20 | 2 · 4 |
| 6 | Seixo | Rocha | 2 | 20 | 3 · 5 |
| 7 | Cascalhão | Rocha | 2 | 20 | 1 · 5 |
| 8 | Tatuí | Terra | 2 | 20 | 4 · 6 |
| 9 | Breu | Sombra | 2 | 20 | 2 · 6 |
| 10 | Bolhudo | Água | 2 | 20 | 1 · 3 |
| 11 | Garcelha | Água/Vento | 2 | 25 | 3 · 4 |
| 12 | Concha | Água | 2 | 25 | 5 · 6 |
| 13 | Lambarim | Água | 2 | 25 | 2 · 3 |
| 14 | Faiscão | Elétrico | 3 | 25 | 3 · 5 |
| 15 | Pilha | Elétrico | 2 | 25 | 1 · 2 |
| 16 | Trovisco | Elétrico/Vento | 3 | 25 | 4 · 5 |
| 17 | Mimosa | Planta | 2 | 25 | 1 · 4 |
| 18 | Cipó | Planta | 3 | 25 | 2 · 5 |
| 19 | Plumito | Vento | 2 | 25 | 3 · 6 |
| 20 | Sonhim | Mente | 3 | 30 | 1 · 6 |
| 21 | Sapão | Água/Sombra | 3 | 30 | 2 · 4 |
| 22 | Lodim | Sombra | 3 | 30 | 3 · 5 |
| 23 | Fumacê | Sombra | 3 | 30 | 4 · 6 |
| 24 | Noctua | Inseto | 3 | 30 | 1 · 5 |
| 25 | Miragem | Mente | 3 | 30 | 2 · 6 |
| 26 | Corujão | Mente/Vento | 3 | 30 | 1 · 3 |
| 27 | Eco | Mente | 3 | 30 | 4 · 5 |
| 28 | Brutão | Luta | 4 | 35 | 2 · 3 |
| 29 | Brasinha | Fogo | 3 | 35 | 5 · 6 |
| 30 | Lavor | Fogo | 4 | 35 | 1 · 2 |
| 31 | Fornalha | Fogo | 4 | 35 | 3 · 4 |
| 32 | Aurélio | Luz | 4 | 40 | 1 · 6 |
| 33 | Coroado | Luz | 4 | 40 | 3 · 6 |

> Ainda não há arte. No protótipo, cada criatura é um círculo na cor do tipo + emoji/ícone
> genérico. A arte própria vem depois ([D6](#17-decisões-em-aberto)).

---

## 8. Itens e baralho de eventos

### Itens

| Item | Efeito | Peso no sorteio |
|---|---|---|
| **Isca** | +1 no dado de captura (ou +1 numa batalha PvP) | 35 |
| **Tônico** | Cura 1 criatura desmaiada | 30 |
| **Rede** | +1 ou −1 no dado de captura | 20 |
| **Elixir** | Cura todas as criaturas desmaiadas | 12 |
| **Amuleto** | Captura garantida | 3 |

Limite na mão: **10 itens** — o excedente é descartado com aviso.

### Baralho de eventos (12 cartas, embaralha de novo quando acaba — por jogador)

| Carta | Efeito |
|---|---|
| Vento a favor | Avance 2 casas |
| Atalho no mato | Avance 3 casas |
| Trilha alagada | Volte 2 casas |
| Ponte quebrada | Volte 3 casas |
| Achado no caminho | +30 PP |
| Ajudou um viajante | +20 PP |
| Mochila furada | −20 PP (mínimo 0) |
| Mercador ambulante | +1 item |
| Treino ao amanhecer | +1 de energia |
| Fonte termal | Cura todas as desmaiadas |
| Dia de sorte | Próxima captura com +1 automático |
| Tempestade | Perde 1 item aleatório |

---

## 9. Balanceamento (simulação)

Simulação Monte Carlo (5.000 partidas por cenário). O script está em [jornada-sim.py](jornada-sim.py).

| Cenário | Resultado |
|---|---|
| Regras do documento original, **1 volta** | Média de 5,2 criaturas e 261 PP; só **43%** chegam com 6 criaturas e **33%** com 300 PP |
| Volta para a casa 66 quando falta requisito | Muitos jogadores **nunca zeram** (só 2 casas de captura naquele trecho) |
| Volta para a casa 59, sem criatura selvagem | Jogador **trava para sempre** se já capturou tudo de 59–70 |
| Volta para a casa 0, Estágio 2+ com **2 números** | Mediana de 38 rolagens, máx. 68 |
| **Regras desta spec** (volta para a casa 0, Estágio 2+ com **1 número**, nunca repetida) | Mediana de **38 rolagens** (p90 = 46, máx. ~90); 41% zeram na 1ª volta, 53% na 2ª, 6% precisam de 3+ |

**Ritmo com 6 rolagens/dia (proposto):** mediana de **6,3 dias**, p90 de 7,7 dias.

Com 6/dia, a fase dura cerca de uma semana — dá tempo de ver os amigos passando à frente e voltar
no dia seguinte, que é o objetivo do loop. Reajustar depois com os dados reais de `game_turns`.

---

## 10. Modelo de dados

Tabelas novas via Flask-Migrate, todas com prefixo `game_`. O **conteúdo** (criaturas, casas,
itens, eventos) **não** vai para o banco — fica em JSON (§15). O banco guarda só o estado.

### `game_players` — estado do jogador (1 linha por usuário)

| Coluna | Tipo | Observação |
|---|---|---|
| `user_id` | INT PK, FK `users.id` | |
| `fase` | TINYINT | 1 = Vale Aurora |
| `posicao` | TINYINT | 0–72 |
| `pp` | INT | |
| `energia` | TINYINT | 0–12 |
| `energia_dia` | DATE | último dia em que a recarga diária foi aplicada |
| `sequencia_dias` | SMALLINT | |
| `ultimo_dia_jogado` | DATE | |
| `insignias` | JSON | lista de chaves de ginásio |
| `volta` | SMALLINT | volta atual (1, 2, 3…) — define o estágio sorteado |
| `acao_pendente` | JSON NULL | máquina de estados: `{"tipo":"captura","criatura":"rochedo"}` etc. (a criatura é sorteada **antes** de mostrar e gravada aqui — recarregar a página não troca o sorteio) |
| `baralho_eventos` | JSON | ordem restante do baralho do jogador |
| `titulo_fase1_em` | DATETIME NULL | data em que zerou |
| `last_seen` | DATETIME | atualizado pelo polling → bolinha verde = visto há < 2 min |
| `created_at` / `updated_at` | DATETIME | `now_br()` |

Índice: `(fase, posicao)` para o Mapa Global; `(fase, posicao DESC, pp DESC)` para o ranking.

### `game_creatures` — criaturas capturadas

`id`, `user_id`, `creature_key`, `fase`, `estagio`, `volta`, `slot` (1–6 ou NULL = reserva),
`desmaiada` (bool), `captured_at`. Único `(user_id, creature_key)` — **é essa restrição que
garante no banco que ninguém tem criatura repetida**.

### `game_escapes` — fugas da volta atual

`user_id`, `creature_key`, `volta`. PK `(user_id, creature_key, volta)`. O sorteio exclui as
fugas da volta atual.

### `game_items` — mão de itens

`user_id`, `item_key`, `qtd`. PK `(user_id, item_key)`.

### `game_discoveries` — descobertas compartilhadas

`creature_key` (PK), `discovered_by` (FK users), `discovered_at`.

### `game_turns` — log de tudo (auditoria + feed + balanceamento)

`id`, `user_id`, `fase`, `tipo` (`movimento`/`captura`/`evento`/`ginasio`/`pvp`/`desafio`/`item`),
`dado`, `de`, `para`, `resultado` (JSON), `pp_delta`, `created_at`. Índice `(fase, id)`.

### `game_battles` — PvP

`id`, `fase`, `casa`, `desafiante_id`, `desafiado_id`, `criatura_desafiante`, `criatura_desafiado`,
`dado_desafiante`, `dado_desafiado`, `vencedor_id`, `itens_roubados` (JSON),
`status` (`pendente`/`resolvida`/`expirada`), `created_at`, `resolved_at`.

> Correspondência com o documento original (Firebase): `player_id`→`user_id`, `nick`/`avatar_url`→
> `users.username`/`users.avatar`, `fase_atual`→`fase`, `posicao_tabuleiro`→`posicao`,
> `power_points`→`pp`, `criaturas`→`game_creatures`, `cartas_item`→`game_items`,
> `ultima_atividade`/`status`→`last_seen`, `cidade_atual`→calculada pela posição.

---

## 11. Rotas e API

Blueprint `app/blueprints/jornada/`. Tudo exige login, exceto o que estiver marcado como público.

### Páginas

| Rota | Tela |
|---|---|
| `GET /jornada/` | Mapa Global (público: sim, só leitura) |
| `GET /jornada/jogar` | Meu tabuleiro |
| `GET /jornada/ranking?aba=fase1\|global` | Ranking |
| `GET /jornada/time` | Meu time e reserva |
| `GET /jornada/treinador/<username>` | Card do jogador |

### API (JSON, CSRF no header)

| Rota | O que faz |
|---|---|
| `POST /jornada/api/rolar` | Gasta energia, rola, move, resolve a casa. Devolve o resultado e a `acao_pendente` |
| `POST /jornada/api/capturar` | Body `{item?}`. Rola a captura da `acao_pendente` |
| `POST /jornada/api/pular` | Desiste da captura / da oferta de batalha |
| `POST /jornada/api/item` | Body `{item, criatura?}`. Usa Tônico/Elixir fora de captura |
| `POST /jornada/api/time` | Body `{slots:[...]}`. Reorganiza o time |
| `POST /jornada/api/pvp/desafiar` | Body `{alvo, criatura}` |
| `POST /jornada/api/pvp/<id>/responder` | Body `{criatura}` |
| `POST /jornada/api/desafio` | Body `{criaturas:[a,b,c]}`. Batalha final |
| `GET /jornada/api/estado?desde=<turn_id>` | Polling: meu estado + movimentos novos dos outros + desafios pendentes |
| `GET /jornada/api/mapa` | Contagem e avatares por local (cache de 15 s) |

Estados de `acao_pendente`: `null` → (rolar) → `captura` | `pvp_oferta` | `desafio` → `null`.
**Enquanto houver ação pendente, `rolar` é recusado** — o jogador resolve primeiro.

---

## 12. Telas

O layout segue os mockups enviados em 25/11/2026. O conteúdo é trocado conforme o §2.

**Layout comum (todos os mockups):**
- Header: logo próprio + nome do jogo + chip de **PP** (e de energia no lugar das moedas — ver [D7](#17-decisões-em-aberto))
- Barra inferior fixa: **Mapa · Ranking · Time · Perfil**
- Visual claro e colorido, cards arredondados; seguir o grid de 8 pt

### Tela 1 — Mapa Global (`/jornada/`)
- Trilha vertical: Vila Semente embaixo → Pico Coroa → **🏛️ Hall da Fama no topo** (nó dourado com coroa,
  avatares dos campeões em ordem de conquista; toque abre a lista e leva a `/jornada/hall-da-fama`, com pódio).
- **Em cada nó: até 4 avatares dos jogadores parados ali + "N treinadores aqui"**, bolinha verde
  para quem foi visto há menos de 2 min. (Nos mockups estão os líderes — trocar pelos jogadores.)
- Tocar no nó → lista de quem está ali (avatar, nick, PP, online) → toca no nome → Card.
- Destaque no nó onde **eu** estou.

### Tela 2 — Meu tabuleiro (`/jornada/jogar`)
- Trilha do trecho atual com ícones por tipo de casa e os peões dos outros jogadores.
- Painel inferior: **dado grande** + botões contextuais (**Capturar** só com captura pendente,
  **Batalhar** só com oferta de PvP) + **itens na mão** (1 toque para usar).
- Toast de resultado ("Tirou 5! Capturou Seixo! +20 PP").
- Contador de energia ("4/6 rolagens hoje · recarrega à meia-noite").

### Tela 3 — Card do Jogador (`/jornada/treinador/<username>`)
- Avatar + online, nick, "Parou em: *Lagoa Clara* — Fase 1", barra **X/10 locais**,
  PP, criaturas **X/99**, sequência de dias, última atividade, insígnias, time de 6.
- Botões **Desafiar** (só se estiver na mesma casa e o PvP for permitido) e **Ver time**.

### Tela 4 — Ranking (`/jornada/ranking`)
- Abas **Fase 1** / **Global** (a aba de cada fase só aparece depois de alcançá-la).
- Ordem: `fase DESC, posicao DESC, pp DESC`.
- 1º lugar em destaque; **minha posição fixa no rodapé**.

### Tela 5 — Time (`/jornada/time`)
- 6 slots + reserva, arrastar para trocar (pode reutilizar a
  [receita de quadro arrastável](../../../../Doc-Geral/docs/padroes/receita-quadro-arrastavel.md)).
- Desmaiadas em cinza, com botão "usar Tônico".

---

## 13. Tempo real e desempenho

- **Polling a cada 5 s** em `/jornada/api/estado` com a tela visível; para a cada 30 s com a aba
  em segundo plano (`visibilitychange`). **Não usar SSE/WebSocket:** a produção roda o Gunicorn
  com 1 worker × 4 threads (`Dockerfile`) e cada conexão aberta prenderia uma thread.
- `estado` devolve só o delta (`game_turns.id > desde`), no máximo 50 linhas.
- `mapa` usa cache em memória de 15 s (contagem por local é barata, mas é chamada por todos).
- Animação do peão "andando" é feita no front a partir de `de`/`para` do delta.
- Atenção: o log de 27/10/2026 mostra `WORKER TIMEOUT` + `SIGKILL ... out of memory?` no casakek.
  Medir a memória antes de abrir o jogo para todos.

---

## 14. Anti-trapaça

- **Todo sorteio no servidor** (`secrets.SystemRandom`). O front só anima o resultado.
- `SELECT ... FOR UPDATE` na linha de `game_players` em toda ação que muda o estado — evita
  rolagem dupla com 4 threads ou cliques repetidos.
- Uma ação só é aceita se combinar com a `acao_pendente` atual.
- Flask-Limiter: `rolar` e `capturar` com 30/min por usuário.
- Toda ação vira linha em `game_turns` (permite auditar e reverter).
- Contas de teste (padrão "E2E …") ficam fora do ranking e do mapa.

---

## 15. Conteúdo como dados

```
app/data/jornada/
├── jogo.json          # nome do jogo, títulos, textos de UI
├── fase1/
│   ├── regiao.json    # nome, locais, faixas de casas, ginásios/líderes
│   ├── tabuleiro.json # 73 casas: {idx, tipo, ref}
│   ├── criaturas.json # 99 criaturas: {key, nome, tipo, estagio, habitat, ataque, pp, captura:[...]}
│   └── eventos.json   # 12 cartas
└── itens.json         # 5 itens + pesos
```

- O motor (`app/services/jornada/`) lê esses arquivos na subida do app e valida a estrutura
  (73 casas, toda `ref` existe, números de captura entre 1 e 6 e distintos).
- Trocar o nome do jogo, uma criatura ou o tabuleiro = editar JSON, sem tocar no motor.
- Uma fase nova = uma pasta nova `faseN/`.

---

## 16. Fases de entrega

| Etapa | Entrega | Esforço |
|---|---|---|
| **J1 — Motor solo** | JSONs da Fase 1, tabelas, `rolar`/`capturar`/itens/eventos/cidade/bônus, energia, tela "Meu tabuleiro" funcional (visual simples), testes pytest do motor (regras do §5 + simulação como teste de sanidade) | ~2 dias |
| **J2 — Social** | Mapa Global com avatares e online, Card do Jogador, Ranking, polling, catálogo de descobertas | ~1,5 dia |
| **J3 — Competição** | Ginásios, PvP assíncrono, desafio final, título, sequência de dias | ~1,5 dia |
| **J4 — Visual** | Layout dos mockups, animação do peão, toasts, arte/ícones das criaturas | ~1–2 dias |
| **J5 — Soltar** | Teste local com 3–4 contas, medir memória no casakek, deploy, link no menu do app | ~½ dia |

Cada etapa é testada **local** antes de seguir; deploy só na J5 e quando o Felipe pedir.

### Status

| Etapa | Situação |
|---|---|
| **J1** | ✅ **Concluída local em 25/11/2026** — motor (`app/services/jornada/`), conteúdo provisório (`app/data/jornada/`), tabelas + migration `a1b2c3d4e5f7`, API, telas `/jornada/jogar` e `/jornada/time`, 34 testes (`tests/test_jornada.py`). Ginásios e Desafio final já entraram na J1. 20 partidas automáticas completas: mediana de **43 rolagens** (máx. 62), 0 erros de regra, 0 criaturas repetidas. Sem deploy e sem link no menu. |
| **J2** | ✅ **Concluída local em 25/11/2026** — Mapa Global (público) com **Hall da Fama no topo**, página `/jornada/hall-da-fama` (pódio), Ranking (Fase/Global + "Você está em Xº" fixo), Card do treinador, catálogo `/jornada/descobertas`, feed "Agora na trilha", peões dos outros no tabuleiro, polling 5 s/30 s (`app/services/jornada/social.py`). |
| **J3** | ✅ **Concluída local em 25/11/2026** — PvP assíncrono (`app/services/jornada/pvp.py`, tabela `game_battles`, migration `b2c3d4e5f6a8`): desafiar na mesma casa, responder, expiração em 24 h com escolha automática, W.O., Isca +1, roubo de até 2 itens, 1 batalha por par a cada 24 h, defensor não vê a criatura do desafiante. |
| **J4** | ✅ **Concluída local em 25/11/2026** — layout dos mockups (`templates/jornada/_layout.html`, `static/jornada/`): header com energia/PP, barra Mapa · Jogar · Ranking · Time · Perfil, tabuleiro em serpentina, sheets de captura/batalha/desafio, toasts. Emblema próprio (bússola), sem pokébola. |
| J5 | **Pendente — aguarda o Felipe**: migrations no MySQL do casakek, deploy (`deploy.ps1 -Build`), link "Jornada" no menu, medir memória do servidor (log de 27/10 com SIGKILL). |

**Testes (25/11/2026):** 53 testes pytest da Jornada (`tests/test_jornada.py`, `tests/test_jornada_social.py`); suíte completa 181 ✓ e as mesmas 10 falhas preexistentes de antes do projeto. E2E no Edge (390 px): login com CSRF real, 6 rolagens com energia 6→0, sheet de captura + toast, time/ranking/perfil/mapa/descobertas, sem overflow horizontal. Spec Cypress `cypress/e2e/04_jornada.cy.js` criada (o binário do Cypress não está instalado na máquina).


---

## 17. Decisões em aberto

| # | Questão | Proposta desta spec |
|---|---|---|
| D1 | Nome definitivo do jogo e da região | "Trilha dos Domadores" / "Vale Aurora" |
| D2 | Energia por dia | ✅ Adotado na J1: 6/dia, acumula até 12 |
| D3 | Insígnias valem como requisito para zerar? | Não — só prestígio |
| D4 | Recompensa da sequência de dias | 7 dias seguidos = +1 Rede |
| D5 | PvP também ao **passar** pelo jogador (documento original) ou só ao **cair** na mesma casa? | ✅ Adotado: só ao cair — passar geraria desafios demais |
| D6 | Arte e nomes definitivos das criaturas | Protótipo com ícone por tipo e formas II/III com nome provisório; definitivos no backlog #28 |
| D7 | **Moedas** (aparecem nos mockups, 1.250) | Fora da Fase 1. Se entrarem, só ganhas jogando — nunca vendidas (doação não pode comprar vantagem) |
| D8 | O Mapa Global é público (sem login)? | Sim, só leitura — vira vitrine do app, como o `/estoque/<username>` |
| D9 | Jogador escolhe aparecer no mapa? | Reaproveitar o toggle existente "aparecer para outros treinadores" |
| D10 | Criatura que **fugiu** pode reaparecer? | Não na mesma volta; sim nas seguintes |
| D11 | Universo do jogo | Felipe quer o universo Pokémon (25/11/2026). Fica com criaturas originais — o Claude não implementa a versão com Pokémon oficiais nem usa a tabela `species` como conteúdo do jogo |
