"""Gera mapas no estilo do canal (Biblioteca de Cenas M1/M2/M4): mapa claro, região destacada em cor chapada
(ou cinza com contorno vermelho), rótulo em Impact e pontos de cidade. Sem IA: desenha fronteiras reais do
Natural Earth (buscador_assets/dados/).

Uso:
  gerar_mapa.py <saida.png> --eua Missouri Kansas [--rotulo MISSOURI] [--ponto "Kansas City:39.10:-94.58"]
  gerar_mapa.py <saida.png> --pais "United Kingdom" [--ponto "London:51.51:-0.13"]
  gerar_mapa.py <saida.png> --pais Germany --globo          (M5: globo PNG transparente, país destacado)
  gerar_mapa.py <saida.png> --pais Russia --regioes "Murmansk" --silhueta   (M6: só a silhueta, sub-região destacada)
  gerar_mapa.py <saida.png> --eua Missouri --silhueta        (silhueta dos 48 estados com o estado destacado)
  opções: --estilo cheio|contorno  --cor azul|laranja  --formato 4:3|16:9|1:1|3:4  --largura 1600
          --vista "lon0,lat0,lon1,lat1" (força o enquadramento)
Referências: v6#121/v8#192 (região laranja chapada num mapa claro), v8#8 (cinza + contorno vermelho ~4 px).
"""
import argparse
import json
import math
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

DADOS = Path(__file__).resolve().parent.parent / "dados"
IMPACT = "/System/Library/Fonts/Supplemental/Impact.ttf"
AGUA, TERRA, TERRA_FORA = "#D7E3F1", "#F8F6F1", "#ECEAE4"
BORDA, BORDA_EST = "#A9B0BC", "#C6CBD4"
CORES = {"azul": "#1D2D85", "laranja": "#F07D1A"}     # azul = Identidade Visual; laranja = referências
CONTORNO_CINZA, CONTORNO_VERM = "#C9CDD5", "#D42A2A"
TEXTO = "#191A21"
_CANAL = Path(__file__).resolve().parents[2] / "canal.json"   # identidade do canal (Estúdio, 2026-10-11)
if _CANAL.exists():
    _id = json.loads(_CANAL.read_text()).get("identidade", {})
    TEXTO = _id.get("cor_texto", TEXTO)
    CORES["azul"] = _id.get("cor_destaque", CORES["azul"])
    IMPACT = _id.get("fonte_marca_arquivo", IMPACT)
SS = 2                                                # desenha 2× e reduz (bordas suaves)
FORA_48 = {"Alaska", "Hawaii"}


def carregar(nome):
    return json.load(open(DADOS / nome))["features"]


def aneis(geom):
    if geom["type"] == "Polygon":
        return [geom["coordinates"]]
    return geom["coordinates"]                         # MultiPolygon: lista de polígonos (cada um = anéis)


def albers(lon, lat, lon0=-96.0, lat0=37.5, p1=29.5, p2=45.5):
    r = math.radians
    n = (math.sin(r(p1)) + math.sin(r(p2))) / 2
    c = math.cos(r(p1)) ** 2 + 2 * n * math.sin(r(p1))
    rho0 = math.sqrt(c - 2 * n * math.sin(r(lat0))) / n
    rho = math.sqrt(c - 2 * n * math.sin(r(lat))) / n
    th = n * r(lon - lon0)
    return rho * math.sin(th), rho0 - rho * math.cos(th)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("saida")
    ap.add_argument("--eua", nargs="*", default=None, help="estados dos EUA a destacar (nome em inglês)")
    ap.add_argument("--pais", nargs="*", default=None, help="países a destacar (nome em inglês, ex.: Germany)")
    ap.add_argument("--rotulo", default=None, help="texto do rótulo (padrão: nome da 1ª região, maiúsculo)")
    ap.add_argument("--sem-rotulo", action="store_true")
    ap.add_argument("--ponto", action="append", default=[], help='"Nome:lat:lon" (cidade/estádio)')
    ap.add_argument("--estilo", default="cheio", choices=["cheio", "contorno"])
    ap.add_argument("--cor", default="azul", choices=list(CORES))
    ap.add_argument("--formato", default="4:3")
    ap.add_argument("--largura", type=int, default=1600)
    ap.add_argument("--vista", default=None)
    ap.add_argument("--globo", action="store_true", help="M5: globo ortográfico (PNG transparente)")
    ap.add_argument("--silhueta", action="store_true", help="M6: só a silhueta do país (PNG transparente)")
    ap.add_argument("--regioes", nargs="*", default=[], help="estados/províncias do --pais a destacar (silhueta)")
    a = ap.parse_args()

    paises = carregar("ne_50m_admin_0_countries.geojson")
    eua = a.eua is not None
    if eua:
        estados = [f for f in carregar("ne_50m_admin_1_states_provinces.geojson")
                   if f["properties"]["admin"] == "United States of America"]
        nomes = {f["properties"]["name"] for f in estados}
        falta = [e for e in a.eua if e not in nomes]
        if falta:
            raise SystemExit(f"estado(s) não encontrado(s): {falta}. Exemplos: {sorted(nomes)[:8]}")
        alvo = [f for f in estados if f["properties"]["name"] in a.eua]
        proj = albers
    else:
        nomes = {f["properties"]["NAME"]: f for f in paises}
        nomes.update({f["properties"]["NAME_LONG"]: f for f in paises})
        falta = [p for p in (a.pais or []) if p not in nomes]
        if falta:
            raise SystemExit(f"país(es) não encontrado(s): {falta}")
        alvo = [nomes[p] for p in (a.pais or [])]
        estados = []
        # equiretangular corrigida pela latitude do centro da vista
        lats = [pt[1] for f in alvo for pol in aneis(f["geometry"]) for pt in pol[0]] or [20]
        lat_c = (min(lats) + max(lats)) / 2
        proj = lambda lon, lat: (lon * math.cos(math.radians(lat_c)), lat)

    if a.globo:
        return globo(a, alvo, paises)
    if a.silhueta:
        return silhueta(a, alvo, estados if eua else None)

    # ---- enquadramento ----
    fw, fh = (float(x) for x in a.formato.split(":"))
    W, H = a.largura, round(a.largura * fh / fw)
    if a.vista:
        l0, b0, l1, b1 = (float(x) for x in a.vista.split(","))
        pts = [proj(l0, b0), proj(l1, b1), proj(l0, b1), proj(l1, b0), proj((l0 + l1) / 2, b0), proj((l0 + l1) / 2, b1)]
        pad = 0
    elif eua:
        pts = [proj(*pt) for f in estados if f["properties"]["name"] not in FORA_48
               for pol in aneis(f["geometry"]) for pt in pol[0]]
        pad = 0.04
    else:
        pts = [proj(*pt) for f in alvo for pol in aneis(f["geometry"]) for pt in pol[0]]
        pad = 0.9                                      # mostra os vizinhos em volta
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    x0, x1, y0, y1 = min(xs), max(xs), min(ys), max(ys)
    dx, dy = x1 - x0, y1 - y0
    x0, x1, y0, y1 = x0 - dx * pad, x1 + dx * pad, y0 - dy * pad, y1 + dy * pad
    esc = min(W * 0.92 / (x1 - x0), H * 0.92 / (y1 - y0)) * SS
    cx, cy = (x0 + x1) / 2, (y0 + y1) / 2

    def tela(lon, lat):
        x, y = proj(lon, lat)
        return (W * SS / 2 + (x - cx) * esc, H * SS / 2 - (y - cy) * esc)

    im = Image.new("RGB", (W * SS, H * SS), AGUA)
    d = ImageDraw.Draw(im)

    def poligono(geom, fill, outline, w):
        for pol in aneis(geom):
            ext = [tela(*pt) for pt in pol[0]]
            if len(ext) > 2:
                d.polygon(ext, fill=fill)
            for anel in pol[1:]:                       # buracos (lagos/enclaves)
                d.polygon([tela(*pt) for pt in anel], fill=AGUA)
            if outline:
                d.line(ext + [ext[0]], fill=outline, width=w, joint="curve")

    cor = CORES[a.cor]
    for f in paises:
        if eua and f["properties"]["NAME"] == "United States of America":
            continue
        dest = f in alvo
        if dest:
            continue
        poligono(f["geometry"], TERRA_FORA if eua else TERRA, BORDA, 2 * SS)
    for f in estados:
        if f["properties"]["name"] in FORA_48 or f in alvo:
            continue
        poligono(f["geometry"], TERRA, BORDA_EST, int(1.5 * SS))
    for f in alvo:
        if a.estilo == "cheio":
            poligono(f["geometry"], cor, None, 0)
        else:
            poligono(f["geometry"], CONTORNO_CINZA, CONTORNO_VERM, 4 * SS)

    # ---- pontos de cidade ----
    # 2026-10-12: nomes eram 40/64 px num mapa de 1600 e saíam com ~18/28 px no vídeo (o card mostra o mapa a ~45%);
    # agora ~2,4× maiores, sempre dentro do mapa (diminui até caber) e sem repetir o nome que já é o rótulo da região
    def cabe(bb):
        return bb[0] > 30 * SS and bb[1] > 30 * SS and bb[2] < W * SS - 30 * SS and bb[3] < H * SS - 30 * SS
    rot_txt = (a.rotulo or "").upper()
    tam_cid = 96 if len(a.ponto) <= 3 else 64
    fp = ImageFont.truetype(IMPACT, tam_cid * SS)
    ocupado = []                                       # caixas dos nomes de cidade (o rótulo da região desvia delas)
    r, pts_tela = 10 * SS, []
    for p in a.ponto:                                  # 1º todos os pontos, depois os nomes desviando de tudo
        nome, lat, lon = p.rsplit(":", 2)
        x, y = tela(float(lon), float(lat))
        d.ellipse([x - r - 4 * SS, y - r - 4 * SS, x + r + 4 * SS, y + r + 4 * SS], fill="white")
        d.ellipse([x - r, y - r, x + r, y + r], fill=TEXTO)
        ocupado.append((x - r - 4 * SS, y - r - 4 * SS, x + r + 4 * SS, y + r + 4 * SS))
        pts_tela.append((nome.upper(), x, y))
    for nome, x, y in pts_tela:
        if nome == rot_txt:
            continue                                   # "PITTSBURGH" saía 2× (rótulo + ponto) e um deles cortado na borda
        g = r + 10 * SS
        cand = [((x + g, y), "lm"), ((x - g, y), "rm"), ((x, y - g), "mb"), ((x, y + g), "mt")]
        proprio = (x - r - 4 * SS, y - r - 4 * SS, x + r + 4 * SS, y + r + 4 * SS)
        escolha = None
        for tam in (tam_cid, int(tam_cid * 0.8), int(tam_cid * 0.65)):
            f_ = ImageFont.truetype(IMPACT, tam * SS)
            for c in cand:
                bb = d.textbbox(c[0], nome, font=f_, anchor=c[1], stroke_width=4 * SS)
                if cabe(bb) and not any(bb[0] < o[2] and o[0] < bb[2] and bb[1] < o[3] and o[1] < bb[3]
                                        for o in ocupado if o != proprio):
                    escolha = (c, f_)
                    break
            if escolha:
                break
        if not escolha:                                # nada livre: o que couber na tela, mesmo encostando
            f_ = ImageFont.truetype(IMPACT, int(tam_cid * 0.65) * SS)
            escolha = (next((c for c in cand if cabe(d.textbbox(c[0], nome, font=f_, anchor=c[1]))), cand[0]), f_)
        (pos, anc), f_ = escolha
        d.text(pos, nome, font=f_, fill=TEXTO, anchor=anc, stroke_width=4 * SS, stroke_fill="white")
        ocupado.append(d.textbbox(pos, nome, font=f_, anchor=anc, stroke_width=4 * SS))

    # ---- rótulo da região (ao lado dela, como "PUGLIA" em v6#121) ----
    if alvo and not a.sem_rotulo:
        txt = (a.rotulo or (alvo[0]["properties"].get("name") or alvo[0]["properties"]["NAME"])).upper()
        tp = [tela(*pt) for f in alvo for pol in aneis(f["geometry"]) for pt in pol[0]]
        rx0, rx1 = min(p[0] for p in tp), max(p[0] for p in tp)
        ry0, ry1 = min(p[1] for p in tp), max(p[1] for p in tp)
        ry, rxc = (ry0 + ry1) / 2, (rx0 + rx1) / 2
        cor_txt = cor if a.estilo == "cheio" else CONTORNO_VERM
        m = 24 * SS
        opcoes = [((rx1 + m, ry), "lm"), ((rx0 - m, ry), "rm"), ((rxc, ry1 + m), "mt"), ((rxc, ry0 - m), "mb"),
                  # região na borda do mapa: embaixo/em cima, alinhado pelo lado de dentro ("NEW YORK GIANTS" no NJ
                  # centralizado saía da tela e caía em cima de "EAST RUTHERFORD", 2026-10-12)
                  ((rx1, ry1 + m), "rt"), ((rx0, ry1 + m), "lt"), ((rx1, ry0 - m), "rb"), ((rx0, ry0 - m), "lb")]

        def livre(pos, anc):
            bb = d.textbbox(pos, txt, font=fr, anchor=anc, stroke_width=5 * SS)
            bate = any(bb[0] < o[2] and o[0] < bb[2] and bb[1] < o[3] and o[1] < bb[3] for o in ocupado)
            return cabe(bb) and not bate
        achou = None
        for tam in (150, 128, 108, 90, 76):            # era 64 fixo (~28 px no vídeo)
            fr = ImageFont.truetype(IMPACT, tam * SS)
            achou = next((o for o in opcoes if livre(*o)), None)
            if achou:
                break
        if not achou:                                  # dentro do mapa, mesmo se encostar num nome
            achou = next((o for o in opcoes if cabe(d.textbbox(o[0], txt, font=fr, anchor=o[1], stroke_width=5 * SS))), opcoes[0])
        pos, anc = achou
        d.text(pos, txt, font=fr, fill=cor_txt, anchor=anc, stroke_width=5 * SS, stroke_fill="white")

    im.resize((W, H), Image.LANCZOS).save(a.saida)
    print(a.saida, W, H)


def globo(a, alvo, paises):
    """M5 (v7#181): globo ortográfico centrado na região, com grade leve; fundo transparente."""
    if not alvo:
        raise SystemExit("--globo precisa de --pais ou --eua")
    pts = [pt for f in alvo for pol in aneis(f["geometry"]) for pt in pol[0]]
    lon0 = (min(p[0] for p in pts) + max(p[0] for p in pts)) / 2
    lat0 = max(-60, min(60, (min(p[1] for p in pts) + max(p[1] for p in pts)) / 2 + 8))
    D = a.largura
    R = D * SS / 2 - 6 * SS
    c0 = D * SS / 2
    r = math.radians
    sf, cf = math.sin(r(lat0)), math.cos(r(lat0))

    def orto(lon, lat):
        dl = r(lon - lon0)
        x = math.cos(r(lat)) * math.sin(dl)
        y = cf * math.sin(r(lat)) - sf * math.cos(r(lat)) * math.cos(dl)
        vis = sf * math.sin(r(lat)) + cf * math.cos(r(lat)) * math.cos(dl)
        if vis < 0:                                    # atrás do globo: encosta no horizonte
            n = math.hypot(x, y) or 1
            x, y = x / n, y / n
        return c0 + x * R, c0 - y * R

    im = Image.new("RGBA", (D * SS, D * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    d.ellipse([c0 - R, c0 - R, c0 + R, c0 + R], fill=AGUA)
    for lat in range(-60, 90, 30):                     # grade
        d.line([orto(lon, lat) for lon in range(-180, 181, 3)], fill="#C3D2E6", width=SS)
    for lon in range(-180, 180, 30):
        d.line([orto(lon, lat) for lat in range(-90, 91, 3)], fill="#C3D2E6", width=SS)
    cor = CORES[a.cor]
    for f in paises:
        dest = f in alvo
        for pol in aneis(f["geometry"]):
            ext = [orto(*pt) for pt in pol[0]]
            if len(ext) > 2:
                d.polygon(ext, fill=cor if dest else TERRA, outline=None if dest else BORDA)
    # máscara redonda (o que encostou no horizonte não pode vazar) + borda e sombreado leve
    mask = Image.new("L", im.size, 0)
    ImageDraw.Draw(mask).ellipse([c0 - R, c0 - R, c0 + R, c0 + R], fill=255)
    im.putalpha(Image.composite(im.getchannel("A"), mask, mask).point(lambda v: v))
    som = Image.new("RGBA", im.size, (0, 0, 0, 0))
    ds = ImageDraw.Draw(som)
    for k in range(40):                                # escurece a borda (volume)
        t = k / 40
        ds.ellipse([c0 - R * (1 - t * 0.12), c0 - R * (1 - t * 0.12), c0 + R * (1 - t * 0.12), c0 + R * (1 - t * 0.12)],
                   outline=(25, 35, 70, int(5 * (1 - t))), width=int(R * 0.004) + 1)
    im = Image.alpha_composite(im, som)
    ImageDraw.Draw(im).ellipse([c0 - R, c0 - R, c0 + R, c0 + R], outline="#9AA6B8", width=3 * SS)
    im.resize((D, D), Image.LANCZOS).save(a.saida)
    print(a.saida, D, D)


def silhueta(a, alvo, estados):
    """M6 (v7#197): silhueta cinza recortada do país, com as sub-regiões destacadas; fundo transparente."""
    if estados is not None:                            # EUA: 48 estados, destaque = --eua
        base = [f for f in estados if f["properties"]["name"] not in FORA_48]
        dest = [f for f in base if f["properties"]["name"] in (a.eua or [])]
        proj = albers
    else:
        if not alvo:
            raise SystemExit("--silhueta precisa de --pais")
        nome = alvo[0]["properties"]["ADMIN"]
        regs = [f for f in carregar("ne_50m_admin_1_states_provinces.geojson") if f["properties"]["admin"] == nome]
        dest = [f for f in regs if f["properties"]["name"] in a.regioes]
        falta = set(a.regioes) - {f["properties"]["name"] for f in dest}
        if falta:
            raise SystemExit(f"região(ões) não encontrada(s) em {nome}: {sorted(falta)}")
        base = alvo
        lats = [pt[1] for f in base for pol in aneis(f["geometry"]) for pt in pol[0]]
        lat_c = (min(lats) + max(lats)) / 2
        lon_ok = lambda lon: lon if lon > -169 else lon + 360   # Rússia/Alasca cruzam a linha de data
        proj = lambda lon, lat: (lon_ok(lon) * math.cos(math.radians(lat_c)), lat)
    pts = [proj(*pt) for f in base for pol in aneis(f["geometry"]) for pt in pol[0]]
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    W = a.largura
    esc = W * SS / (max(xs) - min(xs))
    H = int((max(ys) - min(ys)) * esc / SS) + 2
    tela = lambda lon, lat: ((proj(lon, lat)[0] - min(xs)) * esc, (max(ys) - proj(lon, lat)[1]) * esc)
    im = Image.new("RGBA", (W * SS, H * SS), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for f in base:
        for pol in aneis(f["geometry"]):
            ext = [tela(*pt) for pt in pol[0]]
            if len(ext) > 2:
                d.polygon(ext, fill="#7F858F")
    cor = CORES[a.cor] if a.cor != "azul" or estados is not None else CORES["azul"]
    for f in dest:
        for pol in aneis(f["geometry"]):
            ext = [tela(*pt) for pt in pol[0]]
            if len(ext) > 2:
                d.polygon(ext, fill=cor)
    im.resize((W, H), Image.LANCZOS).save(a.saida)
    print(a.saida, W, H)


if __name__ == "__main__":
    main()
