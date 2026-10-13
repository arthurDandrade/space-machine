"""Divide um vídeo de referência em "cenas" (trechos entre mudanças de composição) para o tiras.py.
Uso: python segmentar.py <video.mp4> <saida_segs.npy>
Saída: array Nx2 de [inicio, fim] em frames a 20 fps (o tiras.py divide por 20).
Mudança = pico da diferença entre frames seguidos (corte, entrada/saída de card, troca de texto).
"""
import subprocess
import sys

import numpy as np

video, saida = sys.argv[1:3]
W, H, FPS = 160, 90, 20
r = subprocess.run(["ffmpeg", "-v", "error", "-i", video, "-vf", f"fps={FPS},scale={W}:{H}",
                    "-f", "rawvideo", "-pix_fmt", "gray", "-"], capture_output=True)
fr = np.frombuffer(r.stdout, np.uint8).reshape(-1, H, W).astype(np.int16)
d = np.abs(np.diff(fr, axis=0)).mean(axis=(1, 2))           # diferença média por frame
# trecho "em movimento forte" = animação/corte; cenas são os trechos calmos entre eles
limiar = max(6.0, np.percentile(d, 90))
mov = d > limiar
segs, ini = [], 0
for k in range(1, len(mov)):
    if mov[k] and not mov[k - 1]:
        if k - ini >= 10:                                    # ≥ 0,5 s
            segs.append([ini, k])
    if mov[k - 1] and not mov[k]:
        ini = k
if len(mov) - ini >= 10:
    segs.append([ini, len(mov)])
np.save(saida, np.array(segs))
print(video.split("/")[-1][:60], len(segs), "cenas", f"limiar={limiar:.1f}")
