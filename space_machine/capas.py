"""Capas do painel: um quadro tirado dos vídeos para mostrar um vídeo (ou um bloco) num card.

Fonte, em ordem: os blocos entregues (<vídeo>/edicao/bloco N.mp4), a prévia mais nova de um bloco, e por fim a
primeira imagem dos assets do bloco. De alguns instantes, fica o quadro com mais detalhe (o JPEG maior): os quadros
só com texto sobre o papel ficam pequenos e perdem para os que têm foto.
Guardadas em <dados>/cache/capas/<canal>/; refeitas quando a fonte muda.
"""
import re
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path

from . import estado
from .sistema import DADOS

CACHE = DADOS / "cache" / "capas"
INSTANTES = (4, 9, 14, 19, 26)
# bloco: outros instantes, para a capa do bloco não repetir a do vídeo (que sai dos mesmos arquivos)
INSTANTES_BLOCO = (6, 12, 17, 23, 31)
_travas = {}
_trava_geral = threading.Lock()


def _ffmpeg():
    return shutil.which("ffmpeg") or "/opt/homebrew/bin/ffmpeg"


def _numero(f):
    m = re.search(r"(\d+)", f.stem)
    return int(m.group(1)) if m else 0


def _imagem_dos_assets(b):
    pasta = Path(b) / "assets"
    if not pasta.is_dir():
        return None
    imgs = sorted(f for f in pasta.rglob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    return imgs[0] if imgs else None


def fontes(video_dir, nn=None):
    """Vídeos (ou uma imagem) de onde sai a capa. Sem nn: o vídeo inteiro; com nn: só aquele bloco."""
    vd = Path(video_dir)
    if nn:
        b = vd / "blocos" / nn
        entregue = vd / "edicao" / f"bloco {int(nn)}.mp4"
        pv = estado.previas(b) if b.is_dir() else []
        if pv:
            return [pv[-1]]
        if entregue.exists():
            return [entregue]
        img = _imagem_dos_assets(b)
        return [img] if img else []
    entregues = sorted((vd / "edicao").glob("bloco *.mp4"), key=_numero)
    sem_cold_open = [f for f in entregues if _numero(f) > 0]
    if sem_cold_open or entregues:
        return (sem_cold_open or entregues)[:2]
    blocos = sorted(p for p in (vd / "blocos").glob("*") if p.is_dir() and p.name.isdigit()) if (vd / "blocos").exists() else []
    for b in blocos:
        pv = estado.previas(b)
        if pv:
            return [pv[-1]]
    for b in blocos:
        img = _imagem_dos_assets(b)
        if img:
            return [img]
    return []


def _gerar(fontes_, destino, instantes_video=INSTANTES):
    with tempfile.TemporaryDirectory() as tmp:
        quadros = []
        for i, f in enumerate(fontes_):
            if f.suffix.lower() != ".mp4":
                instantes = (None,)
            else:
                instantes = instantes_video
            for j, t in enumerate(instantes):
                saida = Path(tmp) / f"{i}_{j}.jpg"
                cmd = [_ffmpeg(), "-loglevel", "error", "-y"] + (["-ss", str(t)] if t is not None else []) + \
                      ["-i", str(f), "-frames:v", "1", "-vf", "scale=640:-2", "-q:v", "5", str(saida)]
                subprocess.run(cmd, capture_output=True, timeout=30)
                if saida.exists() and saida.stat().st_size:
                    quadros.append(saida)
        if not quadros:
            return None
        melhor = max(quadros, key=lambda q: q.stat().st_size)
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp_destino = destino.with_suffix(".tmp.jpg")
        shutil.copyfile(melhor, tmp_destino)
        tmp_destino.replace(destino)
        return destino


def capa(canal_slug, video_dir, nn=None):
    """Caminho do JPEG da capa (gera ou refaz se a fonte for mais nova), ou None se não há de onde tirar."""
    vd = Path(video_dir)
    fs = fontes(vd, nn)
    if not fs:
        return None
    destino = CACHE / canal_slug / (f"{vd.name}_{nn}.jpg" if nn else f"{vd.name}.jpg")
    mais_nova = max(f.stat().st_mtime for f in fs)
    with _trava_geral:
        trava = _travas.setdefault(str(destino), threading.Lock())
    with trava:
        if destino.exists() and destino.stat().st_mtime >= mais_nova:
            return destino
        return _gerar(fs, destino, INSTANTES_BLOCO if nn else INSTANTES)


def banner(canal_slug, arquivo):
    """Banner do canal para o card. Arte de canal do YouTube (16:9, 2560×1440) tem margens enormes: o que aparece
    em toda tela é a faixa do meio (1546×423); o card usa essa faixa, com um pouco de folga em cima e embaixo.
    Banner em outro formato vai como está."""
    from PIL import Image
    arquivo = Path(arquivo)
    destino = CACHE / canal_slug / "_banner.jpg"
    if destino.exists() and destino.stat().st_mtime >= arquivo.stat().st_mtime:
        return destino
    with Image.open(arquivo) as im:
        w, h = im.size
        if abs(w / h - 16 / 9) < 0.05:
            cw, ch = w * 1546 / 2560, h * 560 / 1440
            im = im.crop((int((w - cw) / 2), int((h - ch) / 2), int((w + cw) / 2), int((h + ch) / 2)))
        im = im.convert("RGB")
        im.thumbnail((1400, 1400))
        destino.parent.mkdir(parents=True, exist_ok=True)
        tmp = destino.with_suffix(".tmp.jpg")
        im.save(tmp, "JPEG", quality=86)
        tmp.replace(destino)
    return destino
