"""Transcreve a narração com tempo por palavra.

Uso: python scripts/transcrever.py <projeto> [--audio narracao.wav]

Gera em <projeto>/_work/:
  palavras.json    [{"i": 0, "p": "Shoyu", "ini": 0.27, "fim": 0.68}, ...]
  transcricao.txt  uma frase por linha, cada palavra com seu tempo: [0.27]Shoyu [0.68]Ramen
"""
import argparse
import os
import re
import subprocess
import tempfile
from pathlib import Path

from comum import caminhos, config, gravar_json, log

EXT_AUDIO = (".wav", ".mp3", ".m4a", ".aac", ".flac", ".ogg", ".aiff", ".aif")


def achar_audio(projeto):
    for p in sorted(Path(projeto).iterdir()):
        if p.suffix.lower() in EXT_AUDIO and not p.name.startswith("_"):
            return p
    raise SystemExit("Nenhum arquivo de narração encontrado no projeto.")


def ts(s):
    h, m, rest = s.split(":")
    sec, ms = rest.split(",")
    return int(h) * 3600 + int(m) * 60 + int(sec) + int(ms) / 1000


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--audio")
    a = ap.parse_args()
    cfg = config()
    proj = Path(a.projeto)
    audio = Path(a.audio) if a.audio else achar_audio(proj)
    work = proj / "_work"
    work.mkdir(parents=True, exist_ok=True)

    with tempfile.TemporaryDirectory() as tmp:
        wav = Path(tmp) / "a.wav"
        subprocess.run(["ffmpeg", "-hide_banner", "-loglevel", "error", "-y", "-i", str(audio),
                        "-ar", "16000", "-ac", "1", str(wav)], check=True)
        saida = Path(tmp) / "w"
        log(f"Transcrevendo {audio.name} (pode levar alguns minutos)...")
        subprocess.run([caminhos.whisper_cli(cfg.get("whisper_cli")), "-m", os.path.expanduser(cfg["whisper_modelo"]),
                        "-f", str(wav), "-ml", "1", "-sow", "-osrt", "-of", str(saida),
                        "-t", str(os.cpu_count() or 4)],
                       check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        srt = (Path(str(saida) + ".srt")).read_text()

    palavras = []
    for bloco in re.split(r"\n\s*\n", srt.strip()):
        linhas = bloco.strip().split("\n")
        if len(linhas) < 3:
            continue
        ini, fim = [ts(x.strip()) for x in linhas[1].split("-->")]
        txt = " ".join(linhas[2:]).strip()
        if not txt or txt.startswith("["):
            continue
        palavras.append({"i": len(palavras), "p": txt, "ini": round(ini, 2), "fim": round(fim, 2)})
    gravar_json(work / "palavras.json", palavras)

    linhas, atual = [], []
    for w in palavras:
        atual.append(f"[{w['ini']:.2f}]{w['p']}")
        if re.search(r"[.!?]$", w["p"]):
            linhas.append(" ".join(atual))
            atual = []
    if atual:
        linhas.append(" ".join(atual))
    (work / "transcricao.txt").write_text("\n".join(linhas) + "\n")
    dur = palavras[-1]["fim"] if palavras else 0
    log(f"OK: {len(palavras)} palavras, {dur:.1f}s -> {work/'transcricao.txt'}")


if __name__ == "__main__":
    main()
