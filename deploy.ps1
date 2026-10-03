# deploy.ps1 - Deploy MeuPokemonGO (https://meupokemongo.duckdns.org) via git pull no servidor casakek
#
# Uso: .\deploy.ps1
#
# O docker-compose.prod.yml NAO monta volume: o codigo fica dentro da imagem.
# Por isso todo deploy faz build (rapido gracas ao cache de camadas do Docker),
# recria o container web, aplica migracoes Alembic e faz health check.

$Server = "felipe@casakek.duckdns.org"
$Port   = "64622"
$Key    = "$env:USERPROFILE\.ssh\id_casakek"
$Remote = "/home/felipe/sistemas/MEUPOKEMONGO"

# -- 0. Checagens locais ------------------------------------------------------
$dirty = git status --porcelain --untracked-files=no
if ($dirty) {
    Write-Warning "Ha alteracoes locais nao commitadas (nao vao para producao):"
    $dirty | ForEach-Object { Write-Host "   $_" }
}

# -- 1. Push local -> GitHub --------------------------------------------------
Write-Host "[1/4] Enviando commits para o GitHub..." -ForegroundColor Cyan
git push origin main
if ($LASTEXITCODE -ne 0) { Write-Error "Falha no git push"; exit 1 }
$localHead = (git rev-parse --short HEAD).Trim()
Write-Host "   GitHub atualizado ($localHead)." -ForegroundColor Green

# -- 2..4. Servidor: pull, build, recriar container, migrar, health check -----
$remoteCmd = @"
set -e
cd $Remote
W=meupokemongo_web_1

echo '[2/4] git pull + build da imagem (container antigo segue no ar)...'
git pull --ff-only origin main
docker-compose -f docker-compose.prod.yml build web

echo '[3/4] Recriando container web...'
# Container criado fora do compose (sem label) bloqueia o 'up' com conflito de nome
if docker inspect `$W >/dev/null 2>&1; then
  if [ -z "`$(docker inspect -f '{{index .Config.Labels "com.docker.compose.project"}}' `$W)" ]; then
    echo '   container sem label do compose - removendo'
    docker rm -f `$W
  fi
fi
docker-compose -f docker-compose.prod.yml up -d web

echo '[4/4] Migracoes + health check...'
for i in `$(seq 1 20); do
  docker exec `$W flask db current >/dev/null 2>&1 && break
  sleep 2
done
docker exec `$W flask db upgrade 2>&1 | grep -E 'Running upgrade|Error|error' || echo '   nenhuma migracao pendente'
echo "   alembic: `$(docker exec `$W flask db current 2>/dev/null | grep -oE '^[0-9a-f]{12}.*')"

for i in `$(seq 1 15); do
  code=`$(curl -s -o /dev/null -w '%{http_code}' http://localhost:5001/ || true)
  [ "`$code" = "200" ] && break
  sleep 2
done
echo "   health / -> HTTP `$code"
[ "`$code" = "200" ] || { docker logs --tail 40 `$W; exit 1; }
echo "   versao no servidor: `$(git rev-parse --short HEAD)"
"@

# Script vai via stdin (o PS 5.1 remove aspas de argumentos de exe nativo).
# Bash nao aceita CRLF nem BOM.
$OutputEncoding = New-Object System.Text.UTF8Encoding $false
$remoteCmd = $remoteCmd -replace "`r", ""
$remoteCmd | & ssh -i "$Key" -p $Port -o StrictHostKeyChecking=no $Server "bash -s"
if ($LASTEXITCODE -ne 0) { Write-Error "Falha no servidor remoto"; exit 1 }

Write-Host ""
Write-Host "Deploy concluido! ($localHead)" -ForegroundColor Green
Write-Host "   Acesse: https://meupokemongo.duckdns.org" -ForegroundColor Cyan
