# Instala o Space Machine neste Windows (o mesmo que o instalar.sh faz no Mac). Pode rodar de novo quando quiser:
# só faz o que falta.
#   powershell -ExecutionPolicy Bypass -File .\instalar.ps1
# Sem perguntas (tudo pelos parâmetros, s ou n):
#   .\instalar.ps1 -Dados C:\SpaceMachine-dados -OutrosIdiomas n -Atalho s
param(
  [string] $Dados,
  [string] $OutrosIdiomas,
  [string] $Atalho
)
$ErrorActionPreference = 'Stop'
# a barra de progresso do Invoke-WebRequest do PowerShell 5.1 deixa o download dezenas de vezes mais lento
$ProgressPreference = 'SilentlyContinue'
Set-Location $PSScriptRoot
Write-Host '== Space Machine: instalação'
if ($env:OS -ne 'Windows_NT') { Write-Host 'Este instalador é o do Windows. No Mac, rode ./instalar.sh.'; exit 1 }
if (-not (Get-Command winget -ErrorAction SilentlyContinue)) {
  Write-Host 'Falta o winget (Instalador de Aplicativos da Microsoft Store). Instale e rode .\instalar.ps1 de novo.'; exit 1
}

function Recarregar-Path {
  $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';' + [Environment]::GetEnvironmentVariable('Path', 'User')
}
function Perguntar([string] $resposta, [string] $texto, [bool] $padrao) {
  if (-not $resposta) { $resposta = Read-Host "$texto [$(if ($padrao) { 'S/n' } else { 's/N' })]" }
  if (-not $resposta) { return $padrao }
  return $resposta -match '^[sSyY1]'
}

Write-Host '-- ferramentas (winget): Python 3.12, Node, ffmpeg, Git'
$programas = @(
  @{ cmd = 'python'; id = 'Python.Python.3.12' },
  @{ cmd = 'node';   id = 'OpenJS.NodeJS.LTS' },
  @{ cmd = 'ffmpeg'; id = 'Gyan.FFmpeg' },
  @{ cmd = 'git';    id = 'Git.Git' }
)
foreach ($p in $programas) {
  Recarregar-Path
  $achado = Get-Command $p.cmd -ErrorAction SilentlyContinue
  # o python.exe de WindowsApps é só um atalho para a Microsoft Store, não um Python
  if ($achado -and $achado.Source -notlike '*\WindowsApps\python.exe') { continue }
  winget install --id $p.id -e --source winget --accept-package-agreements --accept-source-agreements --disable-interactivity --scope user
}
Recarregar-Path

Write-Host '-- Python (.venv)'
if (-not (Test-Path .venv\Scripts\python.exe)) {
  $base = Get-ChildItem "$env:LOCALAPPDATA\Programs\Python\Python312\python.exe", "$env:ProgramFiles\Python312\python.exe" -ErrorAction SilentlyContinue | Select-Object -First 1
  $base = if ($base) { $base.FullName } else { 'python' }
  & $base -m venv .venv
}
.\.venv\Scripts\python.exe -m pip install -q --upgrade pip
.\.venv\Scripts\python.exe -m pip install -q -r requirements.txt
if ($LASTEXITCODE) { Write-Host 'O pip não conseguiu instalar as dependências (veja o erro acima).'; exit 1 }

Write-Host '-- painel (React, em painel\)'
Push-Location painel
try {
  cmd /c 'npm ci --no-audit --no-fund --loglevel=error'
  cmd /c 'npm run build --silent' | Out-Null
  if ($LASTEXITCODE) { Write-Host 'Não consegui montar o painel (rode: cd painel; npm run build).' } else { Write-Host 'ok: painel montado' }
} finally { Pop-Location }

Write-Host '-- transcrição (whisper.cpp) e modelo em inglês'
$cacheWhisper = Join-Path $HOME '.cache\whisper'
$binWhisper = Join-Path $cacheWhisper 'bin'
New-Item -ItemType Directory -Force $binWhisper | Out-Null
if (-not (Test-Path (Join-Path $binWhisper 'whisper-cli.exe'))) {
  # as versões "vX.Y.Z" saem sem binário; os builds "bNNNN" trazem o whisper-bin-x64.zip
  $rel = Invoke-RestMethod -UseBasicParsing 'https://api.github.com/repos/ggml-org/whisper.cpp/releases?per_page=15'
  $zipUrl = $rel | ForEach-Object { $_.assets } | Where-Object name -eq 'whisper-bin-x64.zip' |
    Select-Object -First 1 -ExpandProperty browser_download_url
  if (-not $zipUrl) { Write-Host 'Não achei o whisper-bin-x64.zip nas versões do whisper.cpp no GitHub.'; exit 1 }
  $tmp = Join-Path $env:TEMP "whisper-$([guid]::NewGuid())"
  New-Item -ItemType Directory $tmp | Out-Null
  Invoke-WebRequest -UseBasicParsing $zipUrl -OutFile (Join-Path $tmp 'w.zip')
  Expand-Archive (Join-Path $tmp 'w.zip') (Join-Path $tmp 'x')
  $cli = Get-ChildItem (Join-Path $tmp 'x') -Recurse -Filter whisper-cli.exe | Select-Object -First 1
  Copy-Item (Join-Path $cli.DirectoryName '*') $binWhisper -Recurse -Force
  Remove-Item $tmp -Recurse -Force
}
Write-Host "ok: $(Join-Path $binWhisper 'whisper-cli.exe')"
function Baixar-Modelo([string] $nome) {
  $alvo = Join-Path $cacheWhisper $nome
  if (-not (Test-Path $alvo)) {
    # curl.exe vem com o Windows 10/11 e mostra o progresso (o modelo tem ~470 MB)
    curl.exe -L --fail -o "$alvo.part" "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$nome"
    if ($LASTEXITCODE) { Write-Host "Não consegui baixar $nome."; exit 1 }
    Move-Item -Force "$alvo.part" $alvo
  }
}
Baixar-Modelo 'ggml-small.en.bin'
if (Perguntar $OutrosIdiomas 'Vai ter canal narrado em outro idioma além do inglês?' $false) { Baixar-Modelo 'ggml-small.bin' }

Write-Host '-- pasta de dados (canais, produções, cache e chaves; fica fora do código)'
$apontador = Join-Path $HOME '.config\spacemachine\dados'
$atual = if (Test-Path $apontador) { (Get-Content $apontador -Raw).Trim() } else { Join-Path $HOME 'SpaceMachine-dados' }
if (-not $Dados) { $Dados = Read-Host "Pasta de dados [$atual]"; if (-not $Dados) { $Dados = $atual } }
New-Item -ItemType Directory -Force (Join-Path $Dados 'canais'), (Split-Path $apontador) | Out-Null
[IO.File]::WriteAllText($apontador, $Dados)
$envDados = Join-Path $Dados '.env'
if (-not (Test-Path $envDados)) { New-Item -ItemType File $envDados | Out-Null }

Write-Host '-- Claude Code'
Recarregar-Path
if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
  cmd /c 'npm install -g @anthropic-ai/claude-code --no-audit --no-fund --loglevel=error'
  Recarregar-Path
}
if (Get-Command claude -ErrorAction SilentlyContinue) { Write-Host "ok: $(cmd /c 'claude --version')" }
else { Write-Host 'Falta o Claude Code (precisa de uma assinatura do Claude): npm install -g @anthropic-ai/claude-code' }

Write-Host '-- atalho na área de trabalho'
if (Perguntar $Atalho 'Criar o atalho Space Machine na área de trabalho?' $true) { .\.venv\Scripts\python.exe -X utf8 -m space_machine atalho }
Write-Host ''
Write-Host 'Pronto. Abra o painel com:  .\spacemachine.cmd   (ou o atalho na área de trabalho)'
Write-Host 'Token do Claude:  claude.cmd setup-token   (o claude sozinho cai na política de scripts do PowerShell)'
Write-Host 'A página Primeiros passos mostra o que ainda falta (token do Claude, After Effects, chaves do canal).'
