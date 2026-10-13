"""Medidas comuns à linha de base (referências) e ao verificador (nossas prévias)."""
import json
import subprocess

import numpy as np


def ler_det(caminho):
    return [json.loads(l) for l in open(caminho)]


def estaveis(fr):
    """Frames em que a composição não está mudando (anterior e seguinte com os mesmos cards)."""
    out = []
    for i in range(1, len(fr) - 1):
        a, b, c = fr[i - 1], fr[i], fr[i + 1]
        if len(a["cards"]) == len(b["cards"]) == len(c["cards"]) and all(
                abs(p[k] - q[k]) < 40 for p, q in zip(sorted(a["cards"]), sorted(b["cards"])) for k in range(4)):
            out.append(b)
    return out


def cards_validos(f):
    return [c for c in f["cards"] if c[2] * c[3] > 150 * 150 and c[1] > 30]


def iou(a, b):
    x0, y0 = max(a[0], b[0]), max(a[1], b[1])
    x1, y1 = min(a[0] + a[2], b[0] + b[2]), min(a[1] + a[3], b[1] + b[3])
    i = max(0, x1 - x0) * max(0, y1 - y0)
    return i / float(a[2] * a[3] + b[2] * b[3] - i + 1e-9)


def tempos_assets(fr, fps):
    vivas, fim = [], []
    for f in fr:
        novas = []
        for c in cards_validos(f):
            m = max(vivas, key=lambda t: iou(t["box"], c), default=None)
            if m and iou(m["box"], c) > 0.5 and m not in novas:
                m["box"] = c
                m["n"] += 1
                novas.append(m)
            else:
                novas.append({"box": c, "n": 1})
        fim += [t for t in vivas if t not in novas]
        vivas = novas
    fim += vivas
    return [t["n"] / fps for t in fim if t["n"] >= 2]


def medir_deteccao(fr, fps):
    est = estaveis(fr)
    so_texto = [f for f in est if not cards_validos(f) and f["textos"] and not f["recortes"]]
    um_card = [cards_validos(f)[0] for f in est if len(cards_validos(f)) == 1]
    dois = [p for p in (sorted(cards_validos(f)) for f in est if len(cards_validos(f)) == 2 and not f["recortes"])
            if p[1][0] >= p[0][0] + p[0][2] - 40 and min(p[0][3], p[1][3]) / max(p[0][3], p[1][3]) > 0.7]
    alt_txt = [max(t[3] for t in f["textos"]) for f in so_texto]
    larg_txt = [max(t[2] for t in f["textos"]) for f in so_texto if len(f["textos"]) == 1]
    # texto preto ao lado/acima de cards (nome acima, rótulo lateral à direita OU à esquerda — B4, B10)
    def rotulos(f):
        cs = cards_validos(f)
        if not cs:
            return []
        topo, esq, dir_ = min(c[1] for c in cs), min(c[0] for c in cs), max(c[0] + c[2] for c in cs)
        return [t for t in f["textos"]
                if t[3] >= 40 and t[2] >= max(120, 1.6 * t[3]) and          # formato de palavra (não ruído/globo)
                (t[1] + t[3] <= topo + 10 or t[0] >= dir_ - 10 or t[0] + t[2] <= esq + 10)]

    def persiste(t, g):
        """Rótulo de verdade fica parado: a mesma caixa (±24 px) aparece num frame estável vizinho (≤0,5 s)."""
        return any(abs(g2["t"] - g["t"]) <= 0.5 and g2 is not g and
                   any(all(abs(t[k] - u[k]) <= 24 for k in range(4)) for u in g2["_rot"]) for g2 in est)

    for f in est:
        f["_rot"] = rotulos(f)
    junto = []
    for f in est:
        fora = [t for t in f["_rot"] if persiste(t, f)]
        if fora:
            junto.append(max(t[3] for t in fora))
    vazio = [f for f in fr if not f["cards"] and not f["textos"] and not f["recortes"]]
    return {
        "frac_so_texto": len(so_texto) / max(1, len(est)),
        "altura_texto_solo": alt_txt,
        "largura_texto_solo": larg_txt,
        "altura_1card": [c[3] for c in um_card],
        "altura_2cards": [(p[0][3] + p[1][3]) / 2 for p in dois],
        "tempo_assets": tempos_assets(fr, fps),
        "frac_vazio": len(vazio) / max(1, len(fr)),
        "altura_texto_junto": junto,
    }


def eventos_por_min(video, dur=None):
    """Mudanças visuais por minuto (mesmo método da análise das referências)."""
    cmd = ["ffmpeg", "-v", "error", "-i", video]
    if dur:
        cmd += ["-t", str(dur)]
    cmd += ["-vf", "fps=20,scale=96:54,format=gray", "-f", "rawvideo", "-"]
    raw = subprocess.run(cmd, capture_output=True).stdout
    a = np.frombuffer(raw, np.uint8).reshape(-1, 54, 96).astype(np.float32)[:, 3:-3]
    return eventos_de(a)


def eventos_de(a):
    fd = np.abs(np.diff(a, axis=0)).reshape(len(a) - 1, -1).mean(1)
    on, q = 0, 0
    for v in fd:
        if v > 3 and q >= 6:
            on += 1
        q = q + 1 if v < 1.2 else 0
    return on / (len(a) / 20) * 60


def pct(v, ps=(10, 50, 90)):
    v = np.asarray(v, float)
    return [round(float(np.percentile(v, p)), 2) for p in ps] if len(v) else [None] * len(ps)
