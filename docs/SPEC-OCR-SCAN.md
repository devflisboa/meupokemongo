# Spec: Catalogação via Screenshot + OCR (#17-B)

*Revisão: 13/10/2026 — baseada na arquitetura real do projeto*

---

## 1. Contexto e objetivo

O backlog (#17) avaliou três abordagens para catalogação em lote:
PokeGenie CSV (já existe), vídeo+OCR e ADB. Esta spec implementa uma
**quarta abordagem, mais ergonômica**: upload de screenshot direta do
celular → OCR no servidor Flask → pré-preenchimento do formulário de
catalogar.

**Problema resolvido:** cadastrar um Pokémon individual com IV real
hoje exige o PokeGenie Pro (pago) ou digitação manual. Com o OCR, o
usuário tira o print da tela do Pokémon GO e o app extrai nome, CP, HP
e IVs automaticamente.

**Não é:** botão flutuante em tempo real. Isso requer app Android nativo
(`SYSTEM_ALERT_WINDOW`) e está fora do escopo desta feature.

---

## 2. Escopo

### Dentro

- Rota `/scan/` com upload de imagem (JPG/PNG/WebP)
- Processamento OCR no servidor (pytesseract + Pillow)
- Extração de: nome do Pokémon, CP, HP, IVs (tela de appraisal)
- Detecção de shiny por pixel signature (cor do sprite — melhor esforço)
- Correspondência nome → `Species` do banco local
- Preview com dados extraídos editáveis antes de salvar
- Salvamento como `UserPokemon` (source="scan") + atualização de `UserCollection`
- Suporte a lote: até 10 imagens por upload
- UX mobile-first (câmera do celular como input)

### Fora do escopo (esta entrega)

- Botão flutuante sobre o Pokémon GO
- Cálculo de PvP rank (grande, implementar junto ao #19)
- Captura de vídeo ou streaming de tela
- Moveset (requer segunda tela de scroll no GO)
- Detecção de shadow/purified/lucky (requer análise de sprite complexa)

---

## 3. Telas do Pokémon GO que o OCR vai ler

### Tela principal do Pokémon (Tela A)

```
┌──────────────────────────────────────┐
│  [tipo]                              │
│  Pikachu                        ✨   │  ← nome + ícone shiny (se brilhante)
│  CP 1234                             │  ← CP
│                                      │
│          [sprite do Pokémon]         │
│                                      │
│  HP ██████░░  89 / 89                │  ← HP atual e máximo
│  ♦ 4800   🍬 150                    │  ← poeira + candy
└──────────────────────────────────────┘
```

**Dados extraíveis:** nome, CP, HP, candy count
**Dados não visíveis:** IVs individuais

### Tela de Avaliação / Appraisal (Tela B)

```
┌──────────────────────────────────────┐
│  Pikachu                   CP 1234  │
│                                      │
│  Ataque   ████████████ 15            │  ← IV Ataque (0–15)
│  Defesa   █████████░░░ 12            │  ← IV Defesa (0–15)
│  PS       ████████████ 15            │  ← IV PS/Stamina (0–15)
│                                      │
│  "Seu Pokémon é uma maravilha!"      │  ← texto de avaliação
└──────────────────────────────────────┘
```

**Dados extraíveis:** IVs numéricos (0–15 cada), nome, CP
**Nota:** desde 2023 o GO exibe os IVs como números — não é necessário
calcular via fórmula. A precisão do OCR aqui é mais importante.

> **Estratégia:** aceitar ambas as telas. Se o usuário enviar a Tela A,
> extrai nome+CP+HP. Se enviar a Tela B (appraisal), extrai também os
> IVs. O parser detecta qual tela é pela presença de "Ataque / Defesa / PS"
> no texto extraído.

---

## 4. Biblioteca OCR

### Comparação para este caso de uso

| Biblioteca | Instalação | Acurácia | Requisito extra | Decisão |
|---|---|---|---|---|
| `pytesseract` | `pip install` + binário | Boa (após pré-proc.) | `tesseract-ocr` no Dockerfile | **Escolhida** |
| `easyocr` | `pip install` | Boa sem pré-proc. | ~300 MB de modelos | Alternativa se pytesseract falhar |
| `google-cloud-vision` | `pip install` | Excelente | API key + custo | Futuro, se acurácia insuficiente |

**Motivo da escolha:** pytesseract é leve em runtime. O Pillow (já instalado)
resolve o pré-processamento. O único custo é adicionar `tesseract-ocr` ao
Dockerfile — uma linha.

### Pré-processamento necessário

O texto do Pokémon GO é branco sobre fundo escuro com gradiente. A
sequência de processamento com Pillow:

```
1. Crop para ROI (região de interesse)
2. Converter para grayscale
3. Inverter (texto preto sobre fundo branco — Tesseract prefere)
4. Binarizar com threshold adaptativo (evita variações de gradiente)
5. Escalar 2× (melhora acurácia em CP e HP que são caracteres pequenos)
6. Enviar ao pytesseract com config: --psm 6 (bloco de texto uniforme)
```

### ROIs por seção da tela

As coordenadas são **relativas** (0.0–1.0 da largura/altura da imagem)
para suportar diferentes resoluções de celular:

| Campo | y_start | y_end | x_start | x_end | Notas |
|---|---|---|---|---|---|
| Nome | 0.05 | 0.15 | 0.05 | 0.75 | Excluir lado direito (ícone shiny) |
| CP | 0.12 | 0.22 | 0.20 | 0.80 | "CP" precede o número |
| HP | 0.58 | 0.68 | 0.05 | 0.95 | "HP" ou barra visual |
| IV Ataque | 0.30 | 0.42 | 0.60 | 0.95 | Só na Tela B (appraisal) |
| IV Defesa | 0.42 | 0.54 | 0.60 | 0.95 | Só na Tela B |
| IV Stamina | 0.54 | 0.66 | 0.60 | 0.95 | Só na Tela B |

> **Nota:** esses valores são estimativas calibradas para 1080×2400 (ratio 1:2.2).
> O serviço deve recalibrar por aspect ratio detectado.
> Ratio < 1.8 → provavelmente tablet/screenshot cortado → aviso ao usuário.

---

## 5. Arquitetura de código

### Novo blueprint: `scan`

Seguir o mesmo padrão do blueprint `import_` existente:
upload → parse → preview → confirmar.

```
app/blueprints/scan/
    __init__.py      # define bp = Blueprint("scan", ...)
    routes.py        # /scan/ (upload), /scan/confirmar (POST)
app/services/
    ocr_service.py   # toda a lógica de OCR (sem Flask, testável)
app/templates/scan/
    index.html       # formulário de upload (mobile-first)
    preview.html     # resultado do OCR com campos editáveis
```

Registro no `app/__init__.py`:
```python
from .blueprints.scan import bp as scan_bp
app.register_blueprint(scan_bp, url_prefix="/scan")
```

### `ocr_service.py` — responsabilidades

```python
def process_images(image_files: list[bytes]) -> list[ScanResult]:
    """Processa uma lista de imagens e retorna os dados extraídos."""

def _preprocess(img: Image) -> Image:
    """Grayscale → invert → threshold → scale 2×."""

def _detect_screen_type(text: str) -> Literal["main", "appraisal", "unknown"]:
    """Detecta se é Tela A (main) ou Tela B (appraisal) pelo texto."""

def _extract_name(text: str) -> str | None:
    """Regex + fuzzy match contra lista de nomes do banco."""

def _extract_cp(text: str) -> int | None:
    """Regex: r'CP\\s*(\\d+)' ou r'(\\d{3,4})' no ROI de CP."""

def _extract_hp(text: str) -> tuple[int, int] | None:
    """Regex: r'(\\d+)\\s*/\\s*(\\d+)' → (atual, máximo)."""

def _extract_ivs(text: str) -> tuple[int, int, int] | None:
    """Regex nos três campos de IV → (atk, def, sta)."""

def _detect_shiny(img: Image, name_roi: Image) -> bool:
    """Detecta pixel dourado/estrela no canto superior direito da área do nome."""

def _match_species(name: str) -> Species | None:
    """Busca por nome_pt exato → fuzzy match → name exato."""
```

### `ScanResult` — dataclass de retorno

```python
@dataclass
class ScanResult:
    # Dados extraídos (None = não encontrado na imagem)
    raw_name: str | None       # texto bruto do OCR
    species: Species | None    # match no banco (pode ser None)
    cp: int | None
    hp_current: int | None
    hp_max: int | None
    atk_iv: int | None         # 0–15
    def_iv: int | None
    sta_iv: int | None
    iv_pct: float | None       # calculado: (atk+def+sta)/45*100
    is_shiny: bool             # False se incerto
    screen_type: str           # "main" | "appraisal" | "unknown"
    confidence: float          # 0.0–1.0 (combinação das certezas)
    warnings: list[str]        # ex: ["Nome ambíguo: Nidoran♀/♂"]
```

---

## 6. Rotas da API

### `GET /scan/` — formulário de upload

- Requer login (`@login_required`)
- Template: `scan/index.html`
- Input: `<input type="file" accept="image/*" multiple capture="environment">`
  - `capture="environment"` abre a câmera traseira direto no celular
  - `multiple` permite selecionar vários prints de uma vez (até 10)

### `POST /scan/` — processar imagens

```
Request: multipart/form-data
  files[]: imagens (JPG/PNG/WebP, máx 10 MB cada, máx 10 arquivos)
  
Response (sucesso): redirect para /scan/preview com resultados na sessão
Response (erro):    flash + redirect de volta para /scan/
```

Lógica:
1. Validar arquivos (extensão, tamanho)
2. Chamar `ocr_service.process_images()`
3. Salvar `results` na sessão (como `store_import_session` do import_)
4. Redirecionar para preview

### `POST /scan/confirmar` — salvar os dados

```
Request: form com os campos editados pelo usuário
  result_<n>_species_id: int
  result_<n>_cp: int
  result_<n>_hp_max: int
  result_<n>_atk_iv: int
  result_<n>_def_iv: int
  result_<n>_sta_iv: int
  result_<n>_is_shiny: bool
  result_<n>_skip: bool        # usuário marcou "pular este"

Response: redirect para /collection/ com flash de resultado
```

Lógica por resultado não pulado:
1. Criar ou atualizar `UserPokemon` (source="scan")
   - `iv_pct = (atk_iv + def_iv + sta_iv) / 45 * 100`
2. Atualizar `UserCollection` do form correspondente:
   - `owned = True`, `quantity += 1`
   - Se `is_shiny`: `has_shiny = True`, `shiny_qty += 1`
   - Se `iv_pct == 100.0`: `has_perfect = True`

---

## 7. Template `scan/index.html`

Mobile-first. Seguir o visual dos templates existentes (Tailwind, dark mode).

```
┌─────────────────────────────────┐
│  Catalogar por Print            │
│                                 │
│  [Área de upload / drag-drop]   │
│  📷 Tirar foto  ou  📁 Galeria  │
│                                 │
│  Como tirar o print certo:      │
│  • Abra o Pokémon GO            │
│  • Toque no Pokémon             │
│  • Print na tela principal      │
│    — ou —                       │
│  • Toque em Avaliar (appraisal) │
│  • Print com os IVs visíveis    │
│                                 │
│  [Thumbnails dos arquivos       │
│   selecionados aparecendo aqui] │
│                                 │
│  [Botão: Analisar →]            │
└─────────────────────────────────┘
```

## 8. Template `scan/preview.html`

Um card por imagem analisada. Campos editáveis pelo usuário antes de
confirmar.

```
┌─────────────────────────────────┐
│  Print 1 de 3                   │
│  [thumbnail pequeno]            │
│                                 │
│  Pokémon: [Pikachu         ▼]  │  ← select com busca (autocomplete)
│  CP:      [1234              ]  │
│  HP máx:  [89                ]  │
│                                 │
│  IVs (appraisal):               │
│  Ataque:  [15 ] Defesa: [12 ]  │
│  PS:      [15 ]    = 93,3%      │
│                                 │
│  ✨ Brilhante: [ ] (marcar)     │
│                                 │
│  ⚠ Nome ambíguo: Nidoran        │
│    ○ Nidoran♀  ○ Nidoran♂      │
│                                 │
│  [Pular este]                   │
└─────────────────────────────────┘
   [Confirmar tudo →]
```

Indicador de confiança:
- `confidence >= 0.85` → card com borda verde (✓ verificado)
- `0.60 <= confidence < 0.85` → borda amarela (⚠ revisar)
- `confidence < 0.60` → borda vermelha (✗ verificação necessária)

---

## 9. Matching de nome — estratégia

O OCR vai retornar texto como "Pikachu", "Charizard", "Galarian Slowpoke"
ou variações com erros ("Pikach u", "CHARIZARD"). A correspondência usa
três passos em cascata:

```
1. Exato contra Species.name_pt (PT-BR) — case-insensitive
2. Exato contra Species.name (inglês) — para screenshots em EN
3. Fuzzy match (difflib.get_close_matches, cutoff=0.75) contra ambas listas
4. Sem match → raw_name retornado, species=None, usuário seleciona manualmente
```

A lista de nomes é carregada uma vez em memória (`_load_name_index()`)
e atualizada a cada restart. Não fazer query por Pokémon durante o OCR.

---

## 10. Detecção de shiny

IVs e CP são texto — OCR resolve direto. Shiny é mais difícil porque
o indicador é um ícone gráfico (estrela/brilho no canto). Abordagem:

1. Recortar o ROI do canto superior direito da área do nome
2. Verificar presença de pixels com saturação alta e matiz dourado
   (HSV: H ≈ 40–55°, S > 0.6, V > 0.7)
3. Se encontrar cluster com > 20 pixels na faixa → `is_shiny = True`
4. Confiança da detecção de shiny é sempre baixa (0.5) → mostrar
   checkbox para o usuário confirmar

Esta é uma heurística. Falsos negativos são aceitáveis (usuário marca
manualmente); falsos positivos seriam piores (marcar como shiny quando
não é).

---

## 11. Dependências novas

### `requirements.txt`

```
pytesseract>=0.3.10
```

`Pillow` já está instalado.

### `Dockerfile` (e `docker-compose.prod.yml`)

```dockerfile
RUN apt-get update && apt-get install -y \
    tesseract-ocr \
    tesseract-ocr-por \
    && rm -rf /var/lib/apt/lists/*
```

`tesseract-ocr-por` é o pacote de idioma PT-BR — necessário para
reconhecer nomes com acentos (Pokémon PT-BR do jogo).

### Variável de ambiente (opcional)

```env
TESSERACT_PATH=/usr/bin/tesseract   # default no Linux, só setar no Windows
```

---

## 12. Rate limit

A rota de upload deve ter rate limit mais restritivo que as demais
(OCR é CPU-intensivo):

```python
@limiter.limit("5 per minute; 30 per hour")
@bp.route("/", methods=["POST"])
```

---

## 13. Limitações conhecidas

| Situação | Comportamento | Mitigação |
|---|---|---|
| Screenshot cortada / parcial | `confidence < 0.4`, alerta ao usuário | Instruções visuais no index.html |
| Pokémon com acento no nome PT | OCR pode errar com Tesseract padrão | `tesseract-ocr-por` + pré-processamento |
| Tela em inglês | Name match tenta `Species.name` (inglês) | Funciona para maioria dos casos |
| Forma regional (ex: Alolan Raichu) | Nome pode vir como "Raichu" sem forma | Preview mostrará select para usuário escolher a forma |
| Resolução muito baixa (< 720p) | OCR de CP/IV pode falhar | Aviso de resolução mínima |
| Pokémon com nome ambíguo (Nidoran) | `warnings` inclui aviso + opções | Usuário seleciona no preview |
| Mais de 10 imagens enviadas | Flash de aviso, processa só as 10 primeiras | Limite no front com JS |
| IV não visível (Tela A sem appraisal) | `atk_iv=None`, campos IV ficam em branco | Usuário preenche ou deixa em branco |

---

## 14. Testes

### Fixtures necessárias

Criar em `tests/fixtures/scan/`:
- `pikachu_main.jpg` — tela principal, Pikachu, CP 1234, não shiny
- `pikachu_appraisal.jpg` — tela de appraisal, 15/12/15
- `charizard_shiny_main.jpg` — tela principal, Charizard brilhante
- `low_res_720p.jpg` — tela em baixa resolução
- `cropped_partial.jpg` — screenshot incompleta

### Casos de teste (`tests/test_ocr_service.py`)

```python
def test_extract_name_from_main_screen()
def test_extract_cp_from_main_screen()
def test_extract_hp_from_main_screen()
def test_extract_ivs_from_appraisal_screen()
def test_detect_shiny_positive()
def test_detect_shiny_negative()
def test_match_species_exact_pt()
def test_match_species_fuzzy_with_typo()
def test_match_species_nidoran_ambiguous()
def test_process_images_batch_3()
def test_process_images_unknown_screen()
def test_low_confidence_returns_warning()
```

### Testes de rota (`tests/test_scan_routes.py`)

```python
def test_upload_valid_image_redirects_to_preview()
def test_upload_invalid_extension_returns_error()
def test_upload_too_large_file_returns_error()
def test_confirmar_creates_user_pokemon()
def test_confirmar_updates_user_collection_shiny()
def test_confirmar_skip_does_not_save()
def test_rate_limit_after_5_requests()
```

---

## 15. Checklist de implementação

- [ ] `app/blueprints/scan/__init__.py`
- [ ] `app/blueprints/scan/routes.py`
- [ ] `app/services/ocr_service.py`
- [ ] `app/templates/scan/index.html`
- [ ] `app/templates/scan/preview.html`
- [ ] Registro do blueprint em `app/__init__.py`
- [ ] `requirements.txt` — adicionar `pytesseract>=0.3.10`
- [ ] `Dockerfile` — adicionar `tesseract-ocr tesseract-ocr-por`
- [ ] Link no menu de navegação (ao lado de "Catalogar")
- [ ] Migração Alembic — `UserPokemon.source` aceitar `"scan"` (enum)
- [ ] `tests/fixtures/scan/` — imagens de fixture
- [ ] `tests/test_ocr_service.py`
- [ ] `tests/test_scan_routes.py`
- [ ] BACKLOG.md — marcar #17-B como entregue

---

## 16. Referências

- pytesseract: https://github.com/madmaze/pytesseract
- Tesseract 5 PSM modes: https://tesseract-ocr.github.io/tessdoc/ImproveQuality
- Como CalcyIV faz OCR: análise do APK disponível no APKMirror
- Blueprint import_ existente: `app/blueprints/import_/routes.py` (padrão a seguir)
- UserPokemon model: `app/models/individual.py` (model alvo do salvamento)
