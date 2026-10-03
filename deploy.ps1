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
# docker-compose 1.29.2 + Docker Engine novo quebra no 'recreate' (KeyError 'ContainerConfig')
# e deixa o servico fora do ar. Por isso: remove e cria do zero (inclui container manual
# sem label do compose e restos '<hash>_meupokemongo_web_1' de recreate que falhou).
for c in `$(docker ps -a --format '{{.Names}}' | grep -E '(^|_)meupokemongo_web_1$'); do
  docker rm -f `$c >/dev/null && echo "   removido `$c"
done
docker-compose -f docker-compose.prod.yml up -d --no-deps web

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

# Script vai por arquivo + redirecionamento do cmd: o PS 5.1 remove aspas de argumentos
# de exe nativo e poe BOM no pipe (o bash ignoraria o 'set -e'). Bash nao aceita CRLF.
$TempDir = "D:\.ClaudeCode\.temp"
New-Item -ItemType Directory -Force $TempDir | Out-Null
$ScriptFile = Join-Path $TempDir "deploy_meupokemongo.sh"
[IO.File]::WriteAllText($ScriptFile, ($remoteCmd -replace "`r", ""), (New-Object System.Text.UTF8Encoding $false))
cmd /c "ssh -i `"$Key`" -p $Port -o StrictHostKeyChecking=no $Server `"bash -s`" < `"$ScriptFile`""
$sshExit = $LASTEXITCODE
Remove-Item $ScriptFile -Force -ErrorAction SilentlyContinue
if ($sshExit -ne 0) { Write-Error "Falha no servidor remoto"; exit 1 }

Write-Host ""
Write-Host "Deploy concluido! ($localHead)" -ForegroundColor Green
Write-Host "   Acesse: https://meupokemongo.duckdns.org" -ForegroundColor Cyan
