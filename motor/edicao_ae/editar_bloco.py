"""Monta, renderiza e roda o QA de um bloco, em sequência (sem precisar olhar o After).

O mesmo passo a passo do editar_bloco.sh, em Python: é o que roda no Windows (o .sh continua sendo o do Mac).
Uso: python motor/edicao_ae/editar_bloco.py <pasta do bloco> <NN> [versao]   (SEM_QA=1 antes: só monta e renderiza)
A prévia sai em meia resolução (960x540): serve ao QA (que mede em 480x270) e para olhar; o vídeo final é renderizado
dos .aep dos blocos (space_machine/final.py). PREVIA_CHEIA=1 antes: prévia em 1920x1080.
Ambiente: SM_PYTHON (Python do Space Machine; padrão: este) e SM_AFTER (nome do app; padrão abaixo).
Saída: <projeto>/edicao/previa_bloco_NN_vV.mp4 + qa_NN.md / qa_NN.jpg. Código 1 se o QA reprovar.
"""
import json
import os
import re
import subprocess
import sys
from pathlib import Path

AQUI = Path(__file__).resolve().parent
sys.path.insert(0, str(AQUI.parent.parent))
from space_machine import plataforma  # noqa: E402


def corrigir_sar(pasta_assets):
    """Vídeo com pixel não quadrado (crop do ffmpeg sem setsar=1) sai esticado no After: corrige antes de montar."""
    for f in sorted(pasta_assets.rglob("*.mp4")):
        sar = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                              "stream=sample_aspect_ratio", "-of", "csv=p=0", str(f)],
                             capture_output=True, text=True).stdout.strip()
        if sar and sar not in ("1:1", "N/A", "0:1"):
            print(f"SAR {sar} -> 1:1: {f.name}", flush=True)
            tmp = f.with_name(f.name + ".sar.mp4")
            r = subprocess.run(["ffmpeg", "-v", "error", "-y", "-i", str(f), "-vf", "setsar=1", "-c:v", "libx264",
                                "-crf", "17", "-pix_fmt", "yuv420p", "-an", str(tmp)])
            if r.returncode == 0:
                tmp.replace(f)


def main():
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    p, n = Path(sys.argv[1]).resolve(), sys.argv[2]
    v = sys.argv[3] if len(sys.argv) > 3 else "1"
    e = p / "edicao"
    py = os.environ.get("SM_PYTHON") or sys.executable
    ae = os.environ.get("SM_AFTER") or "Adobe After Effects 2026"

    if (p / "assets").exists():
        corrigir_sar(p / "assets")

    r = subprocess.run([py, "gerar_ae2.py", str(p), "--item", n], cwd=AQUI, capture_output=True, text=True)
    saida = (r.stdout.strip().splitlines() or [""])[-1]
    print(saida, flush=True)
    if r.returncode:
        print(r.stderr, flush=True)
        return 1

    log_montar = e / f"log_{n}_v2.txt"
    log_montar.unlink(missing_ok=True)
    plataforma.rodar_jsx(ae, e / f"montar_{n}_v2.jsx", 1800)
    texto = plataforma.esperar_log(log_montar, 1800)
    print(texto + "\n", flush=True)
    # sem "OK comp=" a montagem não salvou: o render abriria o bloco_NN_v2.aep da versão anterior
    if not re.search(r"^OK comp=", texto, re.M):
        print("MONTAGEM FALHOU (sem 'OK comp=' no log): render cancelado", flush=True)
        return 1

    comp = json.loads((e / f"plano_edicao_{n}.json").read_text())["nome"]
    previa = e / f"previa_bloco_{n}_v{v}.mp4"
    log_render = e / f"log_render_{n}.txt"
    # json.dumps: caminho do Windows tem barra invertida, que solta dentro de uma string do .jsx vira escape
    render = {"aep": str(e / f"bloco_{n}_v2.aep"), "comp": comp, "saida": str(previa), "log": str(log_render),
              "meia": not os.environ.get("PREVIA_CHEIA")}
    (e / f"render_{n}.jsx").write_text(f"var RENDER = {json.dumps(render, ensure_ascii=False)};\n"
                                       + (AQUI / "renderizar.jsx").read_text())
    log_render.unlink(missing_ok=True)
    plataforma.rodar_jsx(ae, e / f"render_{n}.jsx", 3000)
    # sem limite, After travado num diálogo segurava a trava do After (e a fila inteira) até o timeout de 3 h do rodar
    texto = plataforma.esperar_log(log_render, 3600)
    if not texto and not log_render.exists():
        print("RENDER SEM RESPOSTA em 1 h (After travado num diálogo?)", flush=True)
        return 1
    print(texto + "\n", flush=True)

    if os.environ.get("SEM_QA"):
        print("QA pulado (SEM_QA=1)", flush=True)
        return 0
    r = subprocess.run([py, str(AQUI / "qa" / "qa_bloco.py"), str(p), "--item", n, "--video", str(previa)],
                       cwd=AQUI, capture_output=True, text=True)
    for linha in (r.stdout + r.stderr).splitlines():
        if re.search(r"Prévia|FALHA|↳", linha):
            print(linha, flush=True)
    return r.returncode


if __name__ == "__main__":
    sys.exit(main())
