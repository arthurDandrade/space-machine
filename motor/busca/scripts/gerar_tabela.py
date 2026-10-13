"""Gera tabelas (G2) e gráficos de barras (G3) como imagem para card, no estilo do canal.
Dados sempre REAIS (fonte citada no rodapé), nunca inventados.

Uso (JSON na linha de comando ou arquivo .json):
  gerar_tabela.py <saida.png> '{"tabela": {"titulo": "...", "colunas": ["Team", "Wins"], "linhas": [["KC", 14], ...],
                                 "destaque": 0, "fonte": "Pro Football Reference"}}'
  gerar_tabela.py <saida.png> '{"grafico": {"titulo": "...", "itens": [["Mahomes", 5250], ...], "unidade": "yds",
                                 "destaque": 0, "fonte": "..."}}'
Referências: v7#47 (print de tabela branca em card retrato), v8#184/#186 (infográfico pronto como card).
"""
import json
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ARIAL = "/System/Library/Fonts/Supplemental/Arial.ttf"
ARIAL_B = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
TEXTO, AZUL, CINZA, LINHA, ZEBRA = "#191A21", "#1D2D85", "#6B7280", "#D9DDE5", "#F3F5F9"
_CANAL = Path(__file__).resolve().parents[2] / "canal.json"   # identidade do canal (Estúdio, 2026-10-11)
if _CANAL.exists():
    _id = json.loads(_CANAL.read_text()).get("identidade", {})
    TEXTO, AZUL = _id.get("cor_texto", TEXTO), _id.get("cor_destaque", AZUL)
    IMPACT = _id.get("fonte_marca_arquivo", IMPACT)
K = 2                                                   # desenha 2× (aguenta o zoom da cena)


def fmt(v):
    if isinstance(v, float) and not v.is_integer():
        return f"{v:,.1f}"
    if isinstance(v, (int, float)):
        return f"{int(v):,}"
    return str(v)


def tabela(spec):
    cols, linhas = spec["colunas"], spec["linhas"]
    f, fb = ImageFont.truetype(ARIAL, 34 * K), ImageFont.truetype(ARIAL_B, 34 * K)
    ft, fs = ImageFont.truetype(IMPACT, 54 * K), ImageFont.truetype(ARIAL, 24 * K)
    cel = [[fmt(v) for v in l] for l in linhas]
    larg = [max([fb.getlength(c)] + [f.getlength(l[j]) for l in cel]) + 48 * K for j, c in enumerate(cols)]
    lh, pad = 62 * K, 40 * K
    titulo = spec.get("titulo", "").upper()
    W = int(max(sum(larg), ft.getlength(titulo)) + 2 * pad)
    H = int(pad + (80 * K if titulo else 0) + lh * (len(cel) + 1) + (56 * K if spec.get("fonte") else 0) + pad)
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    y = pad
    if titulo:
        d.text((pad, y), titulo, font=ft, fill=TEXTO)
        y += 80 * K
    x = pad
    d.rectangle([pad, y, W - pad, y + lh], fill=TEXTO)
    for j, c in enumerate(cols):                         # cabeçalho; 1ª coluna à esquerda, números à direita
        if j == 0:
            d.text((x + 24 * K, y + lh / 2), c, font=fb, fill="white", anchor="lm")
        else:
            d.text((x + larg[j] - 24 * K, y + lh / 2), c, font=fb, fill="white", anchor="rm")
        x += larg[j]
    y += lh
    for i, l in enumerate(cel):
        dest = spec.get("destaque") == i
        if dest:
            d.rectangle([pad, y, W - pad, y + lh], fill="#DCE2F5")
        elif i % 2:
            d.rectangle([pad, y, W - pad, y + lh], fill=ZEBRA)
        x = pad
        for j, v in enumerate(l):
            fo, cor = (fb, AZUL) if dest else (f, TEXTO)
            if j == 0:
                d.text((x + 24 * K, y + lh / 2), v, font=fo, fill=cor, anchor="lm")
            else:
                d.text((x + larg[j] - 24 * K, y + lh / 2), v, font=fo, fill=cor, anchor="rm")
            x += larg[j]
        y += lh
        d.line([pad, y, W - pad, y], fill=LINHA, width=K)
    if spec.get("fonte"):
        d.text((pad, y + 18 * K), "Source: " + spec["fonte"], font=fs, fill=CINZA)
    return im


def grafico(spec):
    itens = spec["itens"]
    f, fb = ImageFont.truetype(ARIAL_B, 36 * K), ImageFont.truetype(IMPACT, 44 * K)
    ft, fs = ImageFont.truetype(IMPACT, 54 * K), ImageFont.truetype(ARIAL, 24 * K)
    W, pad = 1600 * K, 50 * K
    bh, gap = 70 * K, 26 * K
    titulo = spec.get("titulo", "").upper()
    rot_w = max(f.getlength(str(n)) for n, _ in itens) + 30 * K
    H = int(pad + (90 * K if titulo else 0) + len(itens) * (bh + gap) + (50 * K if spec.get("fonte") else 0) + pad)
    im = Image.new("RGB", (W, H), "white")
    d = ImageDraw.Draw(im)
    y = pad
    if titulo:
        d.text((pad, y), titulo, font=ft, fill=TEXTO)
        y += 90 * K
    vmax = max(v for _, v in itens) or 1
    un = (" " + spec["unidade"]) if spec.get("unidade") else ""
    area = W - 2 * pad - rot_w - 260 * K
    for i, (n, v) in enumerate(itens):
        cor = AZUL if spec.get("destaque") in (None, i) else "#AEB6C8"   # sem destaque: todas azuis
        d.text((pad + rot_w - 20 * K, y + bh / 2), str(n), font=f, fill=TEXTO, anchor="rm")
        x0 = pad + rot_w
        x1 = x0 + max(6 * K, area * v / vmax)
        d.rounded_rectangle([x0, y, x1, y + bh], radius=10 * K, fill=cor)
        d.text((x1 + 18 * K, y + bh / 2), fmt(v) + un, font=fb, fill=TEXTO, anchor="lm")
        y += bh + gap
    if spec.get("fonte"):
        d.text((pad, y + 10 * K), "Source: " + spec["fonte"], font=fs, fill=CINZA)
    return im


def main():
    saida, arg = sys.argv[1], sys.argv[2]
    spec = json.loads(Path(arg).read_text() if arg.endswith(".json") else arg)
    im = tabela(spec["tabela"]) if "tabela" in spec else grafico(spec["grafico"])
    im.save(saida)
    print(saida, im.width, im.height)


if __name__ == "__main__":
    main()
