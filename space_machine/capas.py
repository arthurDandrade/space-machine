"""Capas do painel: a thumbnail do vídeo ou um quadro tirado dos vídeos, para mostrar um vídeo (ou um bloco) num card.

Fonte, em ordem: a thumbnail que você enviou (<vídeo>/thumbnail.*), os blocos entregues (<vídeo>/edicao/bloco N.mp4),
a prévia mais nova de um bloco, e por fim a primeira imagem dos assets do bloco. De alguns instantes, fica o quadro com mais detalhe (o JPEG maior): os quadros
só com texto sobre o papel ficam pequenos e perdem para os que têm foto.
Guardadas em <dados>/cache/capas/<canal>/; refeitas quando a fonte muda.
"""
import hashlib
import json
import re
import shutil
import time
import subprocess
import tempfile
import threading
from pathlib import Path

from . import estado
from . import plataforma
from .sistema import DADOS

CACHE = DADOS / "cache" / "capas"
INSTANTES = (4, 9, 14, 19, 26)
# bloco: outros instantes, para a capa do bloco não repetir a do vídeo (que sai dos mesmos arquivos)
INSTANTES_BLOCO = (6, 12, 17, 23, 31)
_travas = {}
_trava_geral = threading.Lock()


def _ffmpeg():
    return plataforma.achar("ffmpeg") or "ffmpeg"


def _numero(f):
    m = re.search(r"(\d+)", f.stem)
    return int(m.group(1)) if m else 0


def _imagem_dos_assets(b):
    pasta = Path(b) / "assets"
    if not pasta.is_dir():
        return None
    imgs = sorted(f for f in pasta.rglob("*") if f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"))
    return imgs[0] if imgs else None


# ---------------- thumbnail do vídeo ----------------
THUMB_EXT = (".jpg", ".jpeg", ".png", ".webp")
LIMITE_YOUTUBE = 2 * 1024 * 1024          # o YouTube recusa thumbnail com mais de 2 MB


def thumbnail(video_dir):
    return next((f for ext in THUMB_EXT if (f := Path(video_dir) / f"thumbnail{ext}").exists()), None)


def _guardar_thumbnail(vd):
    """A thumbnail atual vai para <vídeo>/thumbnails_anteriores/ (trocar ou remover nunca apaga)."""
    t = thumbnail(vd)
    if t:
        guarda = vd / "thumbnails_anteriores"
        guarda.mkdir(exist_ok=True)
        t.rename(guarda / f"thumbnail_{time.strftime('%Y%m%d-%H%M%S', time.localtime(t.stat().st_mtime))}{t.suffix}")
    (vd / "thumbnail.json").unlink(missing_ok=True)


def salvar_thumbnail(video_dir, dados, nome):
    """Grava a imagem enviada como <vídeo>/thumbnail.<ext>. ValueError se não for uma imagem que abre."""
    from io import BytesIO
    from PIL import Image
    vd = Path(video_dir)
    ext = Path(nome or "").suffix.lower()
    if ext not in THUMB_EXT:
        raise ValueError("Envie uma imagem PNG, JPG ou WEBP.")
    try:
        with Image.open(BytesIO(dados)) as im:
            im.verify()
        with Image.open(BytesIO(dados)) as im:
            largura, altura = im.size
    except Exception:  # noqa: BLE001 — qualquer falha de leitura = não é imagem
        raise ValueError("Esse arquivo não é uma imagem que dê para abrir.")
    _guardar_thumbnail(vd)
    (vd / f"thumbnail{'.jpg' if ext == '.jpeg' else ext}").write_bytes(dados)
    (vd / "thumbnail.json").write_text(json.dumps({"nome": Path(nome).name, "largura": largura, "altura": altura,
                                                   "enviada": time.strftime("%Y-%m-%d %H:%M:%S")}, ensure_ascii=False))


def remover_thumbnail(video_dir):
    _guardar_thumbnail(Path(video_dir))


def info_thumbnail(video_dir):
    t = thumbnail(video_dir)
    if not t:
        return None
    try:
        info = json.loads((Path(video_dir) / "thumbnail.json").read_text())
    except (OSError, ValueError):
        info = {"nome": t.name}
    return {**info, "arquivo": str(t), "tamanho": t.stat().st_size, "versao": int(t.stat().st_mtime),
            "grande_demais": t.stat().st_size > LIMITE_YOUTUBE}


def fontes(video_dir, nn=None):
    """Thumbnail, vídeos ou uma imagem de onde sai a capa. Sem nn: o vídeo inteiro; com nn: só aquele bloco."""
    vd = Path(video_dir)
    if not nn and thumbnail(vd):
        return [thumbnail(vd)]
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
    # o nome leva a fonte: trocar ou remover a thumbnail muda a capa mesmo com a fonte nova mais velha que o cache
    marca = hashlib.md5("|".join(map(str, fs)).encode()).hexdigest()[:8]
    destino = CACHE / canal_slug / (f"{vd.name}_{nn}_{marca}.jpg" if nn else f"{vd.name}_{marca}.jpg")
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
