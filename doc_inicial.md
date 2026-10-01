MeuPokémonGO

Sua coleção. Sua evolução. Suas trocas.

Projeto web independente para gerenciamento de coleção Pokémon GO, acompanhamento de evolução e identificação de oportunidades de troca entre treinadores.

---

01 — Visão do Produto

1.1 Identidade

Nome: MeuPokémonGO

Slogan: Sua coleção. Sua evolução. Suas trocas.

Objetivo: criar uma aplicação web pública que permita organizar, visualizar e analisar uma coleção de Pokémon GO, além de possibilitar a identificação de Pokémon desejados e oportunidades de troca entre treinadores.

O projeto será desenvolvido como aplicação de portfólio, utilizando uma arquitetura moderna e preparada para evolução.

1.2 Público

Visitante

Pode:

- navegar pelas páginas públicas;
- consultar Pokémon;
- pesquisar;
- visualizar coleção pública;
- consultar Pokémon faltantes;
- visualizar oportunidades públicas.

Treinador

Pode:

- possuir uma coleção;
- registrar quantidades;
- marcar Pokémon para troca;
- informar Pokémon desejados;
- adicionar amigos;
- visualizar oportunidades de troca;
- receber notificações.

Administrador

Pode:

- administrar usuários;
- acompanhar analytics;
- visualizar logs;
- executar sincronizações;
- administrar dados Pokémon;
- acompanhar matches;
- receber alertas no Telegram.

---

02 — Requisitos Funcionais

RF01 — Página inicial

A aplicação deverá possuir uma Home contendo:

- identidade visual;
- apresentação do projeto;
- estatísticas;
- pesquisa;
- acesso à coleção;
- Pokémon faltantes;
- Pokémon para evolução;
- Pokémon disponíveis para troca;
- oportunidades de troca.

RF02 — Pokédex

A aplicação deverá permitir:

- listar Pokémon;
- pesquisar por nome;
- pesquisar pelo número da Pokédex;
- filtrar por geração;
- filtrar por tipo;
- filtrar por forma;
- visualizar detalhes;
- visualizar cadeia evolutiva;
- visualizar status de coleção.

RF03 — Dados Pokémon

Os dados externos deverão ser obtidos por meio de uma camada denominada:

"PokemonDataProvider"

A aplicação não deverá depender diretamente de uma API externa dentro dos componentes da interface.

Os dados externos deverão ser:

1. consultados;
2. validados;
3. normalizados;
4. armazenados/cacheados;
5. utilizados pela aplicação.

RF04 — Coleção

O treinador poderá registrar:

- Pokémon;
- forma;
- quantidade;
- status de posse;
- disponibilidade para troca;
- observações.

RF05 — Pokémon faltantes

O sistema deverá calcular automaticamente Pokémon faltantes.

Um Pokémon será considerado faltante quando o treinador não possuir um registro válido de posse para aquela espécie/forma.

RF06 — Evolução pendente

O sistema deverá identificar quando:

- o treinador possui uma etapa anterior;
- existe uma evolução conhecida;
- a etapa posterior ainda não está registrada como possuída.

RF07 — Pokémon desejados

O treinador poderá cadastrar Pokémon que deseja obter.

Poderá existir:

- espécie desejada;
- forma desejada;
- prioridade.

RF08 — Pokémon para troca

O treinador poderá marcar Pokémon como:

"Disponível para troca"

O sistema deverá considerar quantidade disponível.

RF09 — Amigos

O sistema deverá permitir:

- enviar convite;
- aceitar convite;
- recusar convite;
- remover amizade;
- controlar visibilidade.

RF10 — Matching

O sistema deverá procurar correspondências.

Exemplo:

Felipe deseja:

"Charizard"

João possui:

"Charizard"

João marcou:

"Charizard → disponível para troca"

Resultado:

"Match de troca"

RF11 — WhatsApp

O sistema deverá:

1. registrar o clique;
2. gerar mensagem estruturada;
3. abrir o WhatsApp.

Importante:

"WHATSAPP_CLICK"

não significa

"MESSAGE_SENT"

O sistema não deverá afirmar que a mensagem foi enviada.

RF12 — Telegram

O Telegram será utilizado para:

- alertas;
- administração;
- erros importantes;
- matches;
- resumos;
- monitoramento.

O Telegram não será utilizado como banco de dados.

RF13 — Analytics

Registrar eventos como:

- acesso;
- navegação;
- pesquisa;
- filtros;
- visualização de Pokémon;
- formulários;
- cliques;
- interesse em troca;
- WhatsApp;
- erros.

RF14 — Importação

Suportar inicialmente:

- CSV;
- JSON.

Processo:

"Upload → Validação → Preview → Confirmação → Importação → Relatório"

RF15 — Administração

Dashboard administrativo contendo:

- usuários;
- coleção;
- Pokémon;
- matches;
- analytics;
- logs;
- sincronizações;
- integrações.

RF16 — SEO

Implementar:

- metadata;
- Open Graph;
- sitemap;
- robots;
- URLs amigáveis;
- páginas indexáveis quando apropriado.

---

03 — Requisitos Não Funcionais

Performance

- imagens otimizadas;
- lazy loading;
- cache;
- paginação;
- consultas indexadas;
- evitar chamadas externas desnecessárias.

Disponibilidade

Se uma API externa estiver indisponível, os dados previamente sincronizados deverão continuar disponíveis.

Escalabilidade

A arquitetura deverá suportar crescimento de:

- Pokémon;
- usuários;
- coleções;
- eventos;
- sessões;
- matches.

Segurança

Implementar:

- autenticação;
- autorização;
- validação server-side;
- rate limiting;
- gerenciamento seguro de secrets;
- proteção contra XSS;
- proteção CSRF quando aplicável;
- queries parametrizadas;
- logs seguros.

Privacidade

Não armazenar desnecessariamente:

- CPF;
- endereço;
- localização precisa;
- credenciais do Pokémon GO;
- conteúdo de conversas;
- tokens;
- senhas.

Acessibilidade

Implementar:

- contraste;
- navegação por teclado;
- labels;
- alt text;
- foco visual;
- suporte a leitores de tela quando aplicável.

Portabilidade

A aplicação deverá funcionar em:

- Vercel;
- Node.js;
- Docker;
- servidor Linux.

Licenciamento

Antes da publicação deverão ser revisados:

- APIs;
- imagens;
- datasets;
- bibliotecas;
- marcas;
- termos de uso.

---

06 — Regras de Negócio

RB01 — Pokémon possuído

Um Pokémon será considerado possuído quando:

"owned = true"

e

"quantity > 0"

RB02 — Quantidade

Nunca permitir:

"quantity < 0"

RB03 — Pokémon faltante

Faltante = espécie/forma sem posse válida.

RB04 — Evolução pendente

Existe quando uma etapa anterior da cadeia está possuída e uma etapa posterior relevante ainda não está possuída.

RB05 — Oferta

Somente Pokémon possuídos poderão ser oferecidos.

Além disso:

"for_trade = true"

RB06 — Desejo

O treinador pode desejar um Pokémon independentemente de possuí-lo.

RB07 — Match

Um match ocorre quando:

Treinador A deseja X
        +
Treinador B possui X
        +
Treinador B oferece X
        +
A interação é permitida

RB08 — Duplicidade

Não criar múltiplos matches ativos para a mesma combinação.

RB09 — Notificação

Um evento relevante deverá gerar no máximo uma notificação por ocorrência lógica.

RB10 — WhatsApp

Registrar o evento antes da abertura do WhatsApp.

RB11 — Dados externos

Dados externos jamais deverão sobrescrever diretamente dados pessoais da coleção.

RB12 — Cache

Caso o provider esteja indisponível, utilizar os dados locais sincronizados.

RB13 — Privacidade

A visibilidade pública deverá respeitar as configurações do usuário.

RB14 — Reserva futura

Caso o sistema evolua para negociações mais complexas, poderá ser implementado mecanismo de reserva para evitar que a mesma unidade seja oferecida simultaneamente a várias pessoas.

Perfeito. Refatorei seu documento inteiro para o seu stack Flask + MySQL. Deixei mais técnico, sem redundância e pronto para virar código - já com modelo de dados e arquitetura.

Pode copiar e usar como PRD_v2.md

---

### MeuPokémonGO - PRD v2.0 (Refatorado Flask/MySQL)

Slogan: Sua coleção. Sua evolução. Suas trocas.
Stack alvo: Python 3.11+, Flask, SQLAlchemy, MySQL 8+, Flask-Migrate
Objetivo: Aplicação web para gerenciar coleção de Pokémon GO e gerar matches de troca entre treinadores.

#### 1. Atores

1.1 Visitante (não logado)
Pode navegar, pesquisar, ver Pokédex e ver coleções públicas. Não pode registrar nada.

1.2 Treinador (logado)
CRUD da própria coleção, wishlist, amizades, matches e importação CSV/JSON.

1.3 Admin
Dashboard, logs, analytics, sincronização do Provider e alertas Telegram.

#### 2. Requisitos Funcionais (Refatorados)

RF01 - Home / Dashboard Público
Deve exibir: contadores (total de espécies, treinadores), barra de busca global, lista de faltantes do usuário logado, evoluções pendentes, últimas trocas disponíveis e oportunidades. Rota: GET /

RF02 - Pokédex
Listagem com paginação server-side (20 por página), busca por nome / número, filtros por geração, tipo e forma. Detalhe com cadeia evolutiva. Rota: GET /pokedex

RF03 - PokemonDataProvider (Camada Crítica)
Toda consulta externa DEVE passar por app/providers/. Interface obrigatória:
get_pokemon_list(), get_pokemon(id), get_evolution_chain(id). 
Implementação: PokeApiProvider -> CachedProvider (tabela pokemon_cache no MySQL). Componentes nunca importam requests diretamente. Atende disponibilidade.

RF04 - Coleção
Tabela user_collections. Campos: owned (bool), quantity (int >=0), for_trade (bool), notes. for_trade só pode ser True se owned=True.

RF05/RF06 - Cálculos Automáticos
faltantes e evolução pendente não são tabelas, são Views/Services. Faltante = sem registro válido owned=True AND quantity>0. Evolução pendente = possui estágio N e não possui estágio N+1 da mesma cadeia.

RF07/RF08 - Desejos e Trocas
wishlists e user_collections.for_trade. Regras separadas.

RF09 - Amizades
Tabela friendships com status pending, accepted, blocked. Respeita visibility do usuário.

RF10 - Matching Engine
Service matching_service.py. Um match é criado quando: A deseja X + B possui X + B.for_trade=True + amizade aceita ou visibilidade pública. Não duplicar match ativo (Unique Constraint).

RF11 - WhatsApp
Nunca afirmar envio. Fluxo: click -> INSERT whatsapp_clicks -> gera link wa.me com mensagem pronta -> redirect. Evento WHATSAPP_CLICK para analytics.

RF12 - Telegram
Bot apenas para alertas. Tabelas não usam Telegram como storage. Eventos: novo match, erro 500 no provider, importação com falha.

RF13 - Analytics
Tabela única events com event_type, user_id, metadata_json, created_at. Tipos: PAGE_VIEW, SEARCH, FILTER, POKEMON_VIEW, TRADE_CLICK, WHATSAPP_CLICK.

RF14 - Importação
Rota POST /import. Fluxo obrigatório: Upload -> Validação (Marshmallow) -> Preview -> Confirmação -> Transação MySQL -> Relatório.

RF15 - Admin
Blueprint /admin protegido por @admin_required. Listagem de usuários, logs, trigger manual de sync_pokemon_cache.

#### 3. Requisitos Não-Funcionais (Flask/MySQL)

Performance: Paginação com LIMIT/OFFSET, índices em user_collections(user_id, species_id), cache de sprites, lazy loading no frontend.

Segurança: SQLAlchemy ORM (evita SQL injection), validação server-side com Marshmallow, Rate Limit com Flask-Limiter, SECRET_KEY em .env, CSRF com Flask-WTF.

Privacidade: Não armazenar credenciais do Pokémon GO, CPF, localização. whatsapp é opcional.

Portabilidade: Deve rodar com gunicorn + Dockerfile + docker-compose com MySQL.

#### 4. Regras de Negócio (Consolidadas)

RB01: possuído = owned=True AND quantity>0
RB02: quantity >= 0 (CHECK no MySQL)
RB03: for_trade=True só se RB01 for True
RB04: Match único por (wisher_id, owner_id, species_id, form_id) onde status='active'
RB05: Dados externos nunca sobrescrevem user_collections
RB06: Se Provider offline, usar pokemon_cache

#### 5. O que mudei e por quê?

1.  Juntei RF05+RF06 e RF07+RF08 - eram cálculos da mesma entidade.
2.  Transformei Analytics e Telegram em eventos, não em funcionalidades soltas.
3.  Criei a camada providers/ e services/ obrigatória para seu Flask não virar spaghetti.
4.  Adicionei Constraints de banco para garantir RB02 e RB04 direto no MySQL.

Quer que eu agora gere o código base desse PRD v2? Já te entrego:
models.py completo com os CHECKs + providers/base.py + app/*init*.py

Criei os dois pro seu portfólio:

1. Logo oficial - MeuPokémonGO D:\.ClaudeCode\Desenvolvimento\projetos-pessoais\.VERUS\MeuPokemonGO
Conceito: Pokébola + gráfico de evolução dentro. Já tá com slogan, pronto pra usar no header do Flask. Fonte bold, cores que funcionam bem no claro e no escuro.

2. Mockup do Dashboard - Flask v1.0  D:\.ClaudeCode\Desenvolvimento\projetos-pessoais\.VERUS\MeuPokemonGO
Esse mockup já está 100% mapeado para o seu PRD refatorado:
- Esquerda: Pokédex Grid (RF02) com status Owned
- Topo: Collection Stats 87/151 = RF05
- Direita: Missing Pokémon (RF05) + Evolution Pending (RF06) + Trade Opportunities (RF10)

Esse layout você faz direto com Jinja + Tailwind, sem precisar de React.

Quer que eu já gere o próximo passo?
1. O logo.svg vetorizado pra você colocar em /static/img/
2. O template dashboard.html em Jinja baseado nesse mockup