"""Desenha as detecções sobre frames, para conferir o detector.
Uso: python desenhar.py <video> <deteccoes.jsonl> <saida.jpg> t1 t2 ...
"""
import json
import subprocess
import sys

import cv2
import numpy as np

video, det, saida, ts = sys.argv[1], sys.argv[2], sys.argv[3], [float(x) for x in sys.argv[4:]]
linhas = {round(j["t"], 2): j for j in map(json.loads, open(det))}
tiles = []
for t in ts:
    j = min(linhas.values(), key=lambda d: abs(d["t"] - t))
    r = subprocess.run(["ffmpeg", "-v", "error", "-ss", str(j["t"]), "-i", video, "-frames:v", "1", "-vf", "scale=640:360",
                        "-f", "rawvideo", "-pix_fmt", "bgr24", "-"], capture_output=True)
    f = np.frombuffer(r.stdout, np.uint8).reshape(360, 640, 3).copy()
    s = 640 / 1920
    for cor, chave in (((0, 200, 0), "cards"), ((0, 0, 255), "textos"), ((255, 0, 200), "recortes")):
        for x, y, w, h in j[chave]:
            cv2.rectangle(f, (int(x * s), int(y * s)), (int((x + w) * s), int((y + h) * s)), cor, 2)
    cv2.putText(f, f"t={j['t']}", (8, 22), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 140, 255), 2)
    tiles.append(f)
while len(tiles) % 4:
    tiles.append(np.full_like(tiles[0], 255))
rows = [np.hstack(tiles[i:i + 4]) for i in range(0, len(tiles), 4)]
cv2.imwrite(saida, np.vstack(rows), [cv2.IMWRITE_JPEG_QUALITY, 85])
print(saida)
