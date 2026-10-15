#!/bin/zsh
# Instala o Space Machine neste Mac. Pode rodar de novo quando quiser: só faz o que falta.
#   ./instalar.sh
set -e
cd ${0:A:h}
echo "== Space Machine: instalação"
[[ $(uname) == Darwin ]] || { echo "O Space Machine roda só no macOS (o editor é o After Effects)."; exit 1; }
command -v brew >/dev/null || { echo "Falta o Homebrew. Instale em https://brew.sh e rode ./instalar.sh de novo."; exit 1; }

echo "-- ferramentas (Homebrew): ffmpeg, whisper-cpp, uv"
for p in ffmpeg whisper-cpp uv; do brew list $p >/dev/null 2>&1 || brew install $p; done

echo "-- Python (.venv)"
[[ -x .venv/bin/python ]] || uv venv -q -p 3.12 .venv
uv pip install -q -p .venv/bin/python -r requirements.txt

echo "-- painel (React, em painel/)"
command -v npm >/dev/null || brew install node
( cd painel && npm ci --no-audit --no-fund --loglevel=error && npm run build --silent >/dev/null ) && echo "ok: painel montado"

echo "-- modelo de transcrição (inglês)"
mkdir -p ~/.cache/whisper
baixar_modelo() { [[ -f ~/.cache/whisper/$1 ]] || curl -L --fail -o ~/.cache/whisper/$1 "https://huggingface.co/ggerganov/whisper.cpp/resolve/main/$1"; }
baixar_modelo ggml-small.en.bin
read "resp?Vai ter canal narrado em outro idioma além do inglês? [s/N] "
[[ $resp == [sS]* ]] && baixar_modelo ggml-small.bin

echo "-- pasta de dados (canais, produções, cache e chaves; fica fora do código)"
atual=$(cat ~/.config/spacemachine/dados 2>/dev/null || echo ~/SpaceMachine-dados)
read "dados?Pasta de dados [$atual]: "
dados=${dados:-$atual}; dados=${~dados}
mkdir -p $dados/canais ~/.config/spacemachine
echo $dados > ~/.config/spacemachine/dados
[[ -f $dados/.env ]] || { touch $dados/.env; chmod 600 $dados/.env; }

echo "-- Claude Code"
if command -v claude >/dev/null; then
  echo "ok: $(claude --version)"
else
  echo "Falta o Claude Code (precisa de uma assinatura do Claude):"
  echo "   npm install -g @anthropic-ai/claude-code"
fi

chmod +x spacemachine motor/edicao_ae/editar_bloco.sh
echo
echo "Pronto. Abra o painel com:  ./spacemachine"
echo "A página Primeiros passos mostra o que ainda falta (token do Claude, After Effects, chaves do canal)."
