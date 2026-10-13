"""Detecta os elementos (cards, textos pretos, recortes) de cada frame dos vídeos de referência.

Uso: python detectar.py <video.mp4> <saida.jsonl> [--fps 2] [--inicio s --dur s]
Cada linha: {"t": seg, "cards": [[x,y,w,h],...], "textos": [...], "recortes": [...]} em pixels 1920x1080.
"""
import argparse
import json
import subprocess

import cv2
import numpy as np

LW, LH = 480, 270
K = 1920 / LW


def fundo(video, n=25):
    """Mediana de frames quase vazios (palco vazio) = fundo com vinheta."""
    dur = float(subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0", video],
                               capture_output=True, text=True).stdout)
    cands = []
    for t in np.linspace(5, dur - 15, 160):
        f = frame_em(video, t)
        if f is None:
            continue
        g = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
        cands.append((float(g[8:-8].std()), f))
    cands.sort(key=lambda x: x[0])
    return np.median(np.stack([c[1] for c in cands[:n]]), axis=0).astype(np.int16)


def frame_em(video, t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1",
                        "-vf", f"scale={LW}:{LH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"],
                       capture_output=True)
    if len(r.stdout) != LW * LH * 3:
        return None
    return np.frombuffer(r.stdout, np.uint8).reshape(LH, LW, 3)


def dividir(diff, caixa, eixo, prof=0, gx=None, gy=None):
    """Separa cards encostados: procura faixas (colunas ou linhas) onde só há sombra/fundo."""
    x, y, w, h = caixa
    reg = diff[y:y + h, x:x + w].astype(np.float32)
    # vão entre cards = faixa onde quase todos os pixels têm cor de fundo/sombra clara
    perto = (reg < 48).astype(np.float32)
    if eixo == 0:   # colunas
        perfil = perto[int(h * 0.12):int(h * 0.88) + 1].mean(axis=0)
        tam = w
    else:
        perfil = perto[:, int(w * 0.12):int(w * 0.88) + 1].mean(axis=1)
        tam = h
    if tam < 40:
        return [caixa]
    baixo = perfil > 0.72
    # ignora as bordas (halo da sombra)
    borda = max(3, tam // 25)
    baixo[:borda] = False
    baixo[-borda:] = False
    cortes, i = [], 0
    while i < tam:
        if baixo[i]:
            j = i
            while j < tam and baixo[j]:
                j += 1
            if j - i >= 2:
                cortes.append((i, j))
            i = j
        else:
            i += 1
    if not cortes:
        return [caixa]
    partes, ini = [], 0
    for a, b in cortes:
        partes.append((ini, a))
        ini = b
    partes.append((ini, tam))
    out = []
    for a, b in partes:
        if b - a < 12:
            continue
        sub = [x + a, y, b - a, h] if eixo == 0 else [x, y + a, w, b - a]
        out += dividir(diff, sub, 1 - eixo, prof + 1, gx, gy) if prof < 3 else [sub]
    return out or [caixa]


def juntar_linhas(caixas):
    """Junta palavras da mesma linha de texto."""
    caixas = sorted(caixas, key=lambda b: b[0])
    out = []
    for b in caixas:
        for o in out:
            sob = min(o[1] + o[3], b[1] + b[3]) - max(o[1], b[1])
            if sob > 0.5 * min(o[3], b[3]) and b[0] - (o[0] + o[2]) < 14:
                x0, y0 = min(o[0], b[0]), min(o[1], b[1])
                x1, y1 = max(o[0] + o[2], b[0] + b[2]), max(o[1] + o[3], b[1] + b[3])
                o[:] = [x0, y0, x1 - x0, y1 - y0]
                break
        else:
            out.append(list(b))
    return out


def detectar(f, bg):
    f16 = f.astype(np.int16)
    diff = np.abs(f16 - bg).max(axis=2)
    diff[:3] = 0
    diff[-3:] = 0
    m = (diff > 32).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((2, 2), np.uint8))
    lum = cv2.cvtColor(f, cv2.COLOR_BGR2GRAY)
    gx = cv2.Sobel(lum, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum, cv2.CV_32F, 0, 1, ksize=3)

    n, lab, st, _ = cv2.connectedComponentsWithStats(m, 8)
    cards, outros = [], []
    for i in range(1, n):
        x, y, w, h, a = st[i]
        if a < 120:
            continue
        fill = a / float(w * h)
        if fill > 0.80 and min(w, h) >= 22:
            for sub in dividir(diff, [x, y, w, h], 0 if w >= h else 1, 0, gx, gy):
                cards.append(sub)
        else:
            outros.append((x, y, w, h, a, i))

    # texto preto: pixels escuros fora dos cards, agrupados em linhas
    escuro = (lum < 70).astype(np.uint8)
    for x, y, w, h in cards:
        escuro[max(0, y - 2):y + h + 2, max(0, x - 2):x + w + 2] = 0
    linhas = cv2.dilate(escuro, np.ones((5, 13), np.uint8))
    n2, lab2, st2, _ = cv2.connectedComponentsWithStats(linhas, 8)
    textos = []
    for i in range(1, n2):
        x, y, w, h, a = st2[i]
        dens = escuro[y:y + h, x:x + w].mean()
        if w >= 12 and h <= 75 and w >= 1.3 * h and 0.05 < dens < 0.6:
            textos.append([x, y, w, h])
    textos = juntar_linhas(textos)

    recortes = []
    for x, y, w, h, a, i in outros:
        if a < 1500:
            continue
        reg = lab[y:y + h, x:x + w] == i
        if lum[y:y + h, x:x + w][reg].mean() < 90:   # componente escuro = texto
            continue
        if any(x >= tx - 4 and y >= ty - 4 and x + w <= tx + tw + 4 and y + h <= ty + th + 4 for tx, ty, tw, th in textos):
            continue
        recortes.append([x, y, w, h])

    esc = lambda L: [[round(v * K) for v in b] for b in L]
    return esc(cards), esc(textos), esc(recortes)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("video")
    ap.add_argument("saida")
    ap.add_argument("--fps", type=float, default=2)
    ap.add_argument("--inicio", type=float, default=0)
    ap.add_argument("--dur", type=float, default=0)
    a = ap.parse_args()
    bg = fundo(a.video)
    np.save(a.saida + ".bg.npy", bg)
    cmd = ["ffmpeg", "-v", "error", "-ss", str(a.inicio), "-i", a.video]
    if a.dur:
        cmd += ["-t", str(a.dur)]
    cmd += ["-vf", f"fps={a.fps},scale={LW}:{LH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"]
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE)
    tam = LW * LH * 3
    k = 0
    with open(a.saida, "w") as out:
        while True:
            buf = p.stdout.read(tam)
            if len(buf) < tam:
                break
            f = np.frombuffer(buf, np.uint8).reshape(LH, LW, 3)
            c, t, r = detectar(f, bg)
            out.write(json.dumps({"t": round(a.inicio + k / a.fps, 2), "cards": c, "textos": t, "recortes": r}) + "\n")
            k += 1
    print(a.saida, k, "frames")


if __name__ == "__main__":
    main()
