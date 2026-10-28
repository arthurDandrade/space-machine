"""Funções compartilhadas pelos scripts do buscador de assets."""
import hashlib
import io
import json
import os
import re
import sys
import time
import unicodedata
from pathlib import Path

import requests
from PIL import Image, ImageDraw, ImageFont, ImageOps

RAIZ = Path(__file__).resolve().parent.parent          # motor/busca (config padrão, dados/)
sys.path.insert(0, str(RAIZ.parent))
import caminhos  # noqa: E402  (motor/caminhos.py: canal, dados, cache, chaves)
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/128.0 Safari/537.36")

sessao = requests.Session()
sessao.headers.update({"User-Agent": UA})


def config():
    """Config padrão do motor com canal.json["busca"] do canal por cima."""
    return caminhos.config_busca()


def ler_json(caminho, padrao=None):
    p = Path(caminho)
    if not p.exists():
        return padrao
    return json.loads(p.read_text())


def gravar_json(caminho, dados):
    p = Path(caminho)
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(p.suffix + ".tmp")
    tmp.write_text(json.dumps(dados, ensure_ascii=False, indent=2))
    tmp.replace(p)


def slug(texto, maximo=40):
    t = unicodedata.normalize("NFKD", str(texto)).encode("ascii", "ignore").decode()
    t = re.sub(r"[^a-zA-Z0-9]+", "-", t).strip("-").lower()
    return t[:maximo] or "x"


def log(*a):
    print(*a, file=sys.stderr, flush=True)


def iter_assets(plano):
    """Percorre (item, cena, asset) do plano."""
    for item in plano.get("itens", []):
        if item.get("titulo_asset"):
            yield item, None, item["titulo_asset"]
        for cena in item.get("cenas", []):
            for asset in cena.get("assets", []):
                yield item, cena, asset


def dominio_bloqueado(url, cfg):
    u = (url or "").lower()
    return any(d in u for d in cfg["dominios_bloqueados"])


def limpar_cache(dias_img=30, dias_busca=30):
    """Apaga do _cache/ as imagens baixadas há mais de 30 dias e buscas vencidas (quadros do YouTube ficam)."""
    agora = time.time()
    for sub, dias in (("img", dias_img), ("busca", dias_busca)):
        for f in (caminhos.cache() / sub).glob("*"):
            try:
                if agora - f.stat().st_mtime > dias * 86400:
                    f.unlink()
            except OSError:
                pass


def baixar_imagem(url, destino_sem_ext, lado_minimo, max_mb=30):
    """Baixa e valida uma imagem. Retorna (caminho, largura, altura) ou None.
    Cache por URL (2026-10-10) em _cache/img/: a mesma imagem em outro asset/bloco não baixa de novo;
    URL que falhou fica marcada por 7 dias."""
    cache = caminhos.cache() / "img" / hashlib.sha1(url.encode()).hexdigest()
    falhou = cache.with_suffix(".falhou")
    if falhou.exists() and time.time() - falhou.stat().st_mtime < 7 * 86400:
        return None
    try:
        if cache.exists():
            dados = cache.read_bytes()
        else:
            r = sessao.get(url, timeout=(8, 25), stream=True)
            if r.status_code != 200:
                if r.status_code in (403, 404, 410):
                    falhou.parent.mkdir(parents=True, exist_ok=True)
                    falhou.touch()
                return None
            dados = b""
            for parte in r.iter_content(1 << 16):
                dados += parte
                if len(dados) > max_mb * 1024 * 1024:
                    return None
        im = Image.open(io.BytesIO(dados))
        if not cache.exists():
            cache.parent.mkdir(parents=True, exist_ok=True)
            cache.write_bytes(dados)
        im.load()
    except Exception:
        return None
    w, h = im.size
    if min(w, h) < lado_minimo:
        return None
    tem_alpha = im.mode in ("RGBA", "LA", "P") and _tem_transparencia(im)
    if tem_alpha:
        caminho = Path(str(destino_sem_ext) + ".png")
        im.convert("RGBA").save(caminho)
    else:
        caminho = Path(str(destino_sem_ext) + ".jpg")
        im = ImageOps.exif_transpose(im).convert("RGB")
        im.save(caminho, quality=93)
    return caminho, w, h


def _tem_transparencia(im):
    try:
        a = im.convert("RGBA").getchannel("A")
        lo, _ = a.getextrema()
        return lo < 250
    except Exception:
        return False


def phash(caminho):
    """Hash perceptual simples (dHash 8x8) para descartar duplicatas."""
    im = Image.open(caminho).convert("L").resize((9, 8), Image.LANCZOS)
    px = list(im.getdata())
    bits = 0
    for y in range(8):
        for x in range(8):
            bits = (bits << 1) | (px[y * 9 + x] > px[y * 9 + x + 1])
    return bits


def distancia_hash(a, b):
    return bin(a ^ b).count("1")


def fonte_pil(tamanho):
    for f in (caminhos.fonte_sistema("Arial Bold.ttf"),
              "/System/Library/Fonts/Helvetica.ttc"):
        if os.path.exists(f):
            try:
                return ImageFont.truetype(f, tamanho)
            except Exception:
                pass
    return ImageFont.load_default(size=tamanho)


def folha_contato(itens, destino, colunas=4, celula=(420, 300), titulo=None):
    """itens: lista de (caminho_imagem_ou_PIL, rotulo). Gera uma grade numerada."""
    if not itens:
        return None
    cw, ch = celula
    rot_h = 34
    topo = 50 if titulo else 0
    linhas = (len(itens) + colunas - 1) // colunas
    folha = Image.new("RGB", (colunas * cw, topo + linhas * (ch + rot_h)), (235, 235, 235))
    d = ImageDraw.Draw(folha)
    f_rot, f_tit = fonte_pil(20), fonte_pil(26)
    if titulo:
        d.text((12, 10), titulo[:140], fill=(0, 0, 0), font=f_tit)
    for i, (img, rotulo) in enumerate(itens):
        x = (i % colunas) * cw
        y = topo + (i // colunas) * (ch + rot_h)
        try:
            im = img if isinstance(img, Image.Image) else Image.open(img)
            if im.mode in ("RGBA", "LA", "P"):
                base = Image.new("RGBA", im.size, (200, 200, 200, 255))
                xadrez = ImageDraw.Draw(base)
                q = max(8, im.size[0] // 30)
                for yy in range(0, im.size[1], q):
                    for xx in range(0, im.size[0], q):
                        if (xx // q + yy // q) % 2:
                            xadrez.rectangle([xx, yy, xx + q, yy + q], fill=(160, 160, 160, 255))
                base.alpha_composite(im.convert("RGBA"))
                im = base
            im = im.convert("RGB")
            im.thumbnail((cw - 8, ch - 8))
            folha.paste(im, (x + (cw - im.size[0]) // 2, y + (ch - im.size[1]) // 2))
        except Exception:
            d.text((x + 10, y + 10), "erro ao abrir", fill=(200, 0, 0), font=f_rot)
        d.rectangle([x, y + ch, x + cw, y + ch + rot_h], fill=(20, 20, 20))
        d.text((x + 8, y + ch + 6), rotulo[:46], fill=(255, 230, 0), font=f_rot)
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    folha.save(destino, quality=88)
    return destino


def pausa(seg):
    time.sleep(seg)


def hash_url(url):
    return hashlib.md5(url.encode()).hexdigest()[:10]
