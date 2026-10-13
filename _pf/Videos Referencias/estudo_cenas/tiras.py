"""Gera folhas de 'tiras de cena': cada cena em 3 momentos (início, meio, fim) para catalogar composições.
Uso: python tiras.py <video> <segs.npy> <prefixo_saida> <rotulo_video>
"""
import subprocess, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

video, segs, pref, rot = sys.argv[1:5]
s = np.load(segs) / 20.0
cenas = [(a, b) for a, b in s if b - a >= 0.5]
FW, FH = 240, 135
POR_LINHA, LINHAS = 3, 12
fonte = ImageFont.truetype("/System/Library/Fonts/Supplemental/Arial Bold.ttf", 15)

def frame(t):
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", f"{t:.2f}", "-i", video, "-frames:v", "1", "-vf", f"scale={FW}:{FH}",
                        "-f", "rawvideo", "-pix_fmt", "rgb24", "-"], capture_output=True)
    if len(r.stdout) != FW * FH * 3:
        return Image.new("RGB", (FW, FH), "black")
    return Image.frombytes("RGB", (FW, FH), r.stdout)

por_folha = POR_LINHA * LINHAS
for fi in range(0, len(cenas), por_folha):
    bloco = cenas[fi:fi + por_folha]
    cw = 3 * FW + 10
    folha = Image.new("RGB", (POR_LINHA * cw, LINHAS * (FH + 20)), (40, 40, 40))
    d = ImageDraw.Draw(folha)
    for k, (a, b) in enumerate(bloco):
        n = fi + k + 1
        x0 = (k % POR_LINHA) * cw
        y0 = (k // POR_LINHA) * (FH + 20)
        ts = [a + 0.35, (a + b) / 2, max(a + 0.4, b - 0.45)]
        for j, t in enumerate(ts):
            folha.paste(frame(t), (x0 + j * FW, y0 + 20))
        d.text((x0 + 4, y0 + 2), f"{rot}#{n}  {a:.1f}-{b:.1f}s ({b-a:.1f}s)", fill=(255, 230, 0), font=fonte)
    folha.save(f"{pref}_{fi // por_folha + 1:02d}.jpg", quality=82)
print(len(cenas), "cenas")
