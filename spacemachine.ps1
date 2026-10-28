# Atalho do Space Machine no Windows (o mesmo que o ./spacemachine faz no Mac).
#   .\spacemachine.ps1                 abre o painel (http://localhost:8765) no navegador, preso a este terminal
#   .\spacemachine.ps1 abrir           igual, mas sem prender o terminal: se o painel já está ligado só abre o navegador,
#                                      senão liga em segundo plano (log em <dados>\logs\painel.log). É o que o atalho usa.
#   .\spacemachine.ps1 <comando> ...   qualquer comando de `python -m space_machine` (rodar, fila, checar, consumo...)
# Do Prompt de Comando, o spacemachine.cmd chama este arquivo.
Set-Location $PSScriptRoot
$py = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (-not (Test-Path $py)) { Write-Host 'Rode .\instalar.ps1 primeiro.'; exit 1 }
# o Space Machine é todo UTF-8 (acento nos prompts e no canal.json); o Python do Windows usa cp1252 se ninguém disser
$env:PYTHONUTF8 = '1'

# monta o painel React (painel\ -> space_machine\static\app\) quando o código dele mudou, ex.: depois de um git pull
function Montar-Painel {
  $saida = 'space_machine\static\app\index.html'
  if (Test-Path $saida) {
    $quando = (Get-Item $saida).LastWriteTime
    $mudou = Get-ChildItem painel\src, painel\index.html, painel\package.json -Recurse -File -ErrorAction SilentlyContinue |
      Where-Object { $_.LastWriteTime -gt $quando } | Select-Object -First 1
    if (-not $mudou) { return }
  }
  if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
    Write-Host 'Falta o Node para montar o painel: winget install OpenJS.NodeJS.LTS'; return
  }
  Write-Host 'Montando o painel...'
  Push-Location painel
  try {
    $marca = 'node_modules\.package-lock.json'
    if (-not (Test-Path $marca) -or (Get-Item package-lock.json).LastWriteTime -gt (Get-Item $marca).LastWriteTime) {
      cmd /c 'npm ci --no-audit --no-fund --loglevel=error'
    }
    cmd /c 'npm run build --silent' | Out-Null
    if ($LASTEXITCODE) { Write-Host 'Não consegui montar o painel (rode: cd painel; npm run build).' }
  } finally { Pop-Location }
}

function Painel-Ligado {
  try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 1 'http://127.0.0.1:8765/api/sistema' | Out-Null; $true }
  catch { $false }
}

function Pasta-Dados {
  if ($env:SM_DADOS) { return $env:SM_DADOS }
  $apontador = Join-Path $HOME '.config\spacemachine\dados'
  if (Test-Path $apontador) { return (Get-Content $apontador -Raw).Trim() }
  return (Join-Path $HOME 'SpaceMachine-dados')
}

$cmd = if ($args.Count) { $args[0] } else { '' }

if ($cmd -eq 'abrir') {
  if (-not (Painel-Ligado)) {
    Montar-Painel
    $logs = Join-Path (Pasta-Dados) 'logs'
    New-Item -ItemType Directory -Force $logs | Out-Null
    $log = Join-Path $logs 'painel.log'
    # console escondido (e não pythonw): o ffmpeg, o whisper e o claude que o painel chama herdam esse console e não
    # piscam uma janela a cada chamada
    Start-Process cmd -WindowStyle Hidden -WorkingDirectory $PSScriptRoot `
      -ArgumentList ('/c ""' + $py + '" -X utf8 -m space_machine painel >> "' + $log + '" 2>&1"')
    for ($i = 0; $i -lt 60; $i++) { if (Painel-Ligado) { break }; Start-Sleep -Milliseconds 250 }
  }
  Start-Process 'http://localhost:8765'
  exit 0
}

if ($cmd -eq '' -or $cmd -eq 'painel') {
  $resto = if ($args.Count -gt 1) { $args[1..($args.Count - 1)] } else { @() }
  Montar-Painel
  Start-Process powershell -WindowStyle Hidden -ArgumentList '-NoProfile', '-Command', 'Start-Sleep 2; Start-Process http://localhost:8765'
  & $py -X utf8 -m space_machine painel @resto
  exit $LASTEXITCODE
}

& $py -X utf8 -m space_machine @args
exit $LASTEXITCODE
