# deploy.ps1 — Empacota e envia MeuPokémonGO para casakek.duckdns.org
# Uso: .\deploy.ps1          (sem rebuild)
# Uso: .\deploy.ps1 -Build   (com rebuild da imagem Docker)

param([switch]$Build)

$Server  = "felipe@casakek.duckdns.org"
$Port    = "64622"
$Key     = "$env:USERPROFILE\.ssh\id_casakek"
$Remote  = "/home/felipe/sistemas/MEUPOKEMONGO"
$Archive = "meupokemongo.tar.gz"

$SshOpts = "-i `"$Key`" -p $Port -o StrictHostKeyChecking=no"

# ── 1. Criar pacote ──────────────────────────────────────────────────────────
Write-Host "[1/4] Empacotando projeto..." -ForegroundColor Cyan

$exclude = @(
    "--exclude=.env",
    "--exclude=__pycache__",
    "--exclude=*.pyc",
    "--exclude=*.pyo",
    "--exclude=.git",
    "--exclude=*.db",
    "--exclude=meupokemongo.tar.gz",
    "--exclude=.venv",
    "--exclude=venv"
)

& tar -czf $Archive $exclude -C .. MEUPOKEMONGO
if ($LASTEXITCODE -ne 0) { Write-Error "Falha ao criar tar"; exit 1 }

$sizeMB = [math]::Round((Get-Item $Archive).Length / 1MB, 2)
Write-Host "   Pacote criado: $Archive ($sizeMB MB)" -ForegroundColor Green

# ── 2. Enviar para o servidor ─────────────────────────────────────────────────
Write-Host "[2/4] Enviando para $Server..." -ForegroundColor Cyan

& scp -i "$Key" -P $Port -o StrictHostKeyChecking=no $Archive "${Server}:/tmp/${Archive}"
if ($LASTEXITCODE -ne 0) { Remove-Item $Archive -Force; Write-Error "Falha no SCP"; exit 1 }

Remove-Item $Archive -Force
Write-Host "   Enviado com sucesso." -ForegroundColor Green

# ── 3. Extrair e subir containers ────────────────────────────────────────────
Write-Host "[3/4] Extraindo e atualizando no servidor..." -ForegroundColor Cyan

$buildFlag = if ($Build) { "--build" } else { "" }

$remoteCmd = @"
set -e
mkdir -p /home/felipe/sistemas
cd /home/felipe/sistemas
tar -xzf /tmp/$Archive
rm /tmp/$Archive
cd MEUPOKEMONGO
docker-compose -f docker-compose.prod.yml up -d $buildFlag
echo '>>> Containers em execucao:'
docker-compose -f docker-compose.prod.yml ps
"@

& ssh -i "$Key" -p $Port -o StrictHostKeyChecking=no $Server $remoteCmd
if ($LASTEXITCODE -ne 0) { Write-Error "Falha no comando remoto"; exit 1 }

Write-Host ""
Write-Host "[4/4] Deploy concluido!" -ForegroundColor Green
Write-Host "      Acesse: http://casakek.duckdns.org:5001" -ForegroundColor Cyan
