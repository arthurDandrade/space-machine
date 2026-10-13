"""Mede a curva de entrada/saída de um card a 60 fps.

Uso: python qa/medir_animacao.py <video> <t_inicio> <duracao> <entrada|saida> [rotulo]
Rastreia o card a partir do momento em que ele está parado (fim da janela na entrada, começo na saída)
e devolve quanto tempo ele leva para percorrer 50% / 90% / 98% do trajeto.
"""
import subprocess
import sys

import cv2
import numpy as np

LW, LH = 480, 270
K = 1920 / LW


def frames(video, t0, dur):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(t0), "-i", video, "-t", str(dur), "-vf",
                        f"fps=60,scale={LW}:{LH}", "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    a = np.frombuffer(r.stdout, np.uint8)
    return a.reshape(-1, LH, LW, 3)


def componentes(f, bg):
    d = np.abs(f.astype(np.int16) - bg).max(axis=2)
    d[:3] = 0
    d[-3:] = 0
    m = (d > 30).astype(np.uint8)
    m = cv2.morphologyEx(m, cv2.MORPH_OPEN, np.ones((3, 3), np.uint8))
    n, lab, st, cen = cv2.connectedComponentsWithStats(m, 8)
    return [(cen[i][0], cen[i][1], st[i][2], st[i][3], st[i][4], st[i][0], st[i][1]) for i in range(1, n) if st[i][4] > 300]


def main():
    return medir(sys.argv[1], float(sys.argv[2]), float(sys.argv[3]), sys.argv[4], sys.argv[5] if len(sys.argv) > 5 else "")


def medir(video, t0, dur, modo, rot=""):
    fr = frames(video, t0, dur)
    # fundo: bordas do quadro são fundo; uso a mediana do frame mais vazio da janela
    vaz = min(range(len(fr)), key=lambda i: fr[i].std())
    bg = cv2.GaussianBlur(fr[vaz], (0, 0), 25).astype(np.int16)
    ordem = range(len(fr) - 1, -1, -1) if modo == "entrada" else range(len(fr))
    pos, alvo = {}, None
    for i in ordem:
        cs = componentes(fr[i], bg)
        if not cs:
            break
        if alvo is None:
            alvo = max(cs, key=lambda c: c[4])
            area0 = alvo[4]
        else:
            cand = [c for c in cs if c[4] > 0.15 * area0]
            if not cand:
                break
            alvo = min(cand, key=lambda c: (c[0] - alvo[0]) ** 2 + (c[1] - alvo[1]) ** 2)
        x0, y0 = alvo[5], alvo[6]
        pos[i] = (x0 * K, y0 * K, (x0 + alvo[2]) * K, (y0 + alvo[3]) * K)
    idx = sorted(pos)
    if len(idx) < 4:
        print(rot, "não rastreou")
        return
    p = np.array([pos[i] for i in idx])
    t = np.array(idx) / 60.0
    repouso = p[-1] if modo == "entrada" else p[0]
    # a borda que percorre o trajeto inteiro (a outra fica presa na borda do quadro enquanto entra)
    desl = np.abs(p - repouso)
    e = int(np.argmax(desl.max(axis=0)))
    dist = desl[:, e]
    total = dist.max()
    if total < 40:
        print(rot, "sem movimento")
        return
    prog = 1 - dist / total if modo == "entrada" else dist / total
    # saída: conta a partir do primeiro movimento; entrada: a partir do 1º frame visível
    t_ini = t[0] if modo == "entrada" else t[int(np.argmax(dist > 6))]
    def quando(x):
        k = np.argmax(prog >= x)
        return t[k] - t_ini
    # velocidade de deriva no repouso (px/s) — o "continua deslizando"
    r = {"rot": rot, "modo": modo, "px": float(total), "50": quando(0.5), "90": quando(0.9), "98": quando(0.98)}
    print(f"{rot:28s} {modo:7s} trajeto≈{total:5.0f}px  50%: {r['50']:.2f}s  90%: {r['90']:.2f}s  98%: {r['98']:.2f}s")
    return r


if __name__ == "__main__":
    main()
