"""O vídeo inteiro como um projeto só (fluxo "video" do explained, 2026-11-05).

Antes cada tópico do roteiro era um bloco com storyboard, busca, escolha, edição no After, prévia e entrega próprios,
e o vídeo final juntava os blocos. Cada bloco era pensado sozinho, então o vídeo saía repetitivo (todo bloco com a
mesma cara). Agora os tópicos são CAPÍTULOS: a narração e a transcrição continuam por capítulo (<vídeo>/blocos/NN/,
para refazer só a voz de um), e daí em diante tudo é do vídeo inteiro, em <vídeo>/producao/ — uma pasta com a mesma
cara da de um bloco, então o motor (compilar_cenas, storyboard.py, buscar, escolher, gerar_ae2, qa_bloco) roda nela
do mesmo jeito:

  narracao.wav            as narrações dos capítulos emendadas (0,2 s antes da 1ª palavra, 0,6 s depois da última)
  roteiro.txt             os roteiros dos capítulos, em ordem
  _work/palavras.json     as palavras de todos os capítulos, no tempo do áudio junto
  _work/transcricao.txt   idem, com "## Capítulo NN: Nome" antes de cada capítulo
  capitulos.json          [{"nn", "nome", "tipo": "cold_open" | "capitulo" | "mudo", "ini", "fim"}] (s no áudio junto)
  cenas.json              o storyboard do vídeo inteiro: um item por capítulo (id = NN)
  edicao/                 plano_edicao_NN / plano_render_NN de cada capítulo, os pedaços renderizados e o QA

O vídeo pronto é um MP4 só (final/final.mp4); por dentro, cada capítulo é renderizado à parte e em paralelo (e só é
renderizado de novo se mudou), e o FFmpeg emenda sem recomprimir.
"""
import json
import re
import subprocess
from pathlib import Path

from .canal import gravar_json, ler_json

CABECA, RABO = 0.2, 0.6          # s de áudio antes da 1ª e depois da última palavra de cada capítulo
MARCA_COLD_OPEN = "#! cold open"
MARCA_CAPITULO = "#! capítulo"


def pasta(vd):
    return Path(vd) / "producao"


def fluxo_video(vd):
    """O vídeo nasceu no fluxo novo (estudio_video.json › fluxo = "video")? Os outros seguem bloco a bloco."""
    return (ler_json(Path(vd) / "estudio_video.json", {}) or {}).get("fluxo") == "video"


def capitulos(vd):
    """As pastas dos capítulos (<vídeo>/blocos/NN), em ordem."""
    b = Path(vd) / "blocos"
    return sorted(p for p in b.iterdir() if p.is_dir() and p.name.isdigit()) if b.is_dir() else []


def _tipo(roteiro):
    if MARCA_COLD_OPEN in roteiro:
        return "cold_open"
    if MARCA_CAPITULO in roteiro:
        return "mudo"
    return "capitulo"


def _nome(roteiro, nn):
    return next((l.lstrip("# ").strip() for l in roteiro.splitlines() if l.startswith("# ")), f"Capítulo {nn}")


def _duracao(arq):
    r = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", str(arq)],
                       capture_output=True, text=True)
    return float(r.stdout.strip() or 0)


def _narracao(b):
    return next((p for p in sorted(b.glob("narracao.*")) if p.stem == "narracao"), None)


def faltam(vd):
    """Capítulos sem narração ou sem transcrição: [(nn, o que falta)]."""
    out = []
    for b in capitulos(vd):
        if not _narracao(b):
            out.append((b.name, "narração"))
        elif not (b / "_work" / "palavras.json").exists():
            out.append((b.name, "transcrição"))
    return out


def atualizado(vd):
    """O projeto do vídeo já tem o áudio e as palavras de todos os capítulos, mais novos que eles?"""
    p = pasta(vd) / "capitulos.json"
    if not p.exists() or not (pasta(vd) / "narracao.wav").exists():
        return False
    juntos = [c["nn"] for c in ler_json(p, [])]
    caps = capitulos(vd)
    if juntos != [b.name for b in caps]:
        return False
    feito = p.stat().st_mtime
    for b in caps:
        for f in (_narracao(b), b / "_work" / "palavras.json", b / "roteiro.txt"):
            if f is None or not f.exists() or f.stat().st_mtime > feito:
                return False
    return True


def juntar(vd):
    """Emenda as narrações e as transcrições dos capítulos em <vídeo>/producao/. Devolve os capítulos (capitulos.json).
    ValueError com o motivo se faltar narração ou transcrição de algum."""
    vd = Path(vd)
    falta = faltam(vd)
    if falta:
        raise ValueError("falta " + ", ".join(f"{o} do capítulo {nn}" for nn, o in falta))
    destino = pasta(vd)
    (destino / "_work").mkdir(parents=True, exist_ok=True)
    caps, palavras, transc, roteiros, entradas, filtros = [], [], [], [], [], []
    t = 0.0
    for k, b in enumerate(capitulos(vd)):
        pal = ler_json(b / "_work" / "palavras.json", []) or []
        if not pal:
            raise ValueError(f"a transcrição do capítulo {b.name} está vazia")
        audio = _narracao(b)
        dur = _duracao(audio)
        a, f = max(0.0, pal[0]["ini"] - CABECA), min(dur, pal[-1]["fim"] + RABO)
        desloc = t - a
        for w in pal:
            palavras.append({"i": len(palavras), "p": w["p"], "ini": round(w["ini"] + desloc, 2),
                             "fim": round(w["fim"] + desloc, 2)})
        roteiro = (b / "roteiro.txt").read_text()
        nome = _nome(roteiro, b.name)
        caps.append({"nn": b.name, "nome": nome, "tipo": _tipo(roteiro), "ini": round(t, 3),
                     "fim": round(t + f - a, 3)})
        tx = (b / "_work" / "transcricao.txt").read_text() if (b / "_work" / "transcricao.txt").exists() else ""
        tx = re.sub(r"\[(\d+(?:\.\d+)?)\]", lambda m: f"[{float(m.group(1)) + desloc:.2f}]", tx.strip())
        transc.append(f"## Capítulo {b.name}: {nome}\n{tx}")
        roteiros.append(roteiro.strip())
        entradas += ["-i", str(audio)]
        filtros.append(f"[{k}:a]aresample=48000,aformat=channel_layouts=mono,atrim={a:.3f}:{f:.3f},"
                       f"asetpts=PTS-STARTPTS[a{k}]")
        t += f - a
    n = len(caps)
    grafo = ";".join(filtros) + ";" + "".join(f"[a{k}]" for k in range(n)) + f"concat=n={n}:v=0:a=1[s]"
    wav = destino / "narracao.wav"
    r = subprocess.run(["ffmpeg", "-v", "error", "-y"] + entradas + ["-filter_complex", grafo, "-map", "[s]",
                       "-c:a", "pcm_s16le", str(wav)], capture_output=True, text=True)
    if r.returncode:
        raise ValueError(f"não consegui emendar as narrações: {r.stderr.strip()[-300:]}")
    gravar_json(destino / "_work" / "palavras.json", palavras)
    (destino / "_work" / "transcricao.txt").write_text("\n\n".join(transc) + "\n")
    (destino / "roteiro.txt").write_text("\n\n".join(roteiros) + "\n")
    gravar_json(destino / "capitulos.json", caps)
    return caps
