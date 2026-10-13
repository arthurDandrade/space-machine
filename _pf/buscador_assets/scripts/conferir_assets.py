"""Folha de conferência dos assets já baixados: 2 frames de cada vídeo (0,3 s e 2 s) + cada imagem/recorte.
Serve para pegar o que a folha de candidatos não mostra (texto por cima, tarja preta, marca d'água, corte errado).

Uso: python scripts/conferir_assets.py <projeto> [saida.jpg]   (padrão: <projeto>/_work/conferir.jpg)
"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageDraw

proj = Path(sys.argv[1])
saida = Path(sys.argv[2]) if len(sys.argv) > 2 else proj / "_work" / "conferir.jpg"
tiles = []
with tempfile.TemporaryDirectory() as tmp:
    for f in sorted((proj / "assets").glob("**/*.*")):
        nome = str(f.relative_to(proj / "assets")).split("/", 1)[-1]
        if f.suffix == ".mp4":
            for t in (0.3, 2.0):
                o = Path(tmp) / f"{len(tiles)}.jpg"
                subprocess.run(["ffmpeg", "-v", "error", "-y", "-ss", str(t), "-i", str(f), "-frames:v", "1",
                                "-vf", "scale=480:-1", str(o)])
                if o.exists():
                    tiles.append((f"{nome} @{t}", Image.open(o).copy()))
        elif f.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp"):
            im = Image.open(f).convert("RGBA")
            fundo = Image.new("RGBA", im.size, (200, 200, 200, 255))
            fundo.alpha_composite(im)
            tiles.append((nome, fundo.convert("RGB")))
if not tiles:
    raise SystemExit("Nenhum asset em assets/.")
W, H, COLS = 480, 270, 4
folha = Image.new("RGB", (W * COLS, (H + 20) * ((len(tiles) + COLS - 1) // COLS)), "white")
d = ImageDraw.Draw(folha)
for i, (nome, im) in enumerate(tiles):
    im.thumbnail((W, H))
    x, y = (i % COLS) * W, (i // COLS) * (H + 20)
    folha.paste(im, (x, y + 20))
    d.text((x + 4, y + 4), nome, fill="black")
saida.parent.mkdir(parents=True, exist_ok=True)
folha.save(saida, quality=80)
print(saida)
