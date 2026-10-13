"""Junta várias folhas de um ou mais assets numa imagem só (para revisar rápido).

Uso: python scripts/juntar_folhas.py <projeto> <saida.jpg> <asset> [<asset> ...]
"""
import sys
from pathlib import Path
from PIL import Image

proj, saida, ids = Path(sys.argv[1]), sys.argv[2], sys.argv[3:]
ims = []
for aid in ids:
    pasta = proj / "_work" / "candidatos" / aid
    for f in sorted(pasta.glob("folha.jpg")) + sorted(pasta.glob("v*_folha.jpg")):
        ims.append(Image.open(f))
if not ims:
    raise SystemExit("nenhuma folha")
w = max(i.width for i in ims)
out = Image.new("RGB", (w, sum(i.height for i in ims)), "white")
y = 0
for i in ims:
    out.paste(i, (0, y))
    y += i.height
out.thumbnail((1800, 4800))
out.save(saida, quality=85)
print(saida, out.size)
