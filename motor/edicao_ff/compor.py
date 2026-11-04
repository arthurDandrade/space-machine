"""Compositor sem After Effects: lê o plano de camadas que o gerador do formato escreve (edicao/plano_render_NN.json, as
mesmas layers que o montar_modelo.jsx recebia como DADOS), desenha cada quadro em Python (numpy + OpenCV + PIL) e o
FFmpeg decodifica os vídeos de banco, põe a narração e codifica o MP4.

Uso: python compor.py <projeto> --item NN --saida <arquivo.mp4> [--meia]
  --meia  960×540 (prévia de rascunho para o QA, ~4x mais rápida); sem ele, 1920×1080.

O que ele entende (o mesmo que o modelo do After fazia, 2026-11-04):
  - layers "null" (pais: a câmera, o carimbo, o documento), "solid" (com degradê e vinheta), "shape" (retângulo,
    elipse e linha; preenchimento e traço com opacidade; traço que se desenha; arco; tracejado), "footage" (imagem
    ou vídeo; tinta, brilho e borda de luz; ondulação; desfoque; sombra) e "text" (fonte do macOS, espaçamento entre
    letras, encolhe para caber em max_w, alinhamento e âncora como no After);
  - pai, âncora, posição, escala (negativa = espelhado), rotação e opacidade, com chaves lineares ou com ease;
  - as expressões que os geradores usam (oscilação, partículas, sonar, estrelas), avaliadas a cada quadro;
  - mesclagem normal, "add" e "screen".
O que ficou de fora: borrão de movimento.
"""
import argparse
import json
import math
import subprocess
import sys
import time as relogio
from pathlib import Path

import cv2
import numpy as np
from PIL import Image, ImageDraw, ImageFont

PASTAS_FONTES = ["/System/Library/Fonts", "/System/Library/Fonts/Supplemental", "/Library/Fonts",
                 str(Path.home() / "Library" / "Fonts")]
_FONTES = {}


# ---------------- fontes ----------------
def _sem_espaco(s):
    return s.replace(" ", "").replace("-", "").lower()


def fonte(nome_ps, tam):
    """Fonte pelo nome PostScript que o After usa ("AvenirNext-Bold", "Baskerville-SemiBold")."""
    if not _FONTES:
        for d in PASTAS_FONTES:
            for f in list(Path(d).glob("*.ttc")) + list(Path(d).glob("*.ttf")) + list(Path(d).glob("*.otf")):
                for i in range(20):
                    try:
                        fam, est = ImageFont.truetype(str(f), 10, index=i).getname()
                    except Exception:
                        break
                    _FONTES.setdefault(_sem_espaco(fam) + "|" + _sem_espaco(est), (str(f), i))
    fam, _, est = nome_ps.partition("-")
    chave = _sem_espaco(fam) + "|" + _sem_espaco(est or "Regular")
    arq, idx = _FONTES.get(chave) or _FONTES.get(_sem_espaco(fam) + "|regular") or \
        next(iter(_FONTES.values()))
    return ImageFont.truetype(arq, max(1, int(round(tam))), index=idx)


# ---------------- chaves e expressões ----------------
def _bezier_y(u, x1, x2):
    """Curva de tempo do ease (x1/x2 = influência de saída e de entrada, 0–1): acha t com x(t)=u e devolve y(t)."""
    lo, hi = 0.0, 1.0
    for _ in range(30):
        t = (lo + hi) / 2
        x = 3 * (1 - t) ** 2 * t * x1 + 3 * (1 - t) * t ** 2 * (1 - x2) + t ** 3
        lo, hi = (t, hi) if x < u else (lo, t)
    t = (lo + hi) / 2
    return 3 * (1 - t) * t ** 2 + t ** 3


def valor(keys, t, linear=False):
    """Valor de uma propriedade com chaves [[t, v, ease?]] no tempo t (antes da 1ª = 1ª; depois da última = última)."""
    if t <= keys[0][0]:
        return np.asarray(keys[0][1], float)
    if t >= keys[-1][0]:
        return np.asarray(keys[-1][1], float)
    for k in range(len(keys) - 1):
        a, b = keys[k], keys[k + 1]
        if a[0] <= t <= b[0]:
            u = (t - a[0]) / max(1e-9, b[0] - a[0])
            ea, eb = (a[2] if len(a) > 2 else None), (b[2] if len(b) > 2 else None)
            if not linear and (ea or eb):
                x1 = (ea[3] / 100) if ea else 0.0
                x2 = (eb[1] / 100) if eb else 0.0
                u = _bezier_y(u, min(1, x1), min(1, x2))
            va, vb = np.asarray(a[1], float), np.asarray(b[1], float)
            return va + (vb - va) * u
    return np.asarray(keys[-1][1], float)


class _Math:
    sin, cos, abs, min, max, floor, sqrt = math.sin, math.cos, abs, min, max, math.floor, math.sqrt
    PI = math.pi


def expressao(js, t, v):
    """As expressões curtas dos geradores (JavaScript do After) avaliadas em Python: "value + [0, 9*Math.sin(...)]",
    "var f = (time*0.45 + 0.25) % 1; [f*100, f*100]"."""
    ns = {"Math": _Math, "time": t, "value": v, "f": 0.0}
    partes = [p.strip() for p in js.split(";") if p.strip()]
    for p in partes[:-1]:
        nome, _, expr = p.replace("var ", "", 1).partition("=")
        ns[nome.strip()] = eval(expr, {"__builtins__": {}}, ns)
    r = eval(partes[-1], {"__builtins__": {}}, ns)
    return np.asarray(r, float)


def _seg(d, campo_keys, campo_fixo, padrao, t, linear=False, expr=None):
    if d.get(campo_keys):
        v = valor(d[campo_keys], t, linear)
    elif d.get(campo_fixo) is not None:
        v = np.asarray(d[campo_fixo], float)
    else:
        v = np.asarray(padrao, float)
    if expr:
        v = expressao(expr, t, v)
    return v


# ---------------- desenho das camadas ----------------
def _premult(rgba):
    out = rgba.copy()
    out[..., :3] *= out[..., 3:4]
    return out


def _desfocar(rgba, sigma):
    """Desfoque gaussiano com margem (a imagem cresce 3σ de cada lado). Devolve (imagem, margem)."""
    m = int(math.ceil(sigma * 3))
    p = cv2.copyMakeBorder(rgba, m, m, m, m, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    pm = _premult(p)
    pm = cv2.GaussianBlur(pm, (0, 0), sigma)
    a = pm[..., 3:4]
    out = np.zeros_like(pm)
    out[..., :3] = np.where(a > 1e-4, pm[..., :3] / np.maximum(a, 1e-4), 0)
    out[..., 3:4] = a
    return out, m


def _sombra(rgba, o):
    """Sombra projetada (After: op 0–255, direção em graus, 0 = para cima, distância, suavidade)."""
    sig = max(0.5, o.get("soft", 10) / 2.5)
    m = int(math.ceil(sig * 3 + o.get("dist", 0)))
    p = cv2.copyMakeBorder(rgba, m, m, m, m, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
    a = cv2.GaussianBlur(p[..., 3], (0, 0), sig) * (o.get("op", 128) / 255)
    th = math.radians(o.get("dir", 135))
    dx, dy = o.get("dist", 0) * math.sin(th), -o.get("dist", 0) * math.cos(th)
    a = cv2.warpAffine(a, np.float32([[1, 0, dx], [0, 1, dy]]), (a.shape[1], a.shape[0]))
    base = np.zeros_like(p)
    base[..., 3] = a
    # a imagem por cima da sombra
    al = p[..., 3:4]
    base[..., :3] = p[..., :3] * al
    base[..., 3:4] = al + a[..., None] * (1 - al)
    base[..., :3] = np.where(base[..., 3:4] > 1e-4, base[..., :3] / np.maximum(base[..., 3:4], 1e-4), 0)
    return base, m


def _grade(rgba, g):
    """A criatura dentro da água: tinta (preto/branco do fundo), brilho e borda de luz vinda de cima à esquerda."""
    out = rgba.copy()
    if g.get("tint"):
        preto, branco, quanto = np.asarray(g["tint"][0], np.float32), np.asarray(g["tint"][1], np.float32), g["tint"][2] / 100
        lum = (0.299 * out[..., 0] + 0.587 * out[..., 1] + 0.114 * out[..., 2])[..., None]
        tingida = preto + (branco - preto) * lum
        out[..., :3] = out[..., :3] * (1 - quanto) + tingida * quanto
    if g.get("brilho"):
        out[..., :3] = np.clip(out[..., :3] + g["brilho"] / 255 * 1.6, 0, 1)
    if g.get("borda"):
        esp, cor, inten = g["borda"][0], np.asarray(g["borda"][1], np.float32), g["borda"][2]
        a = out[..., 3]
        d = max(1, int(round(esp)))
        sombra_a = cv2.warpAffine(a, np.float32([[1, 0, d], [0, 1, d]]), (a.shape[1], a.shape[0]))
        luz = np.clip(a - sombra_a, 0, 1)
        luz = cv2.GaussianBlur(luz, (0, 0), max(0.6, esp / 2))[..., None] * a[..., None]
        out[..., :3] = out[..., :3] + (cor - out[..., :3]) * luz * inten
        escuro_a = cv2.warpAffine(a, np.float32([[1, 0, -d], [0, 1, -d]]), (a.shape[1], a.shape[0]))
        esc = cv2.GaussianBlur(np.clip(a - escuro_a, 0, 1), (0, 0), max(0.6, esp / 2))[..., None] * a[..., None]
        out[..., :3] = out[..., :3] * (1 - esc * inten * 0.5)
    return np.clip(out, 0, 1)


def _texto(d):
    """Texto como o modelo do After: tamanho, encolhe para caber em max_w, espaçamento, linhas com \\r, alinhamento.
    Devolve (rgba, âncora em px da imagem)."""
    tam = float(d.get("size") or 100)
    linhas = str(d["text"]).split("\r")

    def medir(tam_):
        f = fonte(d["font"], tam_)
        esp = (d.get("tracking") or 0) / 1000 * tam_
        larg = [sum(f.getlength(ch) + esp for ch in ln) - (esp if ln else 0) for ln in linhas]
        return f, esp, larg

    f, esp, larg = medir(tam)
    if d.get("max_w") and max(larg) > d["max_w"]:
        tam = tam * d["max_w"] / max(larg)
        f, esp, larg = medir(tam)
    lead = tam * 1.15
    asc, desc = f.getmetrics()
    m = int(tam * 0.5)
    W_, H_ = int(max(larg)) + 2 * m, int(lead * (len(linhas) - 1) + asc + desc) + 2 * m
    im = Image.new("L", (max(1, W_), max(1, H_)), 0)
    dr = ImageDraw.Draw(im)
    for k, ln in enumerate(linhas):
        x = m + {"left": 0, "right": max(larg) - larg[k]}.get(d.get("justify"), (max(larg) - larg[k]) / 2)
        y = m + k * lead
        for ch in ln:
            dr.text((x, y), ch, font=f, fill=255)
            x += f.getlength(ch) + esp
    a = np.asarray(im, np.float32) / 255
    rgba = np.zeros(a.shape + (4,), np.float32)
    rgba[..., :3] = np.asarray(d["color"][:3], np.float32)
    rgba[..., 3] = a
    ys, xs = np.nonzero(a > 0.02)
    if len(xs):
        x0, x1, y0, y1 = xs.min(), xs.max(), ys.min(), ys.max()
    else:
        x0 = x1 = y0 = y1 = 0
    ax = {"left": x0, "right": x1}.get(d.get("justify"), (x0 + x1) / 2)
    ay = {"top": y0, "bottom": y1}.get(d.get("anchor_mode"), (y0 + y1) / 2)
    return rgba, [ax, ay]


def _comprimento(pts):
    return sum(math.dist(pts[i], pts[i + 1]) for i in range(len(pts) - 1))


def _parcial(pts, frac):
    """Os primeiros `frac` (0–1) do comprimento de uma linha (o traço que se desenha)."""
    total, alvo, out = _comprimento(pts), None, [pts[0]]
    alvo = total * frac
    andado = 0
    for i in range(len(pts) - 1):
        seg = math.dist(pts[i], pts[i + 1])
        if andado + seg >= alvo:
            r = (alvo - andado) / seg if seg else 0
            out.append([pts[i][0] + (pts[i + 1][0] - pts[i][0]) * r, pts[i][1] + (pts[i + 1][1] - pts[i][1]) * r])
            return out
        andado += seg
        out.append(pts[i + 1])
    return out


def _elipse_pts(c, rx, ry, ini=0.0, fim=1.0, n=180):
    """Pontos da elipse do After: começa no alto (12 h) e vai no sentido horário; ini/fim em fração."""
    k = max(2, int(n * (fim - ini)))
    return [[c[0] + rx * math.sin(2 * math.pi * (ini + (fim - ini) * j / k)),
             c[1] - ry * math.cos(2 * math.pi * (ini + (fim - ini) * j / k))] for j in range(k + 1)]


def _forma(d, trim_frac=None):
    """Rasteriza as formas da layer (2× e reduz: bordas suaves). Devolve (rgba, âncora = origem da layer)."""
    itens = d["items"]
    xs, ys = [], []
    for it in itens:
        o = it.get("pos") or [0, 0]
        sw = it.get("sw", 0) if it.get("stroke") else 0
        if it["t"] in ("rect", "ellipse"):
            w, h = it["size"]
            xs += [o[0] - w / 2 - sw, o[0] + w / 2 + sw]
            ys += [o[1] - h / 2 - sw, o[1] + h / 2 + sw]
        else:
            xs += [p[0] for p in it["pts"]]
            ys += [p[1] for p in it["pts"]]
            xs += [min(xs) - sw, max(xs) + sw]
            ys += [min(ys) - sw, max(ys) + sw]
    x0, y0 = math.floor(min(xs)) - 4, math.floor(min(ys)) - 4
    x1, y1 = math.ceil(max(xs)) + 4, math.ceil(max(ys)) + 4
    S = 2
    Wd, Hd = max(1, (x1 - x0) * S), max(1, (y1 - y0) * S)
    acc = np.zeros((Hd // S if Hd // S else 1, Wd // S if Wd // S else 1, 4), np.float32)
    P = lambda p: (((p[0] - x0) * S), ((p[1] - y0) * S))
    for it in itens:
        im = Image.new("RGBA", (Wd, Hd), (0, 0, 0, 0))
        dr = ImageDraw.Draw(im)
        o = it.get("pos") or [0, 0]
        cor = lambda c, op: tuple(int(round(v * 255)) for v in c[:3]) + (int(round(2.55 * (100 if op is None else op))),)
        fr = 1.0 if (trim_frac is None or it.get("trim") is False) else max(0.0, min(1.0, trim_frac))
        if it["t"] == "rect":
            w, h = it["size"]
            box = [P([o[0] - w / 2, o[1] - h / 2]), P([o[0] + w / 2, o[1] + h / 2])]
            r = (it.get("radius") or 0) * S
            if it.get("fill"):
                dr.rounded_rectangle(box, r, fill=cor(it["fill"], it.get("fill_op")))
            if it.get("stroke"):
                dr.rounded_rectangle(box, r, outline=cor(it["stroke"], it.get("stroke_op")), width=int(it.get("sw", 2) * S))
        elif it["t"] == "ellipse" and not it.get("arco") and not it.get("tracejado") and fr >= 1:
            w, h = it["size"]
            box = [P([o[0] - w / 2, o[1] - h / 2]), P([o[0] + w / 2, o[1] + h / 2])]
            if it.get("fill"):
                dr.ellipse(box, fill=cor(it["fill"], it.get("fill_op")))
            if it.get("stroke"):
                dr.ellipse(box, outline=cor(it["stroke"], it.get("stroke_op")), width=int(it.get("sw", 2) * S))
        else:
            if it["t"] == "ellipse":
                ini, fim = ((it["arco"][0] / 100, it["arco"][1] / 100) if it.get("arco") else (0.0, 1.0))
                pts = _elipse_pts(o, it["size"][0] / 2, it["size"][1] / 2, ini, fim)
                fechado = not it.get("arco")
            else:
                pts = [[p[0] + o[0], p[1] + o[1]] for p in it["pts"]]
                fechado = bool(it.get("closed"))
            if fr < 1:
                pts = _parcial(pts, fr)
                fechado = False
            if len(pts) < 2:
                continue
            if it.get("fill") and fechado:
                dr.polygon([P(p) for p in pts], fill=cor(it["fill"], it.get("fill_op")))
            if it.get("stroke"):
                c = cor(it["stroke"], it.get("stroke_op"))
                larg = max(1, int(it.get("sw", 2) * S))
                if it.get("tracejado"):
                    traco, vao = it["tracejado"][0] * S, it["tracejado"][1] * S
                    seq = [P(p) for p in pts]
                    andado, desenha, ac = 0.0, True, [seq[0]]
                    for i in range(len(seq) - 1):
                        ac.append(seq[i + 1])
                        andado += math.dist(seq[i], seq[i + 1])
                        if andado >= (traco if desenha else vao):
                            if desenha:
                                dr.line(ac, fill=c, width=larg)
                            desenha, andado, ac = not desenha, 0.0, [seq[i + 1]]
                    if desenha and len(ac) > 1:
                        dr.line(ac, fill=c, width=larg)
                else:
                    seq = [P(p) for p in pts] + ([P(pts[0])] if fechado else [])
                    dr.line(seq, fill=c, width=larg, joint="curve")
                    r = larg / 2       # pontas arredondadas, como o "Line Cap" redondo do modelo
                    for q in (seq[0], seq[-1]):
                        dr.ellipse([q[0] - r, q[1] - r, q[0] + r, q[1] + r], fill=c)
        arr = np.asarray(im.resize((Wd // S or 1, Hd // S or 1), Image.LANCZOS), np.float32) / 255
        a = arr[..., 3:4]
        acc[..., :3] = arr[..., :3] * a + acc[..., :3] * (1 - a)
        acc[..., 3:4] = a + acc[..., 3:4] * (1 - a)
    acc[..., :3] = np.where(acc[..., 3:4] > 1e-4, acc[..., :3] / np.maximum(acc[..., 3:4], 1e-4), 0)
    return acc, [-x0, -y0]


def _solido(d, W, H):
    rgba = np.zeros((H, W, 4), np.float32)
    rgba[..., :3] = np.asarray(d["color"][:3], np.float32)
    rgba[..., 3] = 1
    if d.get("ramp"):
        (x0, y0), c0, (x1, y1), c1 = d["ramp"][0], d["ramp"][1], d["ramp"][2], d["ramp"][3]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        vx, vy = x1 - x0, y1 - y0
        u = np.clip(((xx - x0) * vx + (yy - y0) * vy) / max(1e-6, vx * vx + vy * vy), 0, 1)[..., None]
        rgba[..., :3] = np.asarray(c0[:3], np.float32) * (1 - u) + np.asarray(c1[:3], np.float32) * u
    if d.get("vinheta"):
        rx, ry, pena = d["vinheta"]
        yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
        dist = np.sqrt(((xx - W / 2) / rx) ** 2 + ((yy - H / 2) / ry) ** 2)
        dentro = np.clip((1 - dist) * min(rx, ry) / pena + 0.5, 0, 1)
        rgba[..., 3] = 1 - dentro
    return rgba, [W / 2, H / 2]


class Video:
    """Um vídeo de banco lido quadro a quadro pelo FFmpeg, no fps da comp; segura o último quadro quando acaba."""

    def __init__(self, arq, w, h, fps):
        self.w, self.h = int(w), int(h)
        self.p = subprocess.Popen(["ffmpeg", "-v", "error", "-i", str(arq), "-vf", f"fps={fps},scale={self.w}:{self.h}",
                                   "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], stdout=subprocess.PIPE)
        self.idx, self.atual = -1, np.zeros((self.h, self.w, 3), np.uint8)

    def quadro(self, k):
        while self.idx < k:
            b = self.p.stdout.read(self.w * self.h * 3)
            if len(b) < self.w * self.h * 3:
                break
            self.atual = np.frombuffer(b, np.uint8).reshape(self.h, self.w, 3)
            self.idx += 1
        return self.atual

    def fechar(self):
        try:
            self.p.kill()
        except Exception:
            pass


# ---------------- a comp ----------------
def _matriz(pos, anc, esc, rot):
    """Camada → pai: T(pos) · R(rot) · S(esc) · T(−âncora), em 3×3."""
    c, s = math.cos(math.radians(rot)), math.sin(math.radians(rot))
    sx, sy = esc[0] / 100, esc[1] / 100
    return np.array([[c * sx, -s * sy, pos[0] - (c * sx * anc[0] - s * sy * anc[1])],
                     [s * sx, c * sy, pos[1] - (s * sx * anc[0] + c * sy * anc[1])],
                     [0, 0, 1]], np.float64)


class Comp:
    def __init__(self, dados, escala=1.0):
        self.d = dados
        self.W, self.H = int(dados["w"] * escala), int(dados["h"] * escala)
        self.esc = escala
        self.fps = dados["fps"]
        self.layers = dados["layers"]
        self.por_id = {L["id"]: L for L in self.layers}
        self.cache, self.videos, self._prep = {}, {}, {}

    def transf(self, L, t, memo):
        """Matriz camada → comp no tempo t (pais incluídos)."""
        if L["id"] in memo:
            return memo[L["id"]]
        ex = L.get("expr") or {}
        tipo = L["kind"]
        pos = _seg(L, "pos_keys", "pos", [self.d["w"] / 2, self.d["h"] / 2], t, expr=ex.get("pos"))
        esc = _seg(L, "scale_keys", "scale", [100, 100], t, L.get("linear_scale"), ex.get("scale"))
        if esc.ndim == 0:
            esc = np.array([esc, esc])
        rot = float(_seg(L, "rot_keys", "rot", 0, t, expr=ex.get("rot")))
        if L.get("anchor") is not None:
            anc = L["anchor"]
        elif tipo == "null":
            anc = [0, 0]
        else:                       # forma: a origem da layer dentro da imagem desenhada; footage/texto: o centro/âncora
            anc = self.base(L, t)[1]
        M = _matriz(pos[:2], anc, esc[:2], rot)
        if L.get("parent") is not None and L["parent"] in self.por_id:
            M = self.transf(self.por_id[L["parent"]], t, memo) @ M
        memo[L["id"]] = M
        return M

    def base(self, L, t):
        """(rgba, âncora) da camada sem as transformações. Fica em cache, menos o que muda com o tempo (vídeo,
        traço que se desenha, ondulação)."""
        i = L["id"]
        if L["kind"] == "footage" and Path(L["file"]).suffix.lower() in (".mp4", ".mov", ".m4v", ".webm"):
            v = self.videos.get(i)
            if v is None:
                v = self.videos[i] = Video(L["file"], L["src"][0], L["src"][1], self.fps)
            lt = t - L.get("start", 0)
            fr = v.quadro(max(0, int(lt * self.fps)))
            rgba = np.ones((v.h, v.w, 4), np.float32)
            rgba[..., :3] = fr.astype(np.float32) / 255
            return rgba, [L["src"][0] / 2, L["src"][1] / 2]
        if L["kind"] == "shape" and L.get("trim_keys"):
            frac = float(valor(L["trim_keys"], t)) / 100
            chave = round(frac, 3)
            c = self.cache.get(i)
            if c is None or c[0] != chave:
                rgba, anc = _forma(L, frac)
                rgba, anc = self._efeitos(L, rgba, anc)
                c = self.cache[i] = (chave, rgba, anc)
            return c[1], c[2]
        if i not in self.cache:
            if L["kind"] == "footage":
                im = Image.open(L["file"]).convert("RGBA")
                rgba = np.asarray(im, np.float32) / 255
                anc = [im.width / 2, im.height / 2]
            elif L["kind"] == "text":
                rgba, anc = _texto(L)
            elif L["kind"] == "shape":
                rgba, anc = _forma(L)
            elif L["kind"] == "solid":
                rgba, anc = _solido(L, self.d["w"], self.d["h"])
            else:
                rgba, anc = None, [0, 0]
            if rgba is not None:
                rgba, anc = self._efeitos(L, rgba, anc)
            self.cache[i] = (None, rgba, anc)
        _, rgba, anc = self.cache[i]
        if L.get("ondula") and rgba is not None:
            rgba, anc = self._ondula(L, rgba, anc, t)
        return rgba, anc

    def _efeitos(self, L, rgba, anc):
        if L.get("grade"):
            rgba = _grade(rgba, L["grade"])
        if L.get("blur"):
            rgba, m = _desfocar(rgba, max(0.5, L["blur"] / 2.5))
            anc = [anc[0] + m, anc[1] + m]
        if L.get("shadow"):
            rgba, m = _sombra(rgba, L["shadow"])
            anc = [anc[0] + m, anc[1] + m]
        return rgba, anc

    def _ondula(self, L, rgba, anc, t):
        """Wave Warp do After: a imagem ondula na vertical, a onda correndo na horizontal."""
        alt, larg, vel = L["ondula"]
        m = int(math.ceil(alt)) + 1
        p = cv2.copyMakeBorder(rgba, m, m, 0, 0, cv2.BORDER_CONSTANT, value=(0, 0, 0, 0))
        h, w = p.shape[:2]
        xs = np.arange(w, dtype=np.float32)
        dy = (alt * np.sin(2 * np.pi * (xs / larg - vel * t))).astype(np.float32)
        mx = np.tile(xs, (h, 1))
        my = np.arange(h, dtype=np.float32)[:, None] - dy[None, :]
        out = cv2.remap(_premult(p), mx, my, cv2.INTER_LINEAR, borderMode=cv2.BORDER_CONSTANT, borderValue=0)
        a = out[..., 3:4]
        out[..., :3] = np.where(a > 1e-4, out[..., :3] / np.maximum(a, 1e-4), 0)
        return out, [anc[0], anc[1] + m]

    def _fonte(self, L, rgba, Mr):
        """A imagem pré-multiplicada que vai para o warp. Quando ela aparece bem menor na tela, uma versão já reduzida
        (INTER_AREA, em degraus de 1/8) entra no lugar: não serrilha e o warp fica muito mais barato. Imagem fixa fica
        em cache; vídeo, ondulação e traço que se desenha são refeitos a cada quadro."""
        esc = math.sqrt(abs(np.linalg.det(Mr[:2, :2])))
        degrau = 1.0 if esc > 0.85 else max(1 / 8, math.ceil(esc * 8) / 8)
        fixo = not (L.get("ondula") or (L["kind"] == "shape" and L.get("trim_keys")) or
                    (L["kind"] == "footage" and Path(L["file"]).suffix.lower() in (".mp4", ".mov", ".m4v", ".webm")))
        chave = (L["id"], degrau)
        src = self._prep.get(chave) if fixo else None
        if src is None:
            src = _premult(rgba)
            if degrau < 1:
                src = cv2.resize(src, (max(1, int(src.shape[1] * degrau)), max(1, int(src.shape[0] * degrau))),
                                 interpolation=cv2.INTER_AREA)
            if fixo:
                self._prep[chave] = src
        if degrau < 1:
            Mr = Mr @ np.diag([1 / degrau, 1 / degrau, 1.0])
        return src, Mr

    def quadro(self, t):
        f = np.zeros((self.H, self.W, 3), np.float32)
        f[...] = np.asarray(self.d.get("cor_fundo", [0, 0, 0])[:3], np.float32)
        memo = {}
        G = np.diag([self.esc, self.esc, 1.0])
        for L in self.layers:
            if L["kind"] == "null" or not (L.get("in", 0) <= t < L.get("out", 1e9)):
                continue
            op = _seg(L, "opacity_keys", "opacity", 100, t, True, (L.get("expr") or {}).get("opacity"))
            op = float(np.clip(op, 0, 100)) / 100
            if op <= 0.002:
                continue
            rgba, _ = self.base(L, t)
            if rgba is None:
                continue
            M = G @ self.transf(L, t, memo)
            h, w = rgba.shape[:2]
            cant = (M @ np.array([[0, w, w, 0], [0, 0, h, h], [1, 1, 1, 1]], np.float64))[:2]
            x0, y0 = max(0, int(math.floor(cant[0].min()))), max(0, int(math.floor(cant[1].min())))
            x1, y1 = min(self.W, int(math.ceil(cant[0].max())) + 1), min(self.H, int(math.ceil(cant[1].max())) + 1)
            if x1 <= x0 or y1 <= y0:
                continue
            Mr = M.copy()
            Mr[0, 2] -= x0
            Mr[1, 2] -= y0
            src, Mr = self._fonte(L, rgba, Mr)
            war = cv2.warpAffine(src, Mr[:2], (x1 - x0, y1 - y0), flags=cv2.INTER_LINEAR,
                                 borderMode=cv2.BORDER_CONSTANT, borderValue=0)
            cor, a = war[..., :3] * op, war[..., 3:4] * op
            roi = f[y0:y1, x0:x1]
            modo = L.get("blend")
            if modo == "add":
                roi += cor
            elif modo == "screen":
                roi[...] = 1 - (1 - roi) * (1 - cor)
            else:
                roi[...] = roi * (1 - a) + cor
            np.clip(roi, 0, 1, out=roi)
        # solta o que já saiu de cena
        for L in self.layers:
            if L.get("out", 1e9) < t - 0.5:
                if L["id"] in self.videos:
                    self.videos.pop(L["id"]).fechar()
                self.cache.pop(L["id"], None)
                for k in [k for k in self._prep if k[0] == L["id"]]:
                    self._prep.pop(k)
        return f


def renderizar(dados, saida, escala=1.0, crf=18, preset="medium"):
    C = Comp(dados, escala)
    n = int(math.ceil(dados["dur"] * C.fps))
    audio = dados.get("audio")
    cmd = ["ffmpeg", "-v", "error", "-y", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{C.W}x{C.H}", "-r", str(C.fps),
           "-i", "-"]
    if audio:
        cmd += ["-ss", f"{dados.get('audio_offset', 0):.3f}", "-i", str(audio)]
    cmd += ["-map", "0:v"] + (["-map", "1:a", "-c:a", "aac", "-b:a", "192k"] if audio else []) + \
        ["-c:v", "libx264", "-crf", str(crf), "-preset", preset, "-pix_fmt", "yuv420p", "-t", f"{dados['dur']:.3f}",
         "-movflags", "+faststart", str(saida)]
    enc = subprocess.Popen(cmd, stdin=subprocess.PIPE)
    t0 = relogio.time()
    try:
        for k in range(n):
            q = C.quadro(k / C.fps)
            enc.stdin.write((q * 255 + 0.5).astype(np.uint8).tobytes())
            if k and k % (C.fps * 10) == 0:
                print(f"  {k / C.fps:.0f}/{dados['dur']:.0f} s ({k / (relogio.time() - t0):.1f} quadros/s)", flush=True)
    finally:
        enc.stdin.close()
        enc.wait()
        for v in C.videos.values():
            v.fechar()
    if enc.returncode:
        raise SystemExit(f"o FFmpeg falhou ao codificar {saida}")
    return relogio.time() - t0


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("projeto")
    ap.add_argument("--item", default="01")
    ap.add_argument("--saida", required=True)
    ap.add_argument("--meia", action="store_true", help="960×540 (prévia de rascunho para o QA)")
    a = ap.parse_args()
    proj = Path(a.projeto).resolve()
    dados = json.loads((proj / "edicao" / f"plano_render_{a.item}.json").read_text())
    s = renderizar(dados, Path(a.saida), 0.5 if a.meia else 1.0, crf=20 if a.meia else 18,
                   preset="veryfast" if a.meia else "medium")
    print(f"OK {a.saida} ({dados['dur']:.1f} s de vídeo em {s:.0f} s)")


if __name__ == "__main__":
    main()
