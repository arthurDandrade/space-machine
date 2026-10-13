#!/bin/zsh
# Monta, renderiza e roda o QA de um bloco, em sequência (sem precisar olhar o After).
# Uso: motor/edicao_ae/editar_bloco.sh <pasta do bloco> <NN> [versao]   (SEM_QA=1 antes: só monta e renderiza)
#   ex.: motor/edicao_ae/editar_bloco.sh <dados>/canais/<canal>/producoes/<video>/blocos/03 03 1
# Ambiente: SM_PYTHON (Python do Space Machine; padrão: .venv do repo) e SM_AFTER (nome do app; padrão abaixo).
# Saída: <projeto>/edicao/previa_bloco_NN_vV.mp4 + qa_NN.md / qa_NN.jpg. Código 1 se o QA reprovar.
setopt pipefail
P=${1:A}; N=$2; V=${3:-1}
E=$P/edicao
cd ${0:A:h} || exit 1
PY=${SM_PYTHON:-../../.venv/bin/python}
AE=${SM_AFTER:-Adobe After Effects 2026}
# vídeo com pixel não quadrado (crop do ffmpeg sem setsar=1) sai esticado no After: corrige antes de montar
for f in $P/assets/**/*.mp4(N); do
  sar=$(ffprobe -v error -select_streams v:0 -show_entries stream=sample_aspect_ratio -of csv=p=0 $f)
  if [[ -n $sar && $sar != 1:1 && $sar != N/A && $sar != 0:1 ]]; then
    echo "SAR $sar -> 1:1: ${f:t}"
    ffmpeg -v error -y -i $f -vf setsar=1 -c:v libx264 -crf 17 -pix_fmt yuv420p -an $f.sar.mp4 && mv $f.sar.mp4 $f
  fi
done
$PY gerar_ae2.py $P --item $N | tail -1 || exit 1
rm -f $E/log_${N}_v2.txt
osascript -e 'with timeout of 1800 seconds' -e "tell application \"$AE\" to DoScriptFile \"$E/montar_${N}_v2.jsx\"" -e 'end timeout' >/dev/null
for i in {1..600}; do [ -f $E/log_${N}_v2.txt ] && break; sleep 3; done   # osascript estourou o tempo: espera o After
cat $E/log_${N}_v2.txt; echo
# sem "OK comp="a montagem não salvou: o render abriria o bloco_NN_v2.aep da versão anterior
grep -q '^OK comp=' $E/log_${N}_v2.txt 2>/dev/null || { echo "MONTAGEM FALHOU (sem 'OK comp=' no log): render cancelado"; exit 1; }
COMP=$(python3 -c "import json;print(json.load(open('$E/plano_edicao_$N.json'))['nome'])")
{ echo "var RENDER = {aep: \"$E/bloco_${N}_v2.aep\", comp: \"$COMP\", saida: \"$E/previa_bloco_${N}_v$V.mp4\", log: \"$E/log_render_${N}.txt\"};"; cat renderizar.jsx; } > $E/render_${N}.jsx
rm -f $E/log_render_${N}.txt
osascript -e 'with timeout of 3000 seconds' -e "tell application \"$AE\" to DoScriptFile \"$E/render_${N}.jsx\"" -e 'end timeout' >/dev/null
# o osascript pode estourar o tempo e o render continua; mas sem limite, After travado num diálogo segurava
# a trava do After (e a fila inteira) até o timeout de 3 h do rodar
for i in {1..1200}; do [ -f $E/log_render_${N}.txt ] && break; sleep 3; done
[ -f $E/log_render_${N}.txt ] || { echo "RENDER SEM RESPOSTA em 1 h (After travado num diálogo?)"; exit 1; }
cat $E/log_render_${N}.txt; echo
[[ -n $SEM_QA ]] && { echo "QA pulado (SEM_QA=1)"; exit 0; }
$PY qa/qa_bloco.py $P --item $N --video $E/previa_bloco_${N}_v$V.mp4 2>&1 | grep -E "Prévia|FALHA|ATENÇÃO|↳"
