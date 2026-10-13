# ADB Scan — Catalogação automática via USB

*Criado: 13/10/2026 — complementa a spec #17-B (`SPEC-OCR-SCAN.md`)*

---

## 1. O que é

O **ADB Scan** é um script Python que roda no PC e conecta no celular via USB.
Enquanto o usuário navega pelos Pokémon dentro do Pokémon GO, o script detecta
automaticamente a tela de detalhe de cada Pokémon, captura o screenshot via ADB e
envia para o servidor para processar com OCR.

O usuário não precisa tirar print manualmente. O fluxo é:

```
Pokémon GO (celular)  →  ADB (USB)  →  script no PC  →  /scan/adb (Flask)  →  OCR  →  session
                                              ↑                                           ↓
                                    notificação no celular                      /scan/preview
                                    + feedback no terminal                      (revisar + confirmar)
```

---

## 2. Diferenças em relação ao upload manual

| Aspecto | Upload manual | ADB automático |
|---|---|---|
| Como captura | Usuário tira print → faz upload | Script captura sozinho via ADB |
| Limite por sessão | 10 imagens por envio | Sem limite prático |
| Storage | Filesystem (`scan_temp/<key>/`) | Mesmo (acumula indefinidamente) |
| Feedback | Página de revisão | Terminal colorido + notificação no celular |
| Pré-requisito | Nenhum | ADB instalado, USB Debugging ativo |
| Indicado para | Catalogar 1–10 Pokémon | Catalogar coleção inteira (50–500+) |

---

## 3. Pré-requisitos

### No PC

**Python 3.9+** com as bibliotecas:
```
pip install Pillow requests
```

**Android Platform Tools** (contém o ADB):
- Download: https://developer.android.com/tools/releases/platform-tools
- Extrair e adicionar a pasta ao `PATH` do sistema

Verificar instalação:
```
adb version
# Android Debug Bridge version 1.0.41
```

### No celular (Android)

1. **Configurações** → **Sobre o telefone** → toque 7 vezes em **Número da versão**
   → aparece "Você é um desenvolvedor!"
2. Volte para **Configurações** → **Opções do desenvolvedor**
3. Ative **Depuração USB**
4. Conecte o cabo USB ao PC
5. Na janela que aparece no celular: **Permitir depuração USB** → marque
   "Sempre permitir deste computador" → **OK**

Verificar conexão:
```
adb devices
# List of devices attached
# ABC1234XYZ     device    ← deve aparecer "device", não "unauthorized"
```

---

## 4. Uso

### Sintaxe básica

```bash
python scripts/adb_scan.py \
  --url https://meupokemongo.duckdns.org \
  --user SEU_USUARIO \
  --password SUA_SENHA
```

### Todos os parâmetros

| Parâmetro | Padrão | Descrição |
|---|---|---|
| `--url` | `https://meupokemongo.duckdns.org` | URL do servidor |
| `--user` | obrigatório | Nome de usuário |
| `--password` | obrigatório | Senha |
| `--interval` | `1.8` | Segundos entre capturas (menor = mais rápido, mais CPU) |
| `--no-go-check` | falso | Não verifica se o GO está em foreground |

### Exemplos

```bash
# Básico
python scripts/adb_scan.py --url https://meupokemongo.duckdns.org --user felipe --password abc123

# Captura mais rápida (a cada 1.2s)
python scripts/adb_scan.py --url ... --user ... --password ... --interval 1.2

# Se o check de foreground travar (raro em alguns Android)
python scripts/adb_scan.py --url ... --user ... --password ... --no-go-check
```

### Fluxo de uso completo

```
1. Conecte o cabo USB
2. Abra o terminal e execute o script
3. Aguarde "Login ok" e "Aguardando Pokémon GO..."
4. Abra o Pokémon GO no celular
5. Navegue para a coleção de Pokémon
6. Abra o primeiro Pokémon (tela de detalhe)
7. O terminal exibe:  🟢 #001 Pikachu CP 1847 (conf 94%)
8. O celular recebe:  ✅ Pokémon capturado! — Pikachu · CP 1847
9. Vá para o próximo Pokémon
10. Repita até catalogar todos que quiser
11. Pressione Ctrl+C no terminal
12. Acesse /scan/preview para revisar e confirmar
```

### Output do terminal

```
🎮 ADB Scan — MeuPokémonGO
   📱 Dispositivo : R5CTA1XXXXX
   🌐 Servidor    : https://meupokemongo.duckdns.org
   ⏱️  Intervalo   : 1.8s

   Fazendo login como felipe... ✓

   Abra o Pokémon GO e navegue pelos seus Pokémon.
   Pressione Ctrl+C quando terminar.

🟢 #001 Pikachu CP 1847  (conf 97%)
🟢 #002 Charizard CP 3214  (conf 91%)
🟡 #003 Nidoran♀ CP 687  (conf 68%)
🔴 #004 ? CP ?  (conf 31%)
[001✓] Aguardando próximo Pokémon...
```

**Cores de confiança:**
- 🟢 ≥ 85% — nome e CP extraídos com alta certeza
- 🟡 60–84% — dados extraídos, mas revisar antes de confirmar
- 🔴 < 60% — OCR teve dificuldade; verificação necessária na revisão

---

## 5. Como a detecção de tela funciona

O script não usa OCR localmente — isso seria lento e exigiria Tesseract no PC.
Em vez disso, usa **heurísticas de pixel** para decidir se vale enviar a imagem
para o servidor:

### Passo 1 — Pokémon GO em foreground?

```bash
adb shell dumpsys window windows | grep "com.nianticlabs.pokemongo"
```

Se o pacote não aparecer, o script aguarda sem capturar. Evita processar
prints da galeria, WhatsApp, etc.

### Passo 2 — É uma nova tela?

Calcula um fingerprint da região central-alta (onde fica o nome do Pokémon):
- Crop de `(w/4, h*0.07)` até `(3w/4, h*0.20)`
- Reduz para 32×8 pixels
- MD5 do buffer de bytes

Se o fingerprint for igual ao da última captura: aguarda. Isso evita múltiplas
capturas do mesmo Pokémon enquanto o usuário ainda está olhando a tela.

### Passo 3 — Parece tela de detalhe do GO?

Dois critérios simultâneos:

```
Critério A — Topo saturado (gradiente de tipo):
  Crop: (0, 0, w, h*0.38)
  % de pixels com saturação HSV > 22% e valor > 60
  Threshold: > 12%

Critério B — Base clara (painel branco de stats):
  Crop: (0, h*0.55, w, h)
  % de pixels com R, G, B > 195
  Threshold: > 22%
```

A tela de detalhe do Pokémon GO tem sempre fundo colorido (tipo) no topo e
painel branco de stats na base. Telas de mapa, menus e batalhas não passam
nos dois critérios simultaneamente.

Se passar em ambos → envia para `/scan/adb` para OCR.

---

## 6. Endpoint `/scan/adb`

### Contrato

```
POST /scan/adb
Content-Type: multipart/form-data
Cookie: session=<flask_session>

file: screenshot.png (imagem PNG, máx 10 MB)
```

```json
// Resposta de sucesso
{
  "ok": true,
  "name": "Pikachu",
  "cp": 1847,
  "confidence": 0.94,
  "iv_pct": null,
  "total": 42
}

// Resposta: tela não reconhecida
{
  "ok": false,
  "reason": "tela não reconhecida",
  "confidence": 0.18
}
```

### Características

- **CSRF exempt**: o endpoint é programático (não vem de um formulário browser)
- **Autenticação**: via session cookie do Flask-Login (obtido pelo form-login no script)
- **Rate limit**: 60/min, 600/hora (mais generoso que o upload manual — capturas
  individuais são mais leves)
- **Storage**: resultado acumulado em `app/static/scan_temp/<key>/results.json`
  (filesystem, sem limite de sessão cookie)
- **Threshold de confiança**: `confidence < 0.20` → retorna `ok: false` e descarta
  localmente (tela de mapa, menus, etc. que passaram na heurística local)

### Acúmulo na sessão

O script mantém a sessão com `requests.Session`. O Flask armazena `scan_key`
no cookie de sessão. Cada POST ao `/scan/adb` acumula no mesmo arquivo
`results.json`. O usuário pode interromper o script e retomar depois — os
resultados ficam no servidor até confirmar ou descartar.

---

## 7. Storage no servidor

```
app/static/scan_temp/
└── <uuid_hex>/              ← criado no primeiro POST /scan/adb ou /scan/upload
    ├── results.json         ← lista de ScanResult.to_dict() acumulados
    ├── thumb_0.webp         ← thumbnail do 1º screenshot
    ├── thumb_1.webp
    └── ...
```

O diretório é excluído em dois momentos:
1. **Confirmar**: `/scan/confirmar` deleta após salvar no banco
2. **Descartar**: `/scan/limpar` deleta sem salvar

Diretórios órfãos (sessão expirada, browser fechado) ficam no disco.
Limpeza manual periódica com `find app/static/scan_temp -mtime +7 -delete`
ou futura tarefa de cron no deploy.

---

## 8. Login do script

O script simula um login via formulário (não usa API especial):

```python
# 1. GET /auth/login → extrai csrf_token do HTML
r = sess.get(f"{base_url}/auth/login")
csrf = re.search(r'name="csrf_token"\s+value="([^"]+)"', r.text).group(1)

# 2. POST /auth/login com credenciais
r = sess.post(f"{base_url}/auth/login",
              data={"username": u, "password": p, "csrf_token": csrf},
              allow_redirects=True)

# 3. requests.Session armazena o cookie automaticamente
# Todos os requests subsequentes da mesma Session são autenticados
```

Vantagem: não requer nenhum endpoint especial no servidor. Usa o mesmo
fluxo de login que o browser. O cookie dura enquanto a sessão Flask
não expirar (configurado para `PERMANENT_SESSION_LIFETIME` no config).

---

## 9. Notificação no celular

Após cada captura bem-sucedida:

```bash
adb shell cmd notification post \
  -S bigtext \
  -t "✅ Pokémon capturado!" \
  mpkm \
  "Pikachu · CP 1847"
```

- **`-S bigtext`**: estilo de notificação expandível
- **`-t`**: título
- **`mpkm`**: tag (substitui notificação anterior da mesma tag = não acumula)
- Requer Android 8+ (API 26+)
- Falha silenciosa se o Android não suportar ou ADB recusar

---

## 10. Limitações conhecidas

| Situação | Comportamento | Mitigação |
|---|---|---|
| Pokémon com fundo muito escuro (tipo Noturno/Fantasma) | Pode não passar no critério de saturação | Aumentar threshold no script ou usar `--no-go-check` e aceitar mais telas |
| Tela de batalha ou raid | Gradiente saturado — pode ser capturada erroneamente | OCR no servidor identifica pela ausência de nome/CP e retorna `confidence < 0.20` |
| Conexão USB instável | `screencap` retorna vazio | Script reporta erro e tenta novamente na próxima iteração |
| Sessão Flask expira durante a coleta | Servidor retorna 401 | Script encerra com mensagem clara; execute novamente para relogar |
| Screenshots em inglês (GO configurado em EN) | OCR tenta match por `Species.name` (inglês) | Funciona para a maioria; nomes muito diferentes podem falhar |
| Forma regional (ex: Alolan Raichu) | OCR pode ler "Raichu" sem a forma | Preview mostra select — usuário seleciona a forma correta |
| IVs só na tela de Appraisal | Tela principal não tem IVs | Abrir a tela de Appraisal para que o script capture também (duas capturas do mesmo Pokémon são mescladas pelo OCR) |
| Celular com notch/Dynamic Island | Pode cortar a região do nome | Ajustar ROIs em `ocr_service.py` se necessário |

---

## 11. Calibrando a heurística de detecção

Se o script estiver capturando muitas telas erradas ou perdendo Pokémon,
ajuste os thresholds em `scripts/adb_scan.py`:

```python
def is_pokemon_detail(img_bytes: bytes) -> bool:
    ...
    # Aumentar sat_ratio threshold → menos falsos positivos (mais seletivo)
    # Diminuir sat_ratio threshold → menos falsos negativos (mais sensível)
    return sat_ratio > 0.12 and bright_ratio > 0.22
    #                   ^^^^                   ^^^^
```

| Pokémons sendo perdidos | Muitas telas erradas capturadas |
|---|---|
| Diminuir `sat_ratio` (ex: `0.08`) | Aumentar `sat_ratio` (ex: `0.18`) |
| Diminuir `bright_ratio` (ex: `0.18`) | Aumentar `bright_ratio` (ex: `0.28`) |

Para depurar, salve os screenshots rejeitados:
```python
# Adicione temporariamente em is_pokemon_detail():
img.save(f"debug_{time.time():.0f}.png")
```

---

## 12. Arquitetura dos arquivos

```
scripts/
└── adb_scan.py              ← script desktop (roda no PC)

app/blueprints/scan/
├── __init__.py              ← define bp = Blueprint("scan", ...)
└── routes.py
    ├── GET  /scan/          ← index com tabs Manual/ADB + banner de pendentes
    ├── POST /scan/upload    ← upload manual de até 10 imagens
    ├── POST /scan/adb       ← recebe screenshot do script ADB (CSRF exempt)
    ├── POST /scan/limpar    ← descarta lote sem salvar
    ├── GET  /scan/preview   ← revisão dos resultados acumulados
    └── POST /scan/confirmar ← salva no banco e limpa o diretório

app/services/
└── ocr_service.py           ← pipeline OCR (pytesseract + Pillow, sem Flask)

app/static/scan_temp/
└── <uuid>/
    ├── results.json         ← acumulador de ScanResult.to_dict()
    └── thumb_N.webp         ← thumbnails das imagens processadas
```

---

## 13. Segurança

- O endpoint `/scan/adb` exige login (`@login_required`) — sem sessão válida retorna 401
- CSRF é dispensado explicitamente com `@csrf.exempt` porque o cliente é um script, não um browser
- Rate limit de 60/min previne abuso de OCR (processo CPU-intensivo)
- O diretório `scan_temp/` está no `.gitignore` — thumbnails não vão para o git
- Senhas são passadas via argumento de linha de comando; prefira variáveis de ambiente em scripts de CI:
  ```bash
  ADB_PASSWORD=suasenha python scripts/adb_scan.py --password "$ADB_PASSWORD" ...
  ```

---

## 14. Referências

- Script: `scripts/adb_scan.py`
- Endpoint: `app/blueprints/scan/routes.py` → `adb_upload()`
- OCR service: `app/services/ocr_service.py`
- Spec original (#17-B): `docs/SPEC-OCR-SCAN.md`
- Android Platform Tools: https://developer.android.com/tools/releases/platform-tools
- ADB screencap: https://developer.android.com/tools/adb#screencap
