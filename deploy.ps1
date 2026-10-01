# deploy.ps1 — Deploy MeuPokémonGO para casakek.duckdns.org via git pull
# Uso: .\deploy.ps1          (sem rebuild — só atualiza código)
# Uso: .\deploy.ps1 -Build   (com rebuild da imagem Docker)

param([switch]$Build)

$Server = "felipe@casakek.duckdns.org"
$Port   = "64622"
$Key    = "$env:USERPROFILE\.ssh\id_casakek"
$Remote = "/home/felipe/sistemas/MEUPOKEMONGO"

$buildFlag = if ($Build) { "--build" } else { "" }

# ── 1. Push local → GitHub ───────────────────────────────────────────────────
Write-Host "[1/3] Enviando commits para o GitHub..." -ForegroundColor Cyan
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Error "Falha no git push"; exit 1 }
Write-Host "   GitHub atualizado." -ForegroundColor Green

# ── 2. Servidor puxa do GitHub e sobe containers ─────────────────────────────
Write-Host "[2/3] Atualizando servidor e containers..." -ForegroundColor Cyan

$remoteCmd = @"
set -e
cd $Remote
git pull origin main
docker compose -f docker-compose.prod.yml up -d $buildFlag
echo '>>> Containers em execucao:'
docker compose -f docker-compose.prod.yml ps
"@

& ssh -i "$Key" -p $Port -o StrictHostKeyChecking=no $Server $remoteCmd
if ($LASTEXITCODE -ne 0) { Write-Error "Falha no servidor remoto"; exit 1 }

Write-Host ""
Write-Host "[3/3] Deploy concluido!" -ForegroundColor Green
Write-Host "      Acesse: http://casakek.duckdns.org:5001" -ForegroundColor Cyan
